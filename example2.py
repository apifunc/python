import logging
import os
import sys
import threading
import time
from typing import Callable

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from apifunc.apifunc import ApiFuncConfig, ApiFuncFramework, DynamicgRPCComponent, PipelineOrchestrator
from apifunc.apifunc import json_to_html, html_to_pdf

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def start_server(framework: ApiFuncFramework, func: Callable, proto_dir: str, generated_dir: str):
    """
    Start the gRPC server in a separate thread.

    Args:
        framework (ApiFuncFramework): The ApiFuncFramework instance.
        func (Callable): The function to expose as a gRPC service.
        proto_dir (str): Directory for proto files.
        generated_dir (str): Directory for generated code.
    """
    try:
        server = framework.start_server(func, proto_dir, generated_dir)
        server.wait_for_termination()
    except Exception as e:
        logger.error(f"Error processing: {e}")


def main():
    """
    Main function to run the example pipeline with two services.
    """
    logger.info("Starting the apifunc example pipeline with two services...")

    # Configuration for JSON-to-HTML service
    json_html_config = ApiFuncConfig(
        proto_dir=os.path.abspath("./proto/json_html"),
        generated_dir=os.path.abspath("./generated/json_html"),
        port=50051
    )
    logger.info(f"Proto files directory: {json_html_config.proto_dir}")
    logger.info(f"Generated code directory: {json_html_config.generated_dir}")

    # Configuration for HTML-to-PDF service
    html_pdf_config = ApiFuncConfig(
        proto_dir=os.path.abspath("./proto/html_pdf"),
        generated_dir=os.path.abspath("./generated/html_pdf"),
        port=50052
    )
    logger.info(f"Proto files directory: {html_pdf_config.proto_dir}")
    logger.info(f"Generated code directory: {html_pdf_config.generated_dir}")

    # Create ApiFuncFramework instances
    json_html_framework = ApiFuncFramework(json_html_config)
    html_pdf_framework = ApiFuncFramework(html_pdf_config)

    # Register functions
    json_html_framework.register_function(json_to_html, json_html_config.proto_dir, json_html_config.generated_dir)
    html_pdf_framework.register_function(html_to_pdf, html_pdf_config.proto_dir, html_pdf_config.generated_dir)

    # Start servers in separate threads
    json_html_thread = threading.Thread(target=start_server,
                                        args=(json_html_framework, json_to_html, json_html_config.proto_dir,
                                              json_html_config.generated_dir))
    html_pdf_thread = threading.Thread(target=start_server,
                                       args=(html_pdf_framework, html_to_pdf, html_pdf_config.proto_dir,
                                             html_pdf_config.generated_dir))

    json_html_thread.start()
    logger.info(f"Starting JSON-to-HTML server on port {json_html_config.port}")
    html_pdf_thread.start()
    logger.info(f"Starting HTML-to-PDF server on port {html_pdf_config.port}")

    # Create DynamicgRPCComponents
    try:
        json_html_component = DynamicgRPCComponent(
            json_to_html,
            proto_dir=json_html_config.proto_dir,
            generated_dir=json_html_config.generated_dir
        )
    except Exception as e:
        logger.error(f"Error processing: {e}")

    html_pdf_component = DynamicgRPCComponent(
        html_to_pdf,
        proto_dir=html_pdf_config.proto_dir,
        generated_dir=html_pdf_config.generated_dir
    )

    # Create PipelineOrchestrator
    pipeline = PipelineOrchestrator()

    # Add components to the pipeline
    pipeline.add_component(json_html_component).add_component(html_pdf_component)

    # Sample input data
    sample_data = {
        "nazwa": "Przykładowy Raport",
        "data": "2023-11-20",
        "wartość": 123.45
    }

    # Execute the pipeline
    result = pipeline.execute_pipeline(sample_data)

    # Wait for threads to finish
    logger.info("JSON-to-HTML server running in background thread")
    logger.info("HTML-to-PDF server running in background thread")
    time.sleep(2)
    logger.info("All services have been shut down.")


if __name__ == "__main__":
    main()