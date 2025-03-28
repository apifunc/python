#!/usr/bin/env python
"""
Example usage of ApiFuncFramework
"""

import logging
import os
import sys
import json

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# Import the necessary components from apifunc
from apifunc.components import DynamicgRPCComponent
from apifunc.apifunc import ApiFuncConfig, ApiFuncFramework

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def json_to_html(json_data):
    """Convert JSON data to HTML"""
    try:
        # Parse JSON if it's a string
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data

        # Create a simple HTML representation
        html = "<html><body><h1>JSON Data</h1><ul>"
        for key, value in data.items():
            html += f"<li><strong>{key}:</strong> {value}</li>"
        html += "</ul></body></html>"

        return html
    except Exception as e:
        logger.error(f"Error converting JSON to HTML: {e}")
        return f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>"

def main():
    """Main function"""
    try:
        logger.info("Starting the apifunc example pipeline...")

        # Create framework with configuration
        config = ApiFuncConfig(
            proto_dir="./proto",
            generated_dir="./generated",
            port=50051  # Set the port here in the config
        )
        framework = ApiFuncFramework(config)

        # Register the function with the framework
        # The framework will create a DynamicgRPCComponent internally
        framework.register_function(json_to_html)

        # Start the gRPC server
        server = framework.start_server()

        logger.info(f"Server running on port {config.port}. Press Ctrl+C to stop.")
        server.wait_for_termination()

    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    except Exception as e:
        logger.error(f"Error processing: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
