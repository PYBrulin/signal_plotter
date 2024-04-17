import unittest

from signal_plotter.plot_window import RecursiveDict


class TestRecursiveDict(unittest.TestCase):
    def test_init(self):
        rd = RecursiveDict({'key1': 'value1', 'key2': {'subkey1': 'subvalue1'}})
        self.assertEqual(rd['key1'], 'value1')
        self.assertEqual(rd['key2']['subkey1'], 'subvalue1')

    def test_setitem(self):
        rd = RecursiveDict()
        rd['key1'] = 'value1'
        self.assertEqual(rd['key1'], 'value1')

    def test_getitem(self):
        rd = RecursiveDict({'key1': 'value1'})
        self.assertEqual(rd['key1'], 'value1')

    def test_getattr(self):
        rd = RecursiveDict({'key1': 'value1'})
        self.assertEqual(rd.key1, 'value1')

    def test_setattr(self):
        rd = RecursiveDict()
        rd.key1 = 'value1'
        self.assertEqual(rd['key1'], 'value1')

    def test_multiple_levels(self):
        rd = RecursiveDict()
        rd['key1'] = {'subkey1': 'subvalue1'}
        self.assertEqual(rd['key1']['subkey1'], 'subvalue1')

    def test_multiple_levels_attr(self):
        rd = RecursiveDict()
        rd["key1.subkey1"] = 'subvalue1'
        self.assertEqual(rd.key1.subkey1, 'subvalue1')
        self.assertEqual(rd['key1.subkey1'], 'subvalue1')


if __name__ == '__main__':
    unittest.main()
