import unittest
from energy import compare_energy, demonstration_results, export_results

class EnergyTests(unittest.TestCase):
    def setUp(self):
        self.base = dict(asset='site', start='2026-10-28T00:00', end='2026-10-29T00:00', timezone='America/Chicago', unit='kWh', source='synthetic', energy_kwh=80)
    def test_required_examples(self):
        a,b,c = demonstration_results()
        self.assertEqual(a['shortfall_kwh'],20)
        self.assertEqual(b['signed_difference_kwh'],-10)
        self.assertEqual(b['shortfall_kwh'],0)
        self.assertIsNone(c['shortfall_kwh'])
        self.assertEqual(c['status'],'unavailable')
    def test_invalid_energy(self):
        for v in ('nan','inf',-1,'',None):
            with self.subTest(v=v), self.assertRaises(ValueError):
                compare_energy(dict(self.base,energy_kwh=v),self.base)
    def test_mismatched_context(self):
        for key,value in [('asset','other'),('start','2026-10-28T01:00'),('end','2026-10-29T01:00'),('timezone','UTC'),('unit','MWh')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                compare_energy(self.base,dict(self.base,**{key:value}))
    def test_missing_provenance(self):
        with self.assertRaises(ValueError): compare_energy(self.base,dict(self.base,source=''))
    def test_reversed_interval(self):
        with self.assertRaises(ValueError): compare_energy(dict(self.base,end=self.base['start']),self.base)
    def test_zero_and_export(self):
        result=compare_energy(dict(self.base,energy_kwh=0),dict(self.base,energy_kwh=0))
        self.assertEqual(result['shortfall_kwh'],0)
        self.assertIn('actual_source',export_results([result]))

if __name__ == '__main__': unittest.main()
