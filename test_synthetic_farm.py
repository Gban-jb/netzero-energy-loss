import unittest

from synthetic_farm import generate_panels, estimate, due_window, priority_score, export_findings


class SyntheticFarmTests(unittest.TestCase):
    def test_generation_is_deterministic_and_varied(self):
        first, second = generate_panels(), generate_panels()
        self.assertEqual(first, second)
        self.assertEqual(len(first), 96)
        self.assertGreater(sum(p['severity'] == 'Critical' for p in first), 0)
        self.assertGreater(sum(p['severity'] == 'Healthy' for p in first), 0)

    def test_scenarios_scale_by_horizon_and_tariff(self):
        p = next(x for x in generate_panels() if x['severity'] == 'High' and x['irradiance_w_m2'] is not None) if any(x['severity'] == 'High' and x['irradiance_w_m2'] is not None for x in generate_panels()) else next(x for x in generate_panels() if x['severity'] == 'Medium' and x['irradiance_w_m2'] is not None)
        low = estimate(p, 0.10, 0, 300)
        high = estimate(p, 0.20, 0, 300)
        self.assertAlmostEqual(high['horizon_scenarios'][6]['tariff_exposure_usd'], 2 * low['horizon_scenarios'][6]['tariff_exposure_usd'])
        self.assertGreater(low['horizon_scenarios'][12]['energy_at_risk_kwh'], low['horizon_scenarios'][3]['energy_at_risk_kwh'])

    def test_missing_irradiance_stays_unavailable(self):
        p = next(x for x in generate_panels() if x['irradiance_w_m2'] is None)
        result = estimate(p, 0.12, 1, 325)
        self.assertIsNone(result['current_loss_w'])
        self.assertIsNone(result['horizon_scenarios'][6]['energy_at_risk_kwh'])
        self.assertIsNone(result['wait_exposure_usd'])

    def test_priority_safety_and_missing_fields(self):
        panels = generate_panels()
        urgent = next(p for p in panels if p['safety_flag'])
        ordinary = next(p for p in panels if p['severity'] == 'Low')
        self.assertEqual(due_window(urgent), 'Now')
        self.assertGreater(priority_score(urgent), priority_score(ordinary))
        incomplete = next(p for p in panels if not p['data_complete'])
        self.assertFalse(incomplete['data_complete'])

    def test_export_is_traceable_and_labeled(self):
        results = [estimate(p, 0.12, 1, 325) for p in generate_panels() if p['severity'] != 'Healthy']
        content = export_findings(results)
        self.assertIn('is_synthetic', content)
        self.assertIn('PNL-', content)

    def test_rejects_invalid_assumptions(self):
        p = generate_panels()[0]
        with self.assertRaises(ValueError):
            estimate(p, -1, 1, 325)

    def test_threshold_timing_is_scenario_based(self):
        p = next(x for x in generate_panels() if x['severity'] == 'Medium' and x['irradiance_w_m2'] is not None)
        no_growth = estimate(p, .12, 0, 325, critical_loss_pct=40)
        fast_growth = estimate(p, .12, 15, 325, critical_loss_pct=40)
        self.assertIsNone(no_growth['threshold_months'])
        self.assertIsNotNone(fast_growth['threshold_months'])
        self.assertGreaterEqual(fast_growth['threshold_months'], 1)
        missing = next(x for x in generate_panels() if x['irradiance_w_m2'] is None)
        self.assertIsNone(estimate(missing, .12, 10, 325)['threshold_months'])


if __name__ == '__main__':
    unittest.main()
