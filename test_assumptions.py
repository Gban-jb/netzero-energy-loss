import unittest
from pathlib import Path
from assumptions import loads, dumps, validate

class AssumptionTests(unittest.TestCase):
    def setUp(self):
        self.rows = loads(Path(__file__).with_name('sample-assumptions.csv').read_text())
    def test_edit_save_reopen(self):
        self.rows[2]['value'] = '45'
        self.assertEqual(loads(dumps(self.rows)), self.rows)
    def test_unknown_is_not_zero(self):
        self.rows[0]['value'] = ''
        self.assertTrue(validate(self.rows))
        self.rows[0]['value'] = '0'
        self.assertFalse(validate(self.rows))
    def test_invalid_values(self):
        for value in ('-1', 'nan', 'inf', 'abc'):
            self.rows[0]['value'] = value
            with self.assertRaises(ValueError):
                dumps(self.rows)
    def test_incomplete_or_duplicate(self):
        self.assertTrue(validate(self.rows[:-1]))
        self.assertTrue(validate(self.rows + [self.rows[0]]))
    def test_units_and_provenance(self):
        self.rows[0]['unit'] = 'USD'
        self.rows[0]['source'] = ''
        self.assertEqual(len(validate(self.rows)), 2)

if __name__ == '__main__':
    unittest.main()
