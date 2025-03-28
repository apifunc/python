#!/usr/bin/env python3
"""
Example of a pipeline with two gRPC services
"""

import logging
import json
import sys
import os
import base64
import time
import threading
# Add the src directory to the Python path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# Import the necessary components from apifunc
from apifunc.apifunc import ApiFuncConfig, ApiFuncFramework
from apifunc.json_to_html import json_to_html
from apifunc.html_to_pdf import html_to_pdf

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pipeline orchestrator class
class PipelineOrchestrator:
    """Class to orchestrate the execution of pipeline components"""

    def __init__(self):
        self.components = []

    def add_component(self, component):
        """Add a component to the pipeline"""
        self.components.append(component)

    def execute_pipeline(self, input_data):
        """Execute the pipeline with the given input data"""
        current_data = input_data

        for i, component in enumerate(self.components):
            logger.info(f"Executing component {i+1}/{len(self.components)}: {component.name}")
            current_data = component.process(current_data)

        return current_data

class DynamicgRPCComponent:
    """Component that calls a gRPC service"""

    def __init__(self, func, proto_dir, generated_dir):
        self.func = func
        self.name = func.__name__
        self.proto_dir = proto_dir
        self.generated_dir = generated_dir

        # Import the generated module dynamically
        import importlib.util
        import sys
        import os

        # Determine the module name from the function name
        module_name = f"{self.name}_pb2_grpc"
        module_path = os.path.join(generated_dir, f"{module_name}.py")

        # Load the module
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Also load the pb2 module
        pb2_module_name = f"{self.name}_pb2"
        pb2_module_path = os.path.join(generated_dir, f"{pb2_module_name}.py")

        pb2_spec = importlib.util.spec_from_file_location(pb2_module_name, pb2_module_path)
        pb2_module = importlib.util.module_from_spec(pb2_spec)
        sys.modules[pb2_module_name] = pb2_module
        pb2_spec.loader.exec_module(pb2_module)

        # Store references to the modules
        self.grpc_module = module
        self.pb2_module = pb2_module

        # Create a gRPC channel and stub
        import grpc

        # Get the port from the function name (assuming convention)
        port = 50051 if "json_to_html" in self.name else 50053

        self.channel = grpc.insecure_channel(f'localhost:{port}')

        # Find the stub class by examining the module attributes
        stub_class = None
        for attr_name in dir(self.grpc_module):
            if attr_name.endswith('Stub'):
                stub_class = getattr(self.grpc_module, attr_name)
                break

        if not stub_class:
            raise ValueError(f"Could not find Stub class in {module_name}")

        self.stub = stub_class(self.channel)

    def process(self, data):
        """Process data through the gRPC service"""
        logger.info(f"Calling gRPC service: {self.name}")

        # Find the request class by examining the module attributes
        request_class = None
        for attr_name in dir(self.pb2_module):
            if attr_name.endswith('Request'):
                request_class = getattr(self.pb2_module, attr_name)
                break

        if not request_class:
            raise ValueError(f"Could not find Request class in {self.pb2_module.__name__}")

        # Convert input data to appropriate format
        if isinstance(data, dict):
            # For JSON to HTML
            request = request_class(json_data=json.dumps(data))
        elif isinstance(data, str):
            # For HTML to PDF
            request = request_class(html_content=data)
        else:
            # Handle binary data
            request = request_class(content=data)

        # Find the method to call on the stub
        method_to_call = None
        for method_name in dir(self.stub):
            if not method_name.startswith('_'):
                method_to_call = method_name
                break

        if not method_to_call:
            raise ValueError(f"Could not find method to call on stub")

        # Call the service
        response = getattr(self.stub, method_to_call)(request)

        # Extract and return the response data
        if hasattr(response, 'html_content'):
            return response.html_content
        elif hasattr(response, 'pdf_data'):
            return response.pdf_data
        else:
            # Try to find a field that might contain the response
            for field_name in dir(response):
                if not field_name.startswith('_') and not callable(getattr(response, field_name)):
                    return getattr(response, field_name)

            # If no specific field found, return the whole response
            return response

def main():
    # Variables to store server instances for later shutdown
    json_html_server = None
    html_pdf_server = None

    try:
        logger.info("Starting the apifunc example pipeline with two services...")

        # Sample data
        sample_data = {
            "title": "Sample Report",
            "author": "APIFunc",
            "date": "2025-03-28",
            "content": "This is a sample report generated by APIFunc."
        }

        # Create configurations for both services
        json_html_config = ApiFuncConfig(
            proto_dir="./proto/json_html",
            generated_dir="./generated/json_html",
            port=50053
        )

        html_pdf_config = ApiFuncConfig(
            proto_dir="./proto/html_pdf",
            generated_dir="./generated/html_pdf",
            port=50054
        )

        # Create framework instances
        json_html_framework = ApiFuncFramework(json_html_config)
        html_pdf_framework = ApiFuncFramework(html_pdf_config)

        # Register functions with frameworks
        json_html_framework.register_function(json_to_html)
        html_pdf_framework.register_function(html_to_pdf)

        # Start servers in background threads
        logger.info(f"Starting JSON-to-HTML server on port {json_html_config.port}")
        json_html_thread = threading.Thread(target=json_html_framework.start_server)
        json_html_thread.daemon = True
        json_html_thread.start()
        # We won't have a server reference to stop later
        json_html_server = None

        logger.info(f"Starting HTML-to-PDF server on port {html_pdf_config.port}")
        html_pdf_thread = threading.Thread(target=html_pdf_framework.start_server)
        html_pdf_thread.daemon = True
        html_pdf_thread.start()
        # We won't have a server reference to stop later
        html_pdf_server = None

        # Give servers time to start
        time.sleep(1)

        # Create components that use the gRPC services
        json_html_component = DynamicgRPCComponent(
            json_to_html,
            proto_dir=json_html_config.proto_dir,
            generated_dir=json_html_config.generated_dir
        )

        html_pdf_component = DynamicgRPCComponent(
            html_to_pdf,
            proto_dir=html_pdf_config.proto_dir,
            generated_dir=html_pdf_config.generated_dir
        )

        # Create and execute pipeline
        pipeline = PipelineOrchestrator()
        pipeline.add_component(json_html_component)
        pipeline.add_component(html_pdf_component)

        # Execute pipeline
        logger.info("Executing pipeline...")
        result = pipeline.execute_pipeline(sample_data)

        # Decode the base64 PDF data
        pdf_data = base64.b64decode(result)

        # Save the result
        output_file = "output.pdf"
        with open(output_file, "wb") as f:
            f.write(pdf_data)

        logger.info(f"Pipeline executed successfully. Output saved to {output_file}")

    except Exception as e:
        logger.error(f"Error processing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Shutdown the servers after pipeline execution
        if json_html_server:
            logger.info("Shutting down JSON-to-HTML server...")
            json_html_server.stop(0)  # 0 means stop immediately
        else:
            logger.info("JSON-to-HTML server running in background thread")

        if html_pdf_server:
            logger.info("Shutting down HTML-to-PDF server...")
            html_pdf_server.stop(0)  # 0 means stop immediately
        else:
            logger.info("HTML-to-PDF server running in background thread")

        logger.info("All services have been shut down.")

if __name__ == "__main__":
    main()
