import copy
import csv
import io
from pathlib import Path
import unittest
import maintenance as m


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.p = m.loads(Path(__file__).with_name('sample-maintenance-scenario.json').read_bytes())

    def test_sample_cost_breakdown_and_missing_replacement(self):
        rows = m.compare(self.p)
        self.assertEqual([r['priced_action_cost_usd'] for r in rows], [75, 82, 179, None, 0])
        self.assertEqual(rows[2]['labor_cost_usd'], 75)
        self.assertEqual(rows[2]['downtime_cost_usd'], 4)
        self.assertIn('downtime_hours', rows[3]['missing_inputs'])
        self.assertIn('Wait is not free', rows[4]['scope'])

    def test_edit_cost_duration_and_reopen(self):
        self.p['options'][1]['direct_cost_usd'] = 45
        self.p['options'][3]['downtime_hours'] = 4
        reopened = m.loads(m.dumps(self.p))
        self.assertEqual([r['priced_action_cost_usd'] for r in m.compare(reopened)], [75,97,179,358,0])
        self.assertEqual(m.compare(self.p), m.compare(reopened))

    def test_unknown_rate_does_not_turn_into_zero(self):
        self.p['downtime_rate']['value'] = None
        rows = m.compare(self.p)
        self.assertEqual(rows[0]['priced_action_cost_usd'], 75)
        self.assertIsNone(rows[1]['priced_action_cost_usd'])
        self.assertEqual(rows[4]['priced_action_cost_usd'], 0)
        self.assertIn('downtime_rate', rows[0]['missing_inputs'])

    def test_missing_direct_cost_is_not_zero(self):
        self.p['options'][0]['direct_cost_usd'] = ''
        self.assertIsNone(m.compare(self.p)[0]['priced_action_cost_usd'])

    def test_invalid_inputs(self):
        for value in (-1, 'nan', 'inf', True, [], 'wrong'):
            with self.subTest(value=value):
                self.p['labor_rate']['value'] = value
                with self.assertRaises(ValueError):
                    m.dumps(self.p)

    def test_schema_and_provenance(self):
        for change in [lambda p:p.update(schema_version=2),
                       lambda p:p.update(options=[]),
                       lambda p:p['options'][0].update(action='wait'),
                       lambda p:p['options'][0].update(source=''),
                       lambda p:p['labor_rate'].update(is_assumption=True),
                       lambda p:p.update(asset='')]:
            p=copy.deepcopy(self.p)
            change(p)
            with self.assertRaises(ValueError):
                m.compare(p)
        for data in ('null','[]','{}','bad'):
            with self.assertRaises(ValueError):
                m.loads(data)

    def test_csv_preserves_provenance_and_blank_total(self):
        rows = list(csv.DictReader(io.StringIO(m.export_csv(self.p))))
        self.assertEqual(rows[3]['priced_action_cost_usd'], '')
        self.assertEqual(rows[0]['labor_rate_source'], self.p['labor_rate']['source'])
        self.assertEqual(rows[0]['is_assumption'], 'true')
        self.assertEqual(rows[0]['scenario_sha256'], m.compare(self.p)[0]['scenario_sha256'])
        before=rows[0]['scenario_sha256']
        self.p['options'][0]['direct_cost_usd'] = 60
        self.assertNotEqual(before, m.compare(self.p)[0]['scenario_sha256'])

    def test_overflow_is_rejected(self):
        self.p['labor_rate']['value'] = 1e308
        self.p['options'][0]['labor_hours'] = 1e308
        with self.assertRaises(ValueError):
            m.compare(self.p)


if __name__ == '__main__':
    unittest.main()
