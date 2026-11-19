import unittest
from scada_import import import_exports,coverage,TIME,POWER,ENERGY

def sample(rows):
    return (','.join([TIME,POWER,ENERGY])+'\n'+'\n'.join(rows)+'\n').encode()

class ScadaImportTests(unittest.TestCase):
    def test_missing_and_absent_are_distinct(self):
        raw=sample(['2026-10-01 00:00,1,10','2026-10-01 00:05,null,10','2026-10-01 00:15,-1,10'])
        frame,manifest,duplicates=import_exports([('a.csv',raw)])
        daily,gaps,aligned=coverage(frame)
        self.assertEqual(daily.iloc[0]['null_power_rows'],1)
        self.assertEqual(daily.iloc[0]['absent_timestamps'],1)
        self.assertEqual(daily.iloc[0]['power_coverage_span_pct'],50)
        self.assertEqual(frame[POWER].iloc[-1],-1)
        self.assertEqual(len(manifest.iloc[0]['sha256']),64)
    def test_duplicate_provenance_and_conflict(self):
        a=sample(['2026-10-01 00:00,1,10'])
        frame,_,duplicates=import_exports([('a.csv',a),('b.csv',a)])
        self.assertEqual(duplicates,1)
        self.assertIn('b.csv:row 2',frame.iloc[0]['source_rows'])
        with self.assertRaisesRegex(ValueError,'Conflicting'):
            import_exports([('a.csv',a),('b.csv',sample(['2026-10-01 00:00,2,10']))])
    def test_invalid_schema_timestamp_and_numeric(self):
        for raw in [b'DateTime,wrong\n1,2',sample(['bad,1,10']),sample(['2026-10-01 00:00,inf,10']),sample(['2026-10-01 00:00,garbage,10']),sample(['2026-10-01 00:00,1'])]:
            with self.assertRaises(ValueError): import_exports([('bad.csv',raw)])
    def test_cadence_mismatch_rejected(self):
        f,_,_=import_exports([('a.csv',sample(['2026-10-01 00:00,1,10','2026-10-01 00:06,1,11']))])
        with self.assertRaisesRegex(ValueError,'align'): coverage(f)
    def test_out_of_order_sorted_and_empty_rejected(self):
        f,_,_=import_exports([('a.csv',sample(['2026-10-01 00:05,1,11','2026-10-01 00:00,1,10']))])
        self.assertTrue(f[TIME].is_monotonic_increasing)
        with self.assertRaises(ValueError): import_exports([('a.csv',sample([]))])

if __name__=='__main__': unittest.main()
