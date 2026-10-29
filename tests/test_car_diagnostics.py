import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'apps/bmw-carplay-receiver/record_car_diagnostics.py'
spec = importlib.util.spec_from_file_location('car_diagnostics', path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CarDiagnosticsTests(unittest.TestCase):
    def test_only_numeric_diagnostic_messages_allowed(self):
        for message in ('skipping transfer (240 frames)',
                        'incomplete data sent, dropping 512 frames',
                        'Error writing into ALSA: -32',
                        'audio receive stats type=102 packets=50 received=50 decrypted=50 authFailures=0 shortPackets=0 forwardGaps=1 reordered=1 duplicates=0 lateOutsideWindow=0 windowPackets=50 windowMs=5000 maxArrivalGapUs=50000 final=false',
                        'video geometry sps width=1008 height=400 pixelAspect=1.0 negotiatedWidth=1008 negotiatedHeight=400 standard=-1 range=-1 transfer=-1',
                        'video geometry output width=1008 height=400 cropLeft=0 cropTop=0 cropRight=1007 cropBottom=399 visibleWidth=1008 visibleHeight=400 stride=1024 slice=400 standard=-1 range=-1 transfer=-1',
                        'audio render stats type=102 codec=AAC_LC queue=0 queueDropped=0 pending=false queued=50 retries=2 dropped=0 outputs=48 underruns=0 capacityFrames=24000 sizeFrames=24000 startFrames=24000 queuedFrames=16000'):
            self.assertTrue(m.accepts(message), message)

    def test_payload_secrets_and_suffixes_rejected(self):
        for message in ('audio first PCM type=102 bytes=4096 head=001122',
                        'audio stream type=102 packet=1 payloadHead=001122',
                        'iap2 authentication certificate=private',
                        'skipping transfer (240 frames) secret=value',
                        'skipping transfer (240 frames)\nsecret=value',
                        'prefix skipping transfer (240 frames)'):
            self.assertFalse(m.accepts(message), message)

    def test_capture_filter_and_cleanup_are_bounded(self):
        script = m.runner_script()
        self.assertIn('--regex', script)
        self.assertNotIn('--print', script)
        self.assertIn('-r 256 -n 2', script)
        self.assertIn('sleep 1800', script)
        self.assertIn('trap cleanup EXIT HUP INT TERM', script)

if __name__ == '__main__': unittest.main()
