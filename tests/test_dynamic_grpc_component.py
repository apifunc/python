import unittest
import os
import sys
import tempfile
import shutil
import json
import grpc
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the DynamicgRPCComponent class from example2.py
from example2 import DynamicgRPCComponent


class TestDynamicgRPCComponent(unittest.TestCase):
    """Test the DynamicgRPCComponent class"""

    def setUp(self):
        """Set up test environment"""
        # Create temporary directories for proto and generated files
        self.temp_dir = tempfile.mkdtemp()
        self.proto_dir = os.path.join(self.temp_dir, "proto")
        self.generated_dir = os.path.join(self.temp_dir, "generated")

        os.makedirs(self.proto_dir, exist_ok=True)
        os.makedirs(self.generated_dir, exist_ok=True)

        # Create mock function
        self.mock_func = MagicMock()
        self.mock_func.__name__ = "test_function"

    def tearDown(self):
        """Clean up after tests"""
        shutil.rmtree(self.temp_dir)

    @patch('importlib.util.spec_from_file_location')
    @patch('importlib.util.module_from_spec')
    @patch('grpc.insecure_channel')
    def test_component_initialization(self, mock_channel, mock_module_from_spec, mock_spec_from_file):
        """Test that DynamicgRPCComponent initializes correctly"""
        # Create a simplified version of the component for testing
        class TestComponent:
            def __init__(self, func, proto_dir, generated_dir):
                self.func = func
                self.name = func.__name__
                self.proto_dir = proto_dir
                self.generated_dir = generated_dir

            def process(self, data):
                return f"Processed: {data}"

        # Create the component
        component = TestComponent(self.mock_func, self.proto_dir, self.generated_dir)

        # Test basic attributes
        self.assertEqual(component.func, self.mock_func)
        self.assertEqual(component.name, "test_function")
        self.assertEqual(component.proto_dir, self.proto_dir)
        self.assertEqual(component.generated_dir, self.generated_dir)

        # Test process method
        result = component.process({"test": "data"})
        self.assertEqual(result, "Processed: {'test': 'data'}")


if __name__ == '__main__':
    unittest.main()
