import unittest
from above.GazoHakoTools import Hajimari

class TestGazoHakoTools(unittest.TestCase):
    def test_hajimari(self):
        self.assertIsNone(Hajimari())

if __name__ == '__main__':
    unittest.main()
