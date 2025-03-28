import argparse
import logging
import sys
import traceback
import datetime

# Set up logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from apifunc import DynamicgRPCComponent, PipelineOrchestrator, json_to_html
except ImportError as e:
    logger.error(f"Import error: {e}")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='apifunc CLI tool')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Add 'run' command
    run_parser = subparsers.add_parser('run', help='Run the pipeline')
    run_parser.add_argument('-o', '--output', required=True, help='Output file path')

    args = parser.parse_args()

    if args.command == 'run':
        try:
            logger.info("Starting the apifunc example pipeline...")

            # Debug: Print available components
            logger.debug(f"DynamicgRPCComponent: {DynamicgRPCComponent}")
            logger.debug(f"PipelineOrchestrator: {PipelineOrchestrator}")

            # Create pipeline components with detailed error handling
            try:
                # Define a transform function
                def transform_data(data):
                    # Process the data as needed
                    return data

                # Create the component with the required transform_func
                grpc_component = DynamicgRPCComponent(transform_func=transform_data)
                logger.debug(f"Created gRPC component: {grpc_component}")
            except Exception as e:
                logger.error(f"Error creating gRPC component: {e}")
                logger.error(traceback.format_exc())
                sys.exit(1)

            try:
                orchestrator = PipelineOrchestrator()
                logger.debug(f"Created orchestrator: {orchestrator}")
            except Exception as e:
                logger.error(f"Error creating orchestrator: {e}")
                logger.error(traceback.format_exc())
                sys.exit(1)

            # Add component to pipeline
            try:
                orchestrator.add_component(grpc_component)
                logger.debug("Added gRPC component to orchestrator")
            except Exception as e:
                logger.error(f"Error adding component to pipeline: {e}")
                logger.error(traceback.format_exc())
                sys.exit(1)

            # Execute pipeline
            try:
                # Create some initial data for the pipeline
                initial_data = {
                    "timestamp": str(datetime.datetime.now()),
                    "source": "CLI",
                    "version": "0.1.6",  # Based on your CHANGELOG.md
                    "data": {}  # Add any specific data needed for your pipeline
                }

                result = orchestrator.execute_pipeline(initial_data)
                logger.debug(f"Pipeline execution result: {result}")
            except Exception as e:
                logger.error(f"Error executing pipeline: {e}")
                logger.error(traceback.format_exc())
                sys.exit(1)

            # Generate report
            try:
                html_content = json_to_html(result)
                logger.debug("Generated HTML content")
            except Exception as e:
                logger.error(f"Error generating HTML: {e}")
                logger.error(traceback.format_exc())
                sys.exit(1)

            # Save output
            try:
                with open(args.output, 'w') as f:
                    f.write(html_content)
                logger.info(f"Pipeline completed successfully. Output saved to {args.output}")
            except Exception as e:
                logger.error(f"Error saving output: {e}")
                logger.error(traceback.format_exc())
                sys.exit(1)

        except Exception as e:
            logger.error(f"Błąd przetwarzania: {e}")
            logger.error(traceback.format_exc())
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
