import importlib.util
import json
from pathlib import Path
import unittest


path = Path(__file__).resolve().parents[1] / 'scripts/car_display_capabilities.py'
spec = importlib.util.spec_from_file_location('capabilities', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CachedCapabilitiesTests(unittest.TestCase):
    def test_allowlist_keeps_display_fields_and_drops_private_fields(self):
        raw = json.dumps({
            'hmi.type': 'BMW ID4++', 'hmi.version': 'test-version',
            'hmi.display-width': '1280', 'hmi.display-height': 480,
            'vehicle.type': 'F25', 'vehicle.VIN': 'PRIVATE',
            'gps': {'latitude': 1, 'longitude': 2}, 'phone': 'PRIVATE',
        })
        result = module.extract_capabilities(raw)
        self.assertEqual(result['hmi.display-height'], 480)
        self.assertEqual(result['hmi.version'], 'test-version')
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertEqual(len(result), 5)

    def test_nested_values_are_not_forwarded(self):
        result = module.extract_capabilities(json.dumps({
            'hmi.version': {'private': 'do not copy'},
            'hmi.role': ['private'], 'tts': None,
        }))
        self.assertEqual(result, {})

    def test_oversized_values_are_not_forwarded(self):
        self.assertEqual(module.extract_capabilities(
            json.dumps({'hmi.version': 'x' * 257})), {})

    def test_nonfinite_numbers_cannot_break_report_serialization(self):
        result = module.extract_capabilities(
            '{"hmi.display-width": NaN, "hmi.display-height": 1e999, "navi": true}')
        self.assertEqual(result, {'navi': True})
        json.dumps(result, allow_nan=False)

    def test_non_object_or_oversized_document_is_rejected(self):
        for raw in ('[]', 'null', '"scalar"', '{not json', ' ' * 262145):
            with self.subTest(raw=raw[:20]):
                with self.assertRaises(ValueError):
                    module.extract_capabilities(raw)


if __name__ == '__main__':
    unittest.main()
