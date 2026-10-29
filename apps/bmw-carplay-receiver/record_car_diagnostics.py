#!/usr/bin/env python3
"""Bounded, payload-free Pi audio diagnostics that survive a USB host change.

start: enable two HAL log tags temporarily, save only strict numeric messages,
       rotate at 256 KiB x 3, and automatically stop/restore tags after 30 minutes.
stop: stop this recorder and let its cleanup restore original tag properties.
pull: copy only the recorder's filtered files. Does not change playback or pairing.
Raw receiver logs, network identifiers, keys and media payloads are never saved.
"""
from pathlib import Path
import argparse
import re
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
ADB = ROOT / 'local/tools/platform-tools/adb'
REMOTE = '/data/local/tmp/bmw-carplay-diagnostics-v1'
PATTERNS = [
    r'skipping transfer \([0-9]+ frames\)',
    r'incomplete data sent, dropping [0-9]+ frames',
    r'Error writing into ALSA: -?[0-9]+',
    r'Error reading (from|into) ALSA: -?[0-9]+',
    r'Error while reading from the pipe: -?[0-9]+',
    r'audio receive stats type=-?[0-9]+ packets=[0-9]+ received=[0-9]+ decrypted=[0-9]+ authFailures=[0-9]+ shortPackets=[0-9]+ forwardGaps=[0-9]+ reordered=[0-9]+ duplicates=[0-9]+ lateOutsideWindow=[0-9]+ windowPackets=[0-9]+ windowMs=[0-9]+ maxArrivalGapUs=[0-9]+ final=(true|false)',
    r'video geometry sps width=[0-9]+ height=[0-9]+ pixelAspect=-?[0-9]+([.][0-9]+)?([Ee]-?[0-9]+)? negotiatedWidth=[0-9]+ negotiatedHeight=[0-9]+ standard=-?[0-9]+ range=-?[0-9]+ transfer=-?[0-9]+',
    r'video geometry output width=-?[0-9]+ height=-?[0-9]+ cropLeft=-?[0-9]+ cropTop=-?[0-9]+ cropRight=-?[0-9]+ cropBottom=-?[0-9]+ visibleWidth=-?[0-9]+ visibleHeight=-?[0-9]+ stride=-?[0-9]+ slice=-?[0-9]+ standard=-?[0-9]+ range=-?[0-9]+ transfer=-?[0-9]+',
    r'audio render stats type=[0-9]+ codec=(AAC_LC|OPUS|LPCM) queue=[0-9]+ queueDropped=[0-9]+ pending=(true|false) queued=[0-9]+ retries=[0-9]+ dropped=[0-9]+ outputs=[0-9]+ underruns=-?[0-9]+ capacityFrames=[0-9]+( sizeFrames=[0-9]+ startFrames=-?[0-9]+ queuedFrames=[0-9]+)?',
]
REGEX = '^(' + '|'.join(PATTERNS) + ')$'


def accepts(message):
    return re.fullmatch(REGEX, message) is not None


def runner_script():
    # Arguments are constants or shell-quoted; no external log content is executed.
    command = shlex.join(['logcat', '-b', 'main', '-v', 'monotonic', '-T', '1',
                         '--regex', REGEX, '-f', REMOTE + '/events.log', '-r', '256', '-n', '2',
                         'AHAL_StreamPrimary:D', 'AHAL_StreamAlsa:W', 'xcertplay-usb:I', '*:S'])
    return f'''#!/system/bin/sh
umask 077
cd {shlex.quote(REMOTE)} || exit 1
getprop log.tag.AHAL_StreamPrimary > primary.previous
getprop log.tag.AHAL_StreamAlsa > alsa.previous
cleanup() {{
    trap - EXIT HUP INT TERM
    [ -n "$recorder_pid" ] && kill "$recorder_pid" 2>/dev/null
    [ -n "$timer_pid" ] && kill "$timer_pid" 2>/dev/null
    setprop log.tag.AHAL_StreamPrimary "$(cat primary.previous)"
    setprop log.tag.AHAL_StreamAlsa "$(cat alsa.previous)"
    rm -f recorder.pid
    printf 'stopped\\n' > status
}}
trap cleanup EXIT HUP INT TERM
setprop log.tag.AHAL_StreamPrimary D || exit 1
setprop log.tag.AHAL_StreamAlsa W || exit 1
{command} >/dev/null 2>&1 &
recorder_pid=$!
printf '%s\\n' "$recorder_pid" > recorder.pid
printf 'running\\n' > status
(sleep 1800; kill "$recorder_pid" 2>/dev/null) &
timer_pid=$!
wait "$recorder_pid"
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'stop', 'pull'])
    parser.add_argument('--serial', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9._:-]+', args.serial):
        parser.error('Invalid explicit serial')
    def adb(*words, timeout=12):
        return subprocess.run([str(ADB), '-s', args.serial, *words], check=True,
                              capture_output=True, text=True, timeout=timeout).stdout
    if adb('get-state').strip() != 'device':
        raise SystemExit('Pi unavailable')
    remote = shlex.quote(REMOTE)
    if args.action == 'start':
        if '--regex' not in adb('logcat', '--help'):
            raise SystemExit('Device logcat lacks required source filtering; recorder not started')
        # Refuse concurrent/repeated start so original property values are not overwritten.
        active = adb('shell', f'if [ -f {remote}/recorder.pid ]; then cat {remote}/recorder.pid; fi').strip()
        if active:
            raise SystemExit('Recorder state already exists; stop it before starting again')
        adb('shell', f'mkdir -p {remote} && chmod 700 {remote}')
        with tempfile.TemporaryDirectory() as temp:
            script = Path(temp) / 'run.sh'
            script.write_text(runner_script())
            adb('push', str(script), REMOTE + '/run.sh')
        adb('shell', f'nohup sh {remote}/run.sh </dev/null >/dev/null 2>&1 &')
        print('Recorder launched: filtered logs only; automatic expiry in 30 minutes. Verify status before USB transfer.')
    elif args.action == 'stop':
        # Verify PID belongs to our exact logcat file before signalling it (PID reuse safe).
        adb('shell', f'''if [ -f {remote}/recorder.pid ]; then
p=$(cat {remote}/recorder.pid)
case "$p" in ''|*[!0-9]*) exit 2;; esac
if tr '\\000' ' ' < /proc/"$p"/cmdline 2>/dev/null | grep -F '{REMOTE}/events.log' >/dev/null; then
kill "$p"
else
setprop log.tag.AHAL_StreamPrimary "$(cat {remote}/primary.previous)"
setprop log.tag.AHAL_StreamAlsa "$(cat {remote}/alsa.previous)"
rm -f {remote}/recorder.pid
printf 'stopped\\n' > {remote}/status
fi
fi''')
        print('Recorder stop requested; original HAL tag values restored by cleanup.')
    else:
        if args.output is None: parser.error('--output is required for pull')
        args.output.mkdir(parents=True, exist_ok=True)
        # Fixed finite filenames; no arbitrary logs or state/property files pulled.
        copied = []
        for name in ('events.log.2', 'events.log.1', 'events.log', 'status'):
            exists = adb('shell', f'[ -f {remote}/{name} ] && echo yes || true').strip() == 'yes'
            if exists:
                adb('pull', REMOTE + '/' + name, str(args.output / name))
                copied.append(name)
        print('Copied: ' + ', '.join(copied))


if __name__ == '__main__': main()
