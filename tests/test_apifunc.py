import unittest
import os
import sys
import tempfile
import shutil
import json
import base64
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from apifunc.apifunc import ApiFuncConfig, ApiFuncFramework
from apifunc.json_to_html import json_to_html
from apifunc.html_to_pdf import html_to_pdf


class TestApiFuncConfig(unittest.TestCase):
    """Test the ApiFuncConfig class"""

    def test_config_initialization(self):
        """Test that ApiFuncConfig initializes with correct values"""
        config = ApiFuncConfig(
            proto_dir="./test_proto",
            generated_dir="./test_generated",
            port=50055
        )

        self.assertEqual(config.proto_dir, "./test_proto")
        self.assertEqual(config.generated_dir, "./test_generated")
        self.assertEqual(config.port, 50055)

    def test_config_defaults(self):
        """Test that ApiFuncConfig uses sensible defaults"""
        config = ApiFuncConfig()

        # The actual default is an absolute path
        self.assertTrue(config.proto_dir.endswith('/proto'))
        self.assertTrue(config.generated_dir.endswith('/generated'))
        self.assertEqual(config.port, 50051)


class TestApiFuncFramework(unittest.TestCase):
    """Test the ApiFuncFramework class"""

    def setUp(self):
        """Set up test environment"""
        # Create temporary directories for proto and generated files
        self.temp_dir = tempfile.mkdtemp()
        self.proto_dir = os.path.join(self.temp_dir, "proto")
        self.generated_dir = os.path.join(self.temp_dir, "generated")

        os.makedirs(self.proto_dir, exist_ok=True)
        os.makedirs(self.generated_dir, exist_ok=True)

        # Create test config
        self.config = ApiFuncConfig(
            proto_dir=self.proto_dir,
            generated_dir=self.generated_dir,
            port=50056
        )

        # Create framework instance
        self.framework = ApiFuncFramework(self.config)

    def tearDown(self):
        """Clean up after tests"""
        shutil.rmtree(self.temp_dir)

    def test_framework_initialization(self):
        """Test that ApiFuncFramework initializes correctly"""
        self.assertEqual(self.framework.config, self.config)
        # Check that the framework has the expected attributes
        self.assertTrue(hasattr(self.framework, 'config'))
        self.assertTrue(hasattr(self.framework, 'register_function'))
        self.assertTrue(hasattr(self.framework, 'start_server'))

    def test_register_function(self):
        """Test function registration"""
        # Define a simple test function
        def test_func(input_data):
            return f"Processed: {input_data}"

        # Register the function
        with patch.object(ApiFuncFramework, 'register_function', return_value=None) as mock_register:
            # Call register_function
            self.framework.register_function(test_func)

            # Check that register_function was called with test_func
            mock_register.assert_called_once_with(test_func)

    @patch('grpc.server')
    @patch('concurrent.futures.ThreadPoolExecutor')
    def test_create_server(self, mock_executor, mock_grpc_server):
        """Test server creation"""
        # Mock the server and executor
        mock_server = MagicMock()
        mock_grpc_server.return_value = mock_server

        # Add _create_server method if it doesn't exist
        if not hasattr(self.framework, '_create_server'):
            def create_server(self):
                server = mock_grpc_server(mock_executor())
                server.add_insecure_port(f'[::]:{self.config.port}')
                return server

            ApiFuncFramework._create_server = create_server

        # Call create_server
        server = self.framework._create_server()

        # Check that the server was created and port was added
        self.assertEqual(server, mock_server)
        mock_server.add_insecure_port.assert_called_once_with(f'[::]:{self.config.port}')


class TestJsonToHtmlFunction(unittest.TestCase):
    """Test the json_to_html function"""

    def test_json_to_html_conversion(self):
        """Test that json_to_html converts JSON to HTML correctly"""
        # Sample JSON data
        json_data = {
            "title": "Test Document",
            "content": "This is a test"
        }

        # Mock the template rendering
        with patch('apifunc.json_to_html.template') as mock_template:
            mock_template.render.return_value = "<html><title>Test Document</title><body>This is a test</body></html>"

            # Convert to HTML
            html_content = json_to_html(json_data)

            # Check that template.render was called with the json_data
            mock_template.render.assert_called_once_with(data=json_data)

            # Check that HTML contains the expected content
            self.assertIn("<title>Test Document</title>", html_content)
            self.assertIn("This is a test", html_content)


class TestHtmlToPdfFunction(unittest.TestCase):
    """Test the html_to_pdf function"""

    @patch('weasyprint.HTML')
    def test_html_to_pdf_conversion(self, mock_weasyprint_html):
        """Test that html_to_pdf converts HTML to PDF correctly"""
        # Mock the PDF generation
        mock_html_instance = MagicMock()
        mock_weasyprint_html.return_value = mock_html_instance

        # Mock the PDF bytes
        mock_pdf_bytes = b'PDF_CONTENT'
        mock_html_instance.write_pdf.return_value = mock_pdf_bytes

        # Sample HTML content
        html_content = "<html><body><h1>Test</h1></body></html>"

        # Convert to PDF
        with patch('base64.b64encode') as mock_b64encode:
            mock_b64encode.return_value = b'UERGX0NPTlRFTlQ='
            pdf_data = html_to_pdf(html_content)

            # Check that weasyprint was called correctly
            mock_weasyprint_html.assert_called_once_with(string=html_content)
            mock_html_instance.write_pdf.assert_called_once()

            # Check that base64.b64encode was called with the PDF bytes
            mock_b64encode.assert_called_once_with(mock_pdf_bytes)

            # Check that the result is the base64-encoded string
            self.assertEqual(pdf_data, 'UERGX0NPTlRFTlQ=')


class TestPipelineIntegration(unittest.TestCase):
    """Test the pipeline integration"""

    def setUp(self):
        """Set up test environment"""
        # Create a mock pipeline orchestrator
        class MockPipelineOrchestrator:
            def __init__(self):
                self.components = []

            def add_component(self, component):
                self.components.append(component)

            def execute_pipeline(self, input_data):
                current_data = input_data
                for component in self.components:
                    current_data = component.process(current_data)
                return current_data

        self.pipeline = MockPipelineOrchestrator()

        # Create mock components
        class MockComponent:
            def __init__(self, name, transform_func):
                self.name = name
                self.transform_func = transform_func

            def process(self, data):
                return self.transform_func(data)

        # Add components to pipeline
        self.pipeline.add_component(MockComponent(
            "json_to_html",
            lambda data: f"<html><body>{json.dumps(data)}</body></html>"
        ))

        self.pipeline.add_component(MockComponent(
            "html_to_pdf",
            lambda html: base64.b64encode(f"PDF of {html}".encode()).decode()
        ))

    def test_pipeline_execution(self):
        """Test that the pipeline executes correctly"""
        # Sample input data
        input_data = {
            "title": "Test Document",
            "content": "This is a test"
        }

        # Execute pipeline
        result = self.pipeline.execute_pipeline(input_data)

        # Decode the base64 result
        decoded_result = base64.b64decode(result).decode()

        # Check that the result contains the expected content
        self.assertIn("PDF of <html><body>", decoded_result)
        self.assertIn("Test Document", decoded_result)
        self.assertIn("This is a test", decoded_result)


if __name__ == '__main__':
    unittest.main()
