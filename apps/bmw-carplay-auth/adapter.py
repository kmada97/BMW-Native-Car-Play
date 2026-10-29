#!/usr/bin/env python3
"""Showcase BAA3→xcertplay adapter. Does not issue identities or establish iPhone trust."""
from __future__ import annotations

import argparse
import base64
import binascii
from collections import OrderedDict
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import ssl
import stat
import struct
import threading
import time
import uuid

HEADER = struct.Struct("<4sBBHI")
MAGIC = b"BAA3"
GET_CERTS, SIGN = 1, 2
BROKER_MAX = 65536
CERT_MAX = 65525  # xcertplay RemoteMfiAuthenticationClient
CHALLENGE_MAX = 128
HTTP_BODY_MAX = 2048
SIGNATURE_MAX = 1024


class AdapterError(Exception):
    def __init__(self, status: int, code: str, detail: str):
        self.status, self.code, self.detail = status, code, detail
        super().__init__(detail)


def invalid(detail: str) -> AdapterError:
    return AdapterError(502, "invalid_broker_response", detail)


def read_exact(connection: socket.socket, size: int, deadline: float) -> bytes:
    result = bytearray()
    while len(result) < size:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Broker deadline")
        connection.settimeout(remaining)
        block = connection.recv(size - len(result))
        if not block:
            raise invalid("Broker closed an incomplete response")
        result.extend(block)
    return bytes(result)


class BrokerClient:
    """A bounded request per Unix connection, exactly matching Showcase's broker header."""
    def __init__(self, path: str, timeout: float = 1.5):
        if not os.path.isabs(path) or not 0.05 <= timeout <= 2:
            raise ValueError("Absolute broker path and timeout in0.05..2seconds required")
        self.path, self.timeout = path, timeout

    def request(self, opcode: int, payload: bytes = b"") -> bytes:
        if opcode not in (GET_CERTS, SIGN) or len(payload) > BROKER_MAX:
            raise ValueError("Unsupported broker operation")
        deadline = time.monotonic() + self.timeout
        try:
            info = os.lstat(self.path)
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid not in (0, os.geteuid()) or stat.S_IMODE(info.st_mode) & 0o077:
                raise AdapterError(503, "unsafe_broker_socket", "Broker must be a private socket owned by this user or root")
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(self.timeout)
                connection.connect(self.path)
                connection.settimeout(max(0.001, deadline-time.monotonic()))
                connection.sendall(HEADER.pack(MAGIC, opcode, 0, 0, len(payload)) + payload)
                magic, response_op, status_code, reserved, length = HEADER.unpack(read_exact(connection, HEADER.size, deadline))
                if magic != MAGIC or response_op != opcode or reserved != 0 or length > BROKER_MAX:
                    raise invalid("Invalid broker header")
                response = read_exact(connection, length, deadline)
                if status_code == 1:
                    raise AdapterError(503, "broker_not_ready", "Owned-device signing broker is not ready")
                if status_code != 0:
                    raise AdapterError(502, "broker_rejected", "Signing broker rejected the operation")
                return response
        except AdapterError:
            raise
        except (TimeoutError, socket.timeout):
            raise AdapterError(504, "broker_timeout", "Signing broker exceeded its deadline") from None
        except OSError:
            raise AdapterError(503, "broker_unavailable", "Owned-device signing broker is unavailable") from None


def certificate_wire(payload: bytes) -> bytes:
    if not 10 <= len(payload) <= CERT_MAX:
        raise invalid("Invalid certificate package length")
    leaf_size, intermediate_size = struct.unpack_from("<II", payload)
    if leaf_size < 1 or intermediate_size < 1 or 8+leaf_size+intermediate_size != len(payload):
        raise invalid("Invalid certificate lengths")
    # Certificate DER bytes remain byte-for-byte unchanged. Only length headers change endianness.
    return struct.pack(">II", leaf_size, intermediate_size) + payload[8:]


def der_signature(signature: bytes) -> bytes:
    """Validate canonical DER SEQUENCE(INTEGER r, INTEGER s); never rewrite signature bytes."""
    if not 8 <= len(signature) <= SIGNATURE_MAX:
        raise invalid("Invalid DER signature size")

    def element(offset: int, tag: int) -> tuple[int, int]:
        if offset+2 > len(signature) or signature[offset] != tag:
            raise invalid("Invalid DER signature structure")
        n = signature[offset+1]
        start = offset+2
        if n & 0x80:
            count = n & 0x7f
            if count == 0 or count > 2 or start+count > len(signature) or signature[start] == 0:
                raise invalid("Invalid DER length")
            n = int.from_bytes(signature[start:start+count], "big")
            if n < 128:
                raise invalid("Noncanonical DER length")
            start += count
        end = start+n
        if end > len(signature):
            raise invalid("Truncated DER signature")
        return start, end

    start, end = element(0, 0x30)
    if end != len(signature):
        raise invalid("Trailing DER signature data")
    for _ in range(2):
        content, finish = element(start, 0x02)
        value = signature[content:finish]
        if not value or value[0] & 0x80 or not any(value) or (len(value)>1 and value[0]==0 and not value[1] & 0x80):
            raise invalid("Invalid DER signature integer")
        start = finish
    if start != end:
        raise invalid("Invalid DER signature members")
    return signature


class IdentityAdapter:
    """One immutable identity per process. HTTP reset cannot rotate keys or the broker."""
    def __init__(self, broker: BrokerClient, cache_limit: int = 256):
        if not 1 <= cache_limit <= 4096:
            raise ValueError("Signature replay cache must contain1..4096entries")
        self.broker = broker
        self.lock = threading.Lock()
        self.pinned: bytes | None = None
        self.poisoned = False
        self.cache: OrderedDict[str, tuple[bytes, bytes]] = OrderedDict()
        self.cache_limit = cache_limit

    def _certificate(self) -> bytes:
        if self.poisoned:
            raise AdapterError(409, "identity_changed", "Broker identity changed; explicitly restart adapter between phone sessions")
        current = certificate_wire(self.broker.request(GET_CERTS))
        if self.pinned is None:
            self.pinned = current
        elif not hmac.compare_digest(self.pinned, current):
            self.poisoned = True
            self.cache.clear()
            raise AdapterError(409, "identity_changed", "Broker identity changed; explicitly restart adapter between phone sessions")
        return self.pinned

    def certificate(self) -> dict:
        with self.lock:
            wire = self._certificate()
            return {"type": "baa", "protocolMajor": 3, "certificate": base64.b64encode(wire).decode("ascii"),
                    "certificateSha256": hashlib.sha256(wire).hexdigest()}

    def sign(self, challenge: bytes, request_id: str) -> dict:
        if not 1 <= len(challenge) <= CHALLENGE_MAX:
            raise AdapterError(400, "invalid_challenge", "Challenge must contain1..128decoded bytes")
        try:
            if str(uuid.UUID(request_id)) != request_id.lower():
                raise ValueError()
        except (ValueError, AttributeError, TypeError):
            raise AdapterError(400, "invalid_request_id", "requestId must be a canonical UUID") from None
        request_id = request_id.lower()
        with self.lock:
            self._certificate()
            digest = hashlib.sha256(challenge).digest()
            cached = self.cache.get(request_id)
            if cached is not None:
                if not hmac.compare_digest(cached[0], digest):
                    raise AdapterError(409, "request_id_conflict", "requestId was already used for another challenge")
                self.cache.move_to_end(request_id)
                signature = cached[1]
            else:
                signature = der_signature(self.broker.request(SIGN, challenge))
                # The upstream protocol has no atomic CERT+SIGN. Detect external broker replacement.
                self._certificate()
                self.cache[request_id] = (digest, signature)
                if len(self.cache) > self.cache_limit:
                    self.cache.popitem(last=False)
            return {"signature": base64.b64encode(signature).decode("ascii"), "requestId": request_id}

    def reset(self) -> dict:
        # xcertplay resets its HTTP/certificate cache. Do not rotate its two-stage identity or
        # erase replay entries; a lost HTTP response may still be retried with the same UUID.
        with self.lock:
            return {"reset": True, "identityPreserved": True}


def json_object(raw: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate field")
            result[key] = value
        return result
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs)
        if not isinstance(value, dict):
            raise ValueError("Object required")
        return value
    except (ValueError, UnicodeError):
        raise AdapterError(400, "invalid_json", "A valid JSON object with unique fields is required") from None


class AuthServer(HTTPServer):
    """Single request at a time; bounded socket reads plus an absolute connection deadline."""
    allow_reuse_address = False
    request_queue_size = 8

    def __init__(self, address, adapter: IdentityAdapter, token: str | None = None, tls_context=None):
        self.adapter, self.token, self.tls_context = adapter, token, tls_context
        ip = ipaddress.ip_address(address[0])
        if not ip.is_loopback and not (token and tls_context):
            raise ValueError("Non-loopback server requires TLS and bearer authentication")
        if token is not None and not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", token):
            raise ValueError("Bearer token must contain32..256URL-safe characters")
        if ip.version == 6:
            self.address_family = socket.AF_INET6
        super().__init__(address, AuthHandler)

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(2)
        if self.tls_context:
            try:
                connection = self.tls_context.wrap_socket(connection, server_side=True)
            except Exception:
                connection.close()
                raise
        return connection, address

    def finish_request(self, request, client_address):
        def expire():
            try:
                request.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            request.close()
        timer = threading.Timer(8, expire)
        timer.daemon = True
        timer.start()
        try:
            super().finish_request(request, client_address)
        finally:
            timer.cancel()

    def handle_error(self, request, client_address):
        # Never dump traceback/local variables, addresses, credentials, challenges or certificates.
        pass


class AuthHandler(BaseHTTPRequestHandler):
    server_version = "BMWAuthAdapter/1"
    sys_version = ""
    protocol_version = "HTTP/1.0"

    def log_message(self, format, *args):
        pass  # Standard request logging can disclose tokens in accidental URL parameters.

    def _reply(self, status: int, body: dict):
        encoded = json.dumps(body, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(encoded)
        self.close_connection = True

    def _authenticate(self):
        if self.headers.get("Origin"):
            raise AdapterError(403, "browser_origin_rejected", "Browser-origin requests are not supported")
        if self.server.token:
            supplied = self.headers.get("Authorization", "")
            if not hmac.compare_digest(supplied.encode("utf-8"), ("Bearer "+self.server.token).encode("utf-8")):
                raise AdapterError(401, "unauthorized", "Bearer authentication required")

    def _body(self) -> dict:
        if self.headers.get("Transfer-Encoding") or len(self.headers.get_all("Content-Length", [])) != 1:
            raise AdapterError(400, "invalid_framing", "Exactly one Content-Length and no transfer encoding required")
        try:
            length = int(self.headers["Content-Length"])
        except (ValueError, TypeError):
            raise AdapterError(400, "invalid_length", "Invalid Content-Length") from None
        if not 0 < length <= HTTP_BODY_MAX:
            raise AdapterError(413, "body_too_large", "Request body outside allowed bounds")
        if self.headers.get_content_type() != "application/json":
            raise AdapterError(415, "invalid_content_type", "application/json required")
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise AdapterError(400, "incomplete_body", "Incomplete request body")
        return json_object(raw)

    def _run(self, method: str):
        try:
            self._authenticate()
            if method == "GET" and self.path == "/mfi/certificate":
                response = self.server.adapter.certificate()
            elif method == "POST" and self.path == "/mfi/reset":
                if self._body():
                    raise AdapterError(400, "invalid_fields", "Reset body must be empty JSON object")
                response = self.server.adapter.reset()
            elif method == "POST" and self.path == "/mfi/sign":
                body = self._body()
                if set(body) != {"challenge", "requestId"} or not all(isinstance(body[x], str) for x in body):
                    raise AdapterError(400, "invalid_fields", "challenge and requestId strings required")
                try:
                    challenge = base64.b64decode(body["challenge"], validate=True)
                except (ValueError, binascii.Error):
                    raise AdapterError(400, "invalid_base64", "Challenge must be standard base64") from None
                response = self.server.adapter.sign(challenge, body["requestId"])
            else:
                raise AdapterError(404, "not_found", "Unsupported endpoint")
            self._reply(200, response)
        except AdapterError as error:
            self._reply(error.status, {"error": error.code, "detail": error.detail})
        except (OSError, TimeoutError):
            self.close_connection = True
        except Exception:
            self._reply(500, {"error": "internal_error", "detail": "Authentication adapter failed"})

    def do_GET(self):
        self._run("GET")

    def do_POST(self):
        self._run("POST")


def private_token(path: str | None) -> str | None:
    if path is None:
        return None
    info = os.lstat(path)
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o077 or info.st_uid != os.geteuid() or info.st_size > 258:
        raise ValueError("Token file must be private, regular and owned by this user (mode0600)")
    token = Path(path).read_text().strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", token):
        raise ValueError("Token must contain32..256URL-safe random characters")
    return token


def validate_binding(bind: str, token: str | None, certificate: str | None, key: str | None):
    address = ipaddress.ip_address(bind)  # IP literal only: no DNS-dependent exposure decisions.
    if bool(certificate) != bool(key):
        raise ValueError("TLS certificate and key must be provided together")
    if not address.is_loopback and not (token and certificate and key):
        raise ValueError("Non-loopback binding requires both TLS and a private bearer token")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", default="/tmp/showcase_baa.sock")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--broker-timeout", type=float, default=1.5)
    parser.add_argument("--token-file")
    parser.add_argument("--tls-cert")
    parser.add_argument("--tls-key")
    args = parser.parse_args()
    try:
        token = private_token(args.token_file)
        validate_binding(args.bind, token, args.tls_cert, args.tls_key)
        if not 1 <= args.port <= 65535:
            raise ValueError("Port must be in1..65535")
        context = None
        if args.tls_cert:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.load_cert_chain(args.tls_cert, args.tls_key)
        broker = BrokerClient(args.socket, args.broker_timeout)
        with AuthServer((args.bind, args.port), IdentityAdapter(broker), token, context) as server:
            print("Authentication adapter listening; owned-device broker and iPhone trust are not verified.", flush=True)
            try:
                server.serve_forever(poll_interval=0.25)
            except KeyboardInterrupt:
                pass
    except (ValueError, OSError, ssl.SSLError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
