#!/usr/bin/env python3
import logging
import json
import sys
import os

# Add the src directory to the Python path if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))
from apifunc.json_to_html import json_to_html
from apifunc.html_to_pdf import html_to_pdf

from apifunc.apifunc import (
    DynamicgRPCComponent,
    PipelineOrchestrator
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("Starting the apifunc example pipeline...")

        # Sample data
        sample_data = {
            "title": "Sample Report",
            "author": "APIFunc",
            "date": "2025-03-28",
            "content": "This is a sample report generated by APIFunc."
        }

        # Create pipeline components
        # Przykład użycia z określonym portem
        json_html_component = DynamicgRPCComponent(json_to_html, port=50051)
        html_pdf_component = DynamicgRPCComponent(html_to_pdf, port=50052)

        # Create and execute pipeline
        pipeline = PipelineOrchestrator()
        pipeline.add_component(json_html_component)
        pipeline.add_component(html_pdf_component)

        # Execute pipeline
        result = pipeline.execute_pipeline(sample_data)

        # Save the result
        with open("output.pdf", "wb") as f:
            f.write(result)

        logger.info("Pipeline executed successfully. Output saved to output.pdf")

    except Exception as e:
        logger.error(f"Error processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
