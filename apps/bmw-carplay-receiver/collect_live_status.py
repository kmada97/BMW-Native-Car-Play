#!/usr/bin/env python3
"""Read a bounded, current-PID receiver log snapshot; emit only allowlisted JSON.

Requires an explicit device serial. Never starts/stops apps, clears logs, changes
settings or reads auth files. Raw stdout/stderr and media payloads are never saved.
Evidence is observed within a bounded window, not a guarantee of current playback.
BMW frame RPC metrics are intentionally absent from logcat and not read here.
"""
from pathlib import Path
import argparse
import json
import math
import os
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
ADB = ROOT / 'local/tools/platform-tools/adb'
APP = 'com.kalyan.bmwcarplay'
TAGS = ('xcertplay-usb', 'XcertplayBMW', 'BmwReceiverBridge')
ENTRY = re.compile(r'^\s*(\d+\.\d+)\s+(\d+)\s+\d+\s+[VDIWEF]\s+([^:]+):\s?(.*)$')
STEPS = {
    'mfi/start': 'preparing_authentication', 'mfi/wait': 'waiting_authentication_provider',
    'mfi/permission': 'waiting_authentication_permission', 'mfi/ready': 'local_auth_ready',
    'wifi/ap': 'starting_hotspot', 'wifi/ap-ready': 'hotspot_ready',
    'bt/select': 'waiting_paired_phone', 'bt/rfcomm': 'connecting_bluetooth',
    'iap2/wireless': 'waiting_iap2_authentication', 'handoff/complete': 'wireless_active',
    'usb/discover': 'discovering_usb_phone', 'usb/wait': 'waiting_usb_phone',
    'usb/permission': 'waiting_usb_permission', 'usb/reenum': 'waiting_usb_configuration',
    'usb/config': 'configuring_usb', 'usb/data': 'opening_usb_data',
    'lockdown/pair': 'pairing_usb_phone', 'lockdown/carkit': 'opening_carkit',
    'network/attach': 'attaching_airplay_network', 'iap2/wired': 'waiting_wired_iap2',
    'control/end': 'control_ended',
}
STAGES = (
    ('mfi local documents ready protocolMajor=', 'local_auth_ready'),
    ('wireless hotspot backend=', 'hotspot_ready'),
    ('wireless Bluetooth PHONE_SMART candidates=', 'paired_phone_selected'),
    ('wireless AirPlay listener attached ', 'airplay_listener_ready'),
    ('airplay listener bound=', 'airplay_listener_ready'),
    ('wireless Bonjour services started', 'airplay_advertised'),
    ('wireless RFCOMM attempt=', 'connecting_bluetooth'),
    ('wireless RFCOMM connected ', 'waiting_iap2_handshake'),
    ('wireless iAP2 CSM channel opened ', 'waiting_iap2_identification'),
    ('wireless Bluetooth iAP2 control starting', 'waiting_iap2_identification'),
    ('iap2 identification accepted', 'waiting_iap2_authentication'),
    ('iap2 authentication accepted', 'bootstrap_authenticated'),
    ('iap2 subscriptions sent', 'waiting_wifi_handoff'),
    ('airplay connection accepted from ', 'airplay_connected'),
    ('airplay control encryption enabled', 'airplay_control_encrypted'),
    ('AirPlay session active ', 'airplay_session_active'),
    ('wireless type-130 tunnel data stream accepted', 'waiting_tunnel_handshake'),
    ('wireless iAP2 tunnel control starting', 'waiting_tunnel_authentication'),
    ('iAP tunnel iap2 authentication accepted', 'tunnel_authenticated'),
    ('wireless iAP2 tunnel ready;', 'tunnel_ready'),
    ('wireless handoff ready; closing Bluetooth bootstrap transport', 'wireless_active'),
    ('airplay screen first frame ', 'receiving_phone_video'),
    ('AirPlay session ended ', 'airplay_session_ended'),
    ('CarPlay transport stopped:', 'transport_stopped'),
    ('wireless bring-up failed', 'wireless_failed'),
    ('wireless RFCOMM attempt failed ', 'bluetooth_attempt_failed'),
    ('tunneled iAP2 control failed', 'tunnel_failed'),
)


def empty_evidence():
    return {
        'mfi_local_ready': False, 'mfi_protocol_major': None,
        'hotspot_ready': False, 'airplay_listener_ready': False,
        'bluetooth_rfcomm_connected': False, 'iap2_handshake_completed': False,
        'iap2_bootstrap_auth': 'not_seen', 'iap2_tunnel_auth': 'not_seen',
        'phone_auth_rejection_seen': False,
        'auth_setup_response_status': None, 'control_encryption_enabled': False,
        'airplay_record_seen': False, 'wireless_handoff_complete': False,
        'phone_video_payload_seen': False, 'decoder_render_seen': False,
        'audio_decrypted_packets_by_type': {}, 'audio_auth_failures_by_type': {},
        'audio_play_started_types': [],
    }


def parse_snapshot(raw, pid, now, lookback=300, fresh=120):
    """Pure parser: untrusted log strings never become output strings."""
    evidence = empty_evidence()
    stage, stage_at, boundary = None, None, False
    generation = None
    auth_cseq = None
    for line in raw.splitlines():
        entry = ENTRY.match(line)
        if not entry or int(entry[2]) != pid or entry[3].strip() not in TAGS:
            continue
        at = float(entry[1])
        if not math.isfinite(at) or not now - lookback <= at <= now + 2:
            continue
        message = entry[4]
        next_stage = None
        if message.startswith('starting controller display='):
            evidence, auth_cseq = empty_evidence(), None
            boundary, generation, next_stage = True, None, 'controller_starting'
        match = re.fullmatch(r'wireless bring-up generation=(\d+) starting', message)
        if match:
            local_ready, major = evidence['mfi_local_ready'], evidence['mfi_protocol_major']
            evidence, auth_cseq = empty_evidence(), None
            evidence.update(mfi_local_ready=local_ready, mfi_protocol_major=major)
            generation, boundary, next_stage = int(match[1]), True, 'starting_hotspot'
        for prefix, fixed_stage in STAGES:
            if message.startswith(prefix):
                next_stage = fixed_stage
                break
        step = re.match(r'STEP ([a-z/-]+):', message)
        if step and step[1] in STEPS:
            next_stage = STEPS[step[1]]
        if next_stage:
            stage, stage_at = next_stage, at
        major = re.fullmatch(r'mfi local documents ready protocolMajor=([123])', message)
        if major:
            evidence.update(mfi_local_ready=True, mfi_protocol_major=int(major[1]))
        if next_stage == 'hotspot_ready': evidence['hotspot_ready'] = True
        if next_stage == 'airplay_listener_ready': evidence['airplay_listener_ready'] = True
        if next_stage == 'waiting_iap2_handshake': evidence['bluetooth_rfcomm_connected'] = True
        if next_stage == 'waiting_iap2_identification': evidence['iap2_handshake_completed'] = True
        for prefix, field in (('', 'iap2_bootstrap_auth'), ('iAP tunnel ', 'iap2_tunnel_auth')):
            if message == prefix + 'iap2 mfi rx=0xaa05 authentication-succeeded':
                evidence[field] = 'accepted'
                stage, stage_at = ('tunnel_authenticated' if prefix else 'bootstrap_authenticated'), at
        # Match the typed exception, never arbitrary payload text containing its name.
        exception_prefix = r'(?:com\.shilapi\.xcertplay\.mfi\.Iap2MfiAuthenticationException: )?'
        if re.fullmatch(exception_prefix + r'(?:iAP tunnel )?iPhone sent AuthenticationFailed', message):
            evidence['phone_auth_rejection_seen'] = True
            if message.startswith('iAP tunnel '): evidence['iap2_tunnel_auth'] = 'rejected'
            elif message.startswith('iap2 '): evidence['iap2_bootstrap_auth'] = 'rejected'
            stage, stage_at = 'phone_authentication_rejected', at
        if re.fullmatch(exception_prefix + r'Timed out waiting for iAP2 MFi authentication', message):
            stage, stage_at = 'phone_authentication_timeout', at
        if next_stage == 'airplay_connected': auth_cseq = None
        request = re.fullmatch(r'airplay rx POST /auth-setup cseq=(\d+) body=\d+', message)
        if request: auth_cseq = request[1]
        response = re.fullmatch(r'airplay tx status=([1-5]\d\d) cseq=(\d+) body=\d+', message)
        if response and auth_cseq == response[2]:
            evidence['auth_setup_response_status'], auth_cseq = int(response[1]), None
        if next_stage == 'airplay_control_encrypted': evidence['control_encryption_enabled'] = True
        if re.match(r'airplay rx RECORD \S+ cseq=\d+ body=\d+$', message):
            evidence['airplay_record_seen'] = True
        if next_stage == 'airplay_session_active': evidence['airplay_record_seen'] = True
        if next_stage == 'wireless_active': evidence['wireless_handoff_complete'] = True
        if next_stage == 'receiving_phone_video': evidence['phone_video_payload_seen'] = True
        if re.fullmatch(r'video decoder rendered first frame bytes=\d+', message):
            evidence['decoder_render_seen'] = True
            if evidence['phone_video_payload_seen']:
                stage, stage_at = 'live_video_decoded', at
        audio = re.fullmatch(r'audio stream type=(\d{1,3}) decrypted=(\d+) authFailures=(\d+)', message)
        if audio:
            evidence['audio_decrypted_packets_by_type'][audio[1]] = int(audio[2])
            evidence['audio_auth_failures_by_type'][audio[1]] = int(audio[3])
        audio_start = re.fullmatch(r'audio playback started type=(\d{1,3})', message)
        if audio_start:
            value = int(audio_start[1])
            if value not in evidence['audio_play_started_types']:
                evidence['audio_play_started_types'].append(value)
    age = max(0, round(now - stage_at, 3)) if stage_at is not None else None
    return {
        'schema_version': 1, 'collection_status': 'ok', 'receiver_running': True,
        'receiver_pid': pid, 'lookback_seconds': lookback,
        'session_boundary_seen': boundary, 'wireless_generation': generation,
        'last_observed_stage': stage, 'last_stage_age_seconds': age,
        'last_stage_fresh': age is not None and age <= fresh,
        'current_stage': stage if age is not None and age <= fresh else 'unknown_or_stale',
        'observed': evidence,
        'bmw_frame_rpc_proof': 'not_collected_logcat_omits_frame_events',
        'evidence_scope': 'bounded_log_observations_not_current_playback_guarantee',
    }


class CollectionError(Exception):
    pass


def collect(serial, lookback, fresh, lines):
    def adb(*args, allow_missing=False):
        try:
            result = subprocess.run([str(ADB), '-s', serial, *args], capture_output=True,
                                    timeout=6, check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise CollectionError('adb_unavailable_or_timed_out') from None
        if result.returncode and not allow_missing:
            raise CollectionError('adb_read_failed')
        return result.stdout.decode('utf-8', errors='replace')

    def get_pid():
        raw = adb('shell', 'pidof', APP, allow_missing=True).strip()
        if not raw: return None
        if not re.fullmatch(r'\d+', raw): raise CollectionError('receiver_pid_ambiguous')
        return int(raw)

    if adb('get-state').strip() != 'device': raise CollectionError('device_not_ready')
    pid = get_pid()
    if pid is None:
        return {'schema_version': 1, 'collection_status': 'receiver_not_running',
                'receiver_running': False}
    # A stable process start tick avoids accepting a PID recycled during collection.
    def start_tick():
        raw = adb('shell', 'cat', f'/proc/{pid}/stat')
        tail = raw.rsplit(')', 1)[-1].split()
        if len(tail) < 20 or not tail[19].isdigit():
            raise CollectionError('process_identity_unavailable')
        return tail[19]

    before = start_tick()
    raw = adb('logcat', '-b', 'main', '-d', '-v', 'epoch', f'--pid={pid}',
              '-t', str(lines), '-s', *(tag + ':V' for tag in TAGS), '*:S')
    now_raw = adb('shell', 'date', '+%s').strip()
    if not re.fullmatch(r'\d{9,12}', now_raw): raise CollectionError('device_clock_unavailable')
    if get_pid() != pid or start_tick() != before:
        raise CollectionError('receiver_changed_during_collection')
    return parse_snapshot(raw, pid, float(now_raw), lookback, fresh)


def bounded(minimum, maximum):
    def parse(value):
        try: number = int(value)
        except ValueError: raise argparse.ArgumentTypeError('Expected an integer') from None
        if not minimum <= number <= maximum:
            raise argparse.ArgumentTypeError(f'Expected {minimum}..{maximum}')
        return number
    return parse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--lookback-seconds', type=bounded(1, 3600), default=300)
    parser.add_argument('--fresh-seconds', type=bounded(1, 600), default=120)
    parser.add_argument('--lines', type=bounded(100, 5000), default=2000)
    args = parser.parse_args()
    if not args.serial or args.serial.startswith('-') or any(c.isspace() for c in args.serial):
        parser.error('Supply one explicit device serial without whitespace')
    try:
        report = collect(args.serial, args.lookback_seconds, args.fresh_seconds, args.lines)
    except CollectionError as error:
        report = {'schema_version': 1, 'collection_status': str(error)}
    text = json.dumps(report, indent=2, sort_keys=True) + '\n'
    if args.output:
        temporary = None
        try:
            fd, temporary = tempfile.mkstemp(prefix='.receiver-status-', dir=args.output.parent)
            with os.fdopen(fd, 'w') as stream: stream.write(text)
            os.replace(temporary, args.output)
        except OSError:
            if temporary:
                try: os.unlink(temporary)
                except OSError: pass
            print(json.dumps({'schema_version': 1, 'collection_status': 'output_write_failed'}))
            return 1
    print(text, end='')
    return 0 if report['collection_status'] == 'ok' else 1


if __name__ == '__main__':
    raise SystemExit(main())
