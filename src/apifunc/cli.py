import argparse
import importlib
import logging
import os
import sys
from typing import List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(args: argparse.Namespace) -> None:
    """Run the pipeline with the specified components"""
    try:
        # Import framework components
        from apifunc.apifunc import ApiFuncConfig, ApiFuncFramework

        # Create framework instance
        config = ApiFuncConfig(
            proto_dir=args.proto_dir,
            generated_dir=args.generated_dir,
            port=args.port
        )
        framework = ApiFuncFramework(config)

        # Start server if requested
        if args.server:
            server = framework.start_server()
            logger.info(f"Server running on port {config.port}. Press Ctrl+C to stop.")
            try:
                server.wait_for_termination()
            except KeyboardInterrupt:
                server.stop(0)
                logger.info("Server stopped.")

    except ImportError as e:
        logger.error(f"Import error: {e}")
    except Exception as e:
        logger.error(f"Error running pipeline: {e}", exc_info=True)

def main(args: Optional[List[str]] = None) -> None:
    """Main entry point for the CLI"""
    parser = argparse.ArgumentParser(description="ApiFuncFramework CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a pipeline")
    run_parser.add_argument("--proto-dir", help="Directory for proto files")
    run_parser.add_argument("--generated-dir", help="Directory for generated code")
    run_parser.add_argument("--port", type=int, default=50051, help="Port for gRPC server")
    run_parser.add_argument("--server", action="store_true", help="Start gRPC server")
    run_parser.set_defaults(func=run_command)

    # Parse arguments
    parsed_args = parser.parse_args(args)

    # Run the appropriate command
    if hasattr(parsed_args, "func"):
        parsed_args.func(parsed_args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
