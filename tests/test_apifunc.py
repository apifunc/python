import unittest
import json
import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.apifunc.apifunc import (
    json_to_html,
    html_to_pdf,
    DynamicgRPCComponent,
    PipelineOrchestrator,
    ModularPipelineInterface
)


class TestModularPipelineInterface(unittest.TestCase):
    def test_abstract_methods(self):
        # Should raise NotImplementedError when instantiated directly
        interface = ModularPipelineInterface()
        with self.assertRaises(NotImplementedError):
            interface.validate_input({})
        with self.assertRaises(NotImplementedError):
            interface.transform({})


class TestJsonToHtml(unittest.TestCase):
    def test_json_to_html_conversion(self):
        test_data = {"name": "Test", "value": 123}
        html_result = json_to_html(test_data)

        # Check if the HTML contains the test data
        self.assertIn("Test", html_result)
        self.assertIn("123", html_result)
        self.assertIn("<html>", html_result)
        self.assertIn("</html>", html_result)


class TestDynamicgRPCComponent(unittest.TestCase):
    def test_component_initialization(self):
        # Test that a component can be initialized with a transform function
        component = DynamicgRPCComponent(json_to_html)
        self.assertEqual(component.transform_func, json_to_html)

    def test_validate_input(self):
        component = DynamicgRPCComponent(json_to_html)
        self.assertTrue(component.validate_input({"test": "data"}))
        self.assertTrue(component.validate_input("test string"))
        self.assertTrue(component.validate_input([1, 2, 3]))
        self.assertFalse(component.validate_input(123))

    def test_transform(self):
        component = DynamicgRPCComponent(json_to_html)
        test_data = {"name": "Test", "value": 123}
        result = component.transform(test_data)
        self.assertIsInstance(result, str)
        self.assertIn("Test", result)


class TestPipelineOrchestrator(unittest.TestCase):
    def test_pipeline_execution(self):
        # Create a simple pipeline with two components
        def first_transform(data):
            return data + " transformed once"

        def second_transform(data):
            return data + " and twice"

        pipeline = PipelineOrchestrator()
        pipeline.add_component(DynamicgRPCComponent(first_transform))
        pipeline.add_component(DynamicgRPCComponent(second_transform))

        result = pipeline.execute_pipeline("Initial data")
        self.assertEqual(result, "Initial data transformed once and twice")

    def test_json_to_html_pipeline(self):
        test_data = {"name": "Test Report", "value": 123}

        pipeline = PipelineOrchestrator()
        pipeline.add_component(DynamicgRPCComponent(json_to_html))

        result = pipeline.execute_pipeline(test_data)
        self.assertIsInstance(result, str)
        self.assertIn("Test Report", result)
        self.assertIn("123", result)

    def test_full_pipeline(self):
        # This test requires weasyprint to be installed
        try:
            import weasyprint

            test_data = {"name": "Test Report", "value": 123}

            pipeline = PipelineOrchestrator()
            pipeline.add_component(DynamicgRPCComponent(json_to_html))
            pipeline.add_component(DynamicgRPCComponent(html_to_pdf))

            result = pipeline.execute_pipeline(test_data)
            self.assertIsInstance(result, bytes)
            self.assertTrue(len(result) > 0)

            # Optionally save the PDF for manual inspection
            # with open("test_output.pdf", "wb") as f:
            #     f.write(result)

        except ImportError:
            self.skipTest("weasyprint not installed, skipping PDF test")


if __name__ == "__main__":
    unittest.main()
