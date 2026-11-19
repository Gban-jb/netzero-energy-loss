import unittest
from pathlib import Path
from baseline import read_intervals, align_intervals, value_shortfalls
from energy import compare_energy

class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.actual_text = Path(__file__).with_name('sample-actual-energy.csv').read_text()
        self.expected_text = Path(__file__).with_name('sample-baseline.csv').read_text()
    def test_samples_and_partial_coverage(self):
        results, summary = align_intervals(read_intervals(self.actual_text),read_intervals(self.expected_text,True))
        self.assertEqual([r['shortfall_kwh'] for r in results],[20,0,None])
        self.assertEqual(summary['comparable_intervals'],2)
        valued=value_shortfalls(results,.10,'synthetic')
        self.assertEqual([r['scenario_shortfall_value_usd'] for r in valued],[2,0,None])
        self.assertEqual(value_shortfalls(results,.20,'synthetic')[0]['scenario_shortfall_value_usd'],4)
    def test_missing_and_mismatch(self):
        actual=read_intervals(self.actual_text)
        expected=read_intervals(self.expected_text.replace('SYNTHETIC_SITE','OTHER_SITE'),True)
        results, summary=align_intervals(actual,expected)
        self.assertEqual(summary['unmatched_baseline_intervals'],3)
        self.assertTrue(all(r['shortfall_kwh'] is None for r in results))
    def test_duplicate_overlap_and_missing_actual(self):
        lines=self.actual_text.splitlines()
        for text in (self.actual_text+'\n'+lines[1],self.actual_text.replace('2026-10-28T01:00,2026-10-28T02:00','2026-10-28T00:30,2026-10-28T02:00'),self.actual_text.replace(',80',',')):
            with self.assertRaises(ValueError):read_intervals(text)
    def test_invalid_tariffs(self):
        for tariff in ('nan','inf',-1,'bad'):
            with self.assertRaises(ValueError):value_shortfalls([],tariff,'source')
        with self.assertRaises(ValueError):value_shortfalls([],0,'')
    def test_dst_and_timezone(self):
        for text in (self.actual_text.replace('America/Chicago','Invalid/Zone'),self.actual_text.replace('2026-10-28T01:00','2026-11-01T01:00')):
            with self.assertRaises(ValueError):read_intervals(text)
    def test_malformed_schema(self):
        for text in ('',self.actual_text.replace('energy_kwh','power_kw'), self.actual_text.replace(',80',',80,extra')):
            with self.assertRaises(ValueError):read_intervals(text)

if __name__ == '__main__':unittest.main()
