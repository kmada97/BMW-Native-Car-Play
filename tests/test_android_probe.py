import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import subprocess

spec = importlib.util.spec_from_file_location('probe', Path(__file__).parents[1] / 'scripts/android_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

class ProbeTest(unittest.TestCase):
    def test_failed_reads_are_unknown_not_absent(self):
        result = probe.assess({'features': {'ok': False}, 'packages': {'ok': False}})
        self.assertIsNone(result['usb_accessory_declared'])
        self.assertIsNone(result['aaidrive_installed'])

    def test_installed_apps_do_not_mean_authenticated(self):
        result = probe.assess({
            'features': {'ok': True, 'output': 'feature:android.hardware.usb.accessory'},
            'packages': {'ok': True, 'output': 'package:de.bmw.connected.mobile20.na\npackage:me.hufman.androidautoidrive'}})
        self.assertTrue(result['usb_accessory_declared'])
        self.assertTrue(result['aaidrive_installed'])
        self.assertEqual(result['authentication'], 'NOT_TESTED')
        self.assertEqual(result['bmw_screen'], 'NOT_TESTED')

    def test_similar_feature_does_not_count(self):
        result = probe.assess({'features': {'ok': True, 'output': 'feature:android.hardware.usb.accessory.fake'},
                                'packages': {'ok': True, 'output': ''}})
        self.assertFalse(result['usb_accessory_declared'])
        self.assertFalse(result['aaidrive_installed'])

    @patch.object(probe.subprocess, 'run', side_effect=subprocess.TimeoutExpired('adb', 20))
    def test_hung_device_is_reported(self, _):
        self.assertFalse(probe.run(['adb', 'get-state'])['ok'])

    @patch.object(probe.subprocess, 'run', side_effect=FileNotFoundError('adb'))
    def test_missing_adb_is_reported(self, _):
        self.assertFalse(probe.run(['adb', 'get-state'])['ok'])

if __name__ == '__main__':
    unittest.main()
