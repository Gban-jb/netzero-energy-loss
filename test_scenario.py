import copy
import csv
import io
import unittest
from pathlib import Path
import scenario

ROOT = Path(__file__).parent


class CompleteScenarioTests(unittest.TestCase):
    def setUp(self):
        self.payload = scenario.loads((ROOT / 'sample-complete-scenario.json').read_bytes())

    def test_edit_save_reopen_and_traceable_export(self):
        for row in self.payload['costs']:
            if row['parameter'] == 'cleaning':
                row['value'] = '45'
            if row['parameter'] == 'tariff':
                row['value'] = '0.15'
        reopened = scenario.loads(scenario.dumps(self.payload))
        result = scenario.calculate(reopened)
        self.assertEqual(result['scenario_shortfall_value_usd'], 3)
        self.assertEqual(result['input_cleaning_value'], '45')
        exported = list(csv.DictReader(io.StringIO(scenario.export_csv(reopened))))[0]
        self.assertEqual(exported['scenario_sha256'], result['scenario_sha256'])
        self.assertEqual(exported['actual_source'], self.payload['actual']['source'])
        self.assertEqual(scenario.calculate(self.payload), result)

    def test_three_required_energy_cases(self):
        for actual, expected, shortfall, dollars in [(80, 100, 20, 2), (110, 100, 0, 0), (80, None, None, None)]:
            with self.subTest(expected=expected, actual=actual):
                self.payload['actual']['energy_kwh'] = actual
                self.payload['expected']['energy_kwh'] = expected
                result = scenario.calculate(self.payload)
                self.assertEqual(result['shortfall_kwh'], shortfall)
                self.assertEqual(result['scenario_shortfall_value_usd'], dollars)
                if expected is None:
                    row = list(csv.DictReader(io.StringIO(scenario.export_csv(self.payload))))[0]
                    self.assertEqual(row['scenario_shortfall_value_usd'], '')

    def test_invalid_cost_blocks_save(self):
        for value in ('', '-1', 'nan', 'inf'):
            self.payload['costs'][0]['value'] = value
            with self.assertRaises(ValueError):
                scenario.dumps(self.payload)

    def test_mismatch_and_invalid_schema_rejected(self):
        for mutate in [lambda p: p.update(schema_version=2),
                       lambda p: p.update(costs=None),
                       lambda p: p['expected'].update(asset='OTHER'),
                       lambda p: p['actual'].update(energy_kwh=True),
                       lambda p: p['actual'].update(start=[]),
                       lambda p: p.update(cached_result=123)]:
            p = copy.deepcopy(self.payload)
            mutate(p)
            with self.assertRaises(ValueError):
                scenario.calculate(p)
        for raw in ('[]', '{}', 'not json'):
            with self.assertRaises(ValueError):
                scenario.loads(raw)

    def test_input_change_changes_fingerprint(self):
        before = scenario.calculate(self.payload)['scenario_sha256']
        self.payload['actual']['energy_kwh'] = 70
        self.assertNotEqual(before, scenario.calculate(self.payload)['scenario_sha256'])


if __name__ == '__main__':
    unittest.main()
