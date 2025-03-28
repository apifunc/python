# cli.py
import argparse
import logging
import os
import sys

from apifunc import DynamicgRPCComponent, PipelineOrchestrator, json_to_html

# Add the directory containing apifunc.py to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))



def example_usage(output_file='raport.pdf', html_to_pdf_service=None):
    """
    Przykładowe użycie modularnego frameworka pipeline
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    sample_data = {
        "nazwa": "Przykładowy Raport",
        "wartość": 1000,
        "kategoria": "Sprzedaż"
    }

    try:
        # Utworzenie komponentów
        json_to_html_component = DynamicgRPCComponent(json_to_html)
        html_to_pdf_component = DynamicgRPCComponent(html_to_pdf_service)

        # Utworzenie i konfiguracja potoku
        pipeline = PipelineOrchestrator()
        pipeline.add_component(json_to_html_component).add_component(html_to_pdf_component)

        # Wykonanie potoku
        result = pipeline.execute_pipeline(sample_data)
        logger.info("Przetwarzanie zakończone sukcesem")

        # Zapis pliku PDF
        with open(output_file, 'wb') as f:
            f.write(result)

        logger.info(f"Plik PDF został zapisany: {output_file}")

    except Exception as e:
        logger.error(f"Błąd przetwarzania: {e}")



def main():
    """
    Main function for the apifunc CLI.
    """
    parser = argparse.ArgumentParser(
        prog='apifunc',
        description='Command-line interface for the apifunc modular pipeline framework.'
    )

    # Subparser for the 'run' command
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # 'run' command
    run_parser = subparsers.add_parser('run', help='Run the example pipeline')
    run_parser.add_argument(
        '-o', '--output',
        default='raport.pdf',
        help='Output file name for the generated PDF (default: raport.pdf)'
    )

    # Parse arguments
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    # Execute the command
    if args.command == 'run':
        logger.info("Starting the apifunc example pipeline...")
        try:
            # Modify example_usage to accept output file name
            example_usage(output_file=args.output)
            logger.info(f"Pipeline completed successfully. Output saved to {args.output}")
        except Exception as e:
            logger.error(f"Error during pipeline execution: {e}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
