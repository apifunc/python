import unittest
import os
import sys
import tempfile
import shutil
import json
import base64
import threading
import time
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import from example2.py
from example2 import PipelineOrchestrator


class TestPipelineOrchestrator(unittest.TestCase):
    """Test the PipelineOrchestrator class"""

    def test_pipeline_orchestrator(self):
        """Test that PipelineOrchestrator works correctly"""
        # Create a pipeline
        pipeline = PipelineOrchestrator()

        # Create mock components
        component1 = MagicMock()
        component1.name = "component1"
        component1.process.return_value = "processed by component1"

        component2 = MagicMock()
        component2.name = "component2"
        component2.process.return_value = "processed by component2"

        # Add components to pipeline
        pipeline.add_component(component1)
        pipeline.add_component(component2)

        # Execute pipeline
        result = pipeline.execute_pipeline("input data")

        # Check that components were called in order
        component1.process.assert_called_once_with("input data")
        component2.process.assert_called_once_with("processed by component1")

        # Check final result
        self.assertEqual(result, "processed by component2")


class TestFullPipelineIntegration(unittest.TestCase):
    """Test the full pipeline integration with mocked services"""

    def setUp(self):
        """Set up test environment"""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()

        # Create mock ApiFuncFramework
        self.mock_framework1 = MagicMock()
        self.mock_framework2 = MagicMock()

        # Create mock DynamicgRPCComponent
        self.mock_component1 = MagicMock()
        self.mock_component1.name = "json_to_html"
        self.mock_component1.process.return_value = "<html><body>Test HTML</body></html>"

        self.mock_component2 = MagicMock()
        self.mock
