"""Protocol tests only. Every certificate/signature below is SYNTHETIC and untrusted."""
import base64
from contextlib import contextmanager
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import struct
import sys
import tempfile
import threading
import time
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adapter import (AdapterError, AuthServer, BrokerClient, IdentityAdapter, HEADER, MAGIC,
                     GET_CERTS, SIGN, certificate_wire, der_signature, private_token, validate_binding)

LEAF = b"SYNTHETIC-LEAF-NOT-AN-ACCEPTED-IDENTITY"
INTERMEDIATE = b"SYNTHETIC-INTERMEDIATE-NOT-TRUSTED"
DER_SHAPE_ONLY = bytes.fromhex("3006020101020102")  # r=1,s=2; NOT a cryptographic signature.


def package(leaf=LEAF, intermediate=INTERMEDIATE):
    return struct.pack("<II", len(leaf), len(intermediate)) + leaf + intermediate


def exact(conn, count):
    value = b""
    while len(value) < count:
        chunk = conn.recv(count-len(value))
        if not chunk:
            raise OSError("Closed")
        value += chunk
    return value


class FakeBroker:
    def __init__(self, directory, callback=None):
        self.path = str(Path(directory)/"synthetic.sock")
        self.requests = []
        self.certs = package()
        self.callback = callback
        self.response_header = None
        self.fragment = False
        self.stopped = threading.Event()
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket.bind(self.path)
        os.chmod(self.path, 0o600)
        self.socket.listen(8)
        self.socket.settimeout(.05)
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        while not self.stopped.is_set():
            try:
                conn, _ = self.socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with conn:
                conn.settimeout(.5)
                try:
                    header = HEADER.unpack(exact(conn, HEADER.size))
                    if header[0] != MAGIC or header[2:4] != (0, 0):
                        raise OSError("Unexpected request header")
                    payload = exact(conn, header[4])
                    self.requests.append((header[1], payload))
                    status, response = self.callback(header[1], payload) if self.callback else (0, self.certs if header[1] == GET_CERTS else DER_SHAPE_ONLY)
                    encoded = (self.response_header or HEADER.pack(MAGIC, header[1], status, 0, len(response))) + response
                    if self.fragment:
                        for offset in range(0, len(encoded), 3):
                            conn.sendall(encoded[offset:offset+3])
                    else:
                        conn.sendall(encoded)
                except OSError:
                    pass

    def close(self):
        self.stopped.set()
        self.socket.close()
        self.thread.join(2)
        if self.thread.is_alive():
            raise AssertionError("Fake broker thread did not stop")


@contextmanager
def fake(callback=None):
    with tempfile.TemporaryDirectory(prefix="bmw-auth-test-", dir="/tmp") as directory:
        broker = FakeBroker(directory, callback)
        try:
            yield broker
        finally:
            broker.close()


@contextmanager
def http_server(adapter, token=None):
    server = AuthServer(("127.0.0.1", 0), adapter, token)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .01}, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)
        assert not thread.is_alive()


def request(port, method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        supplied = {"Content-Type": "application/json"}
        supplied.update(headers or {})
        if isinstance(body, dict):
            body = json.dumps(body)
        conn.request(method, path, body=body, headers=supplied)
        response = conn.getresponse()
        return response.status, json.loads(response.read())
    finally:
        conn.close()


class BrokerTests(unittest.TestCase):
    def test_exact_wire_conversion_fragmentation_and_digest(self):
        with fake() as broker:
            broker.fragment = True
            result = IdentityAdapter(BrokerClient(broker.path)).certificate()
            wire = base64.b64decode(result["certificate"])
            self.assertEqual(wire, struct.pack(">II", len(LEAF), len(INTERMEDIATE))+LEAF+INTERMEDIATE)
            self.assertEqual(result["type"], "baa")
            self.assertEqual(result["protocolMajor"], 3)
            self.assertEqual(result["certificateSha256"], hashlib.sha256(wire).hexdigest())
            self.assertEqual(broker.requests, [(GET_CERTS, b"")])

    def test_sign_exact_message_der_retry_dedupe_and_reset(self):
        with fake() as broker:
            adapter = IdentityAdapter(BrokerClient(broker.path))
            challenge = bytes(range(128))
            ident = str(uuid.uuid4())
            result = adapter.sign(challenge, ident)
            self.assertEqual(base64.b64decode(result["signature"]), DER_SHAPE_ONLY)
            self.assertEqual(adapter.reset(), {"reset": True, "identityPreserved": True})
            self.assertEqual(adapter.sign(challenge, ident), result)
            self.assertEqual([item for item in broker.requests if item[0] == SIGN], [(SIGN, challenge)])
            with self.assertRaises(AdapterError) as conflict:
                adapter.sign(b"different", ident)
            self.assertEqual(conflict.exception.status, 409)

    def test_identity_rotation_is_latched_even_after_reset(self):
        with fake() as broker:
            adapter = IdentityAdapter(BrokerClient(broker.path)); first = adapter.certificate()
            broker.certs = package(b"DIFFERENT-SYNTHETIC-LEAF")
            with self.assertRaises(AdapterError) as failure:
                adapter.sign(b"synthetic challenge", str(uuid.uuid4()))
            self.assertEqual(failure.exception.code, "identity_changed")
            self.assertFalse(any(op == SIGN for op, _ in broker.requests))
            broker.certs = package(); adapter.reset()
            with self.assertRaises(AdapterError):
                adapter.certificate()
            self.assertIsNotNone(first)

    def test_rotation_during_sign_does_not_return_wrong_identity_signature(self):
        with fake() as broker:
            def response(op, payload):
                if op == SIGN:
                    broker.certs = package(b"ROTATED-DURING-SIGN")
                    return 0, DER_SHAPE_ONLY
                return 0, broker.certs
            broker.callback = response
            with self.assertRaises(AdapterError) as failure:
                IdentityAdapter(BrokerClient(broker.path)).sign(b"challenge", str(uuid.uuid4()))
            self.assertEqual(failure.exception.code, "identity_changed")

    def test_bad_headers_are_rejected_before_payload(self):
        for header in [HEADER.pack(b"NOPE", 1, 0, 0, 0), HEADER.pack(MAGIC, 2, 0, 0, 0),
                       HEADER.pack(MAGIC, 1, 0, 1, 0), HEADER.pack(MAGIC, 1, 0, 0, 65537)]:
            with self.subTest(header=header), fake() as broker:
                broker.response_header = header
                with self.assertRaises(AdapterError) as error:
                    BrokerClient(broker.path).request(GET_CERTS)
                self.assertEqual(error.exception.code, "invalid_broker_response")

    def test_not_ready_failed_sign_and_deadline(self):
        for status, expected in [(1, 503), (2, 502), (3, 502), (255, 502)]:
            with self.subTest(status=status), fake(lambda op, body: (status, b"")) as broker:
                with self.assertRaises(AdapterError) as error:
                    BrokerClient(broker.path).request(GET_CERTS)
                self.assertEqual(error.exception.status, expected)
        def delayed(op, body):
            time.sleep(.15)
            return 0, package()
        with fake(delayed) as broker:
            before = time.monotonic()
            with self.assertRaises(AdapterError) as error:
                BrokerClient(broker.path, timeout=.05).request(GET_CERTS)
            self.assertEqual(error.exception.status, 504)
            self.assertLess(time.monotonic()-before, .3)

    def test_private_socket_and_bounds(self):
        with fake() as broker:
            os.chmod(broker.path, 0o666)
            with self.assertRaises(AdapterError) as error:
                BrokerClient(broker.path).request(GET_CERTS)
            self.assertEqual(error.exception.code, "unsafe_broker_socket")
            self.assertEqual(broker.requests, [])
        for malformed in [b"short", struct.pack("<II", 0, 1)+b"x", struct.pack("<II", 2, 2)+b"xx", b"x"*65526]:
            with self.assertRaises(AdapterError):
                certificate_wire(malformed)
        for malformed in [b"x"*64, DER_SHAPE_ONLY+b"x", bytes.fromhex("3006020100020102"), bytes.fromhex("300702020001020102")]:
            with self.assertRaises(AdapterError):
                der_signature(malformed)

    def test_concurrent_retries_serialize_and_sign_once(self):
        with fake() as broker:
            adapter = IdentityAdapter(BrokerClient(broker.path)); ident = str(uuid.uuid4()); results = []; failures = []
            def sign():
                try: results.append(adapter.sign(b"synthetic", ident))
                except Exception as error: failures.append(error)
            threads = [threading.Thread(target=sign) for _ in range(8)]
            for thread in threads: thread.start()
            for thread in threads: thread.join(2)
            self.assertFalse(failures)
            self.assertEqual(len(results), 8)
            self.assertEqual(len([op for op, _ in broker.requests if op == SIGN]), 1)
            self.assertTrue(all(result == results[0] for result in results))


class HttpTests(unittest.TestCase):
    def test_xcertplay_http_contract_and_input_validation(self):
        with fake() as broker, http_server(IdentityAdapter(BrokerClient(broker.path))) as port:
            self.assertEqual(request(port, "GET", "/mfi/certificate")[0], 200)
            body = {"challenge": base64.b64encode(b"synthetic").decode(), "requestId": str(uuid.uuid4())}
            code, result = request(port, "POST", "/mfi/sign", body)
            self.assertEqual(code, 200); self.assertEqual(result["signature"], base64.b64encode(DER_SHAPE_ONLY).decode())
            self.assertEqual(request(port, "POST", "/mfi/reset", {})[1]["identityPreserved"], True)
            for bad in [{"challenge": "???", "requestId": str(uuid.uuid4())},
                        {"challenge": "", "requestId": str(uuid.uuid4())},
                        {"challenge": base64.b64encode(b"x"*129).decode(), "requestId": str(uuid.uuid4())},
                        {"challenge": "eA==", "requestId": "not-uuid"},
                        {"challenge": "eA==", "requestId": str(uuid.uuid4()), "extra": True},
                        '{"challenge":"eA==","challenge":"eQ==","requestId":"x"}']:
                self.assertEqual(request(port, "POST", "/mfi/sign", bad)[0], 400)
            self.assertEqual(request(port, "POST", "/mfi/sign", "x"*2049)[0], 413)
            self.assertEqual(request(port, "POST", "/mfi/reset", "{}", {"Content-Type": "text/plain"})[0], 415)
            self.assertEqual(request(port, "GET", "/mfi/certificate?token=anything")[0], 404)
            self.assertEqual(request(port, "GET", "/mfi/certificate", headers={"Origin": "https://example.com"})[0], 403)

    def test_authentication_precedes_broker_access(self):
        token = "synthetic_test_token_32_characters_long"
        with fake() as broker, http_server(IdentityAdapter(BrokerClient(broker.path)), token) as port:
            self.assertEqual(request(port, "GET", "/mfi/certificate")[0], 401)
            self.assertEqual(broker.requests, [])
            self.assertEqual(request(port, "GET", "/mfi/certificate", headers={"Authorization": "Bearer "+token})[0], 200)

    def test_external_bind_cannot_skip_tls_or_token(self):
        validate_binding("127.0.0.1", None, None, None)
        validate_binding("::1", None, None, None)
        for token, cert, key in [(None, None, None), ("x"*32, None, None), (None, "cert", "key"), ("x"*32, "cert", None)]:
            with self.assertRaises(ValueError): validate_binding("0.0.0.0", token, cert, key)
        validate_binding("0.0.0.0", "x"*32, "cert", "key")
        with self.assertRaises(ValueError): AuthServer(("0.0.0.0", 0), None)
        with self.assertRaises(ValueError): validate_binding("localhost", None, None, None)

    def test_private_token_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"token"; path.write_text("synthetic_test_token_32_characters_long\n");path.chmod(0o600)
            self.assertEqual(private_token(str(path)), path.read_text().strip())
            path.chmod(0o644)
            with self.assertRaises(ValueError): private_token(str(path))


if __name__ == "__main__":
    unittest.main()
