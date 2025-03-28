import unittest
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

class SimpleTest(unittest.TestCase):
    def test_simple(self):
        self.assertTrue(True)

if __name__ == "__main__":
    unittest.main()
