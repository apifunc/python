import os
import sys
import inspect
import importlib
import json
import socket
from typing import Any, Dict, List, Optional, Callable, Type
import logging

import grpc
from concurrent import futures
import grpc_tools.protoc

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


class ModularPipelineInterface:
    """
    Interfejs dla modularnych komponentów pipeline
    """

    def validate_input(self, input_data: Any) -> bool:
        """
        Walidacja danych wejściowych
        """
        raise NotImplementedError("Metoda validate_input musi być zaimplementowana")

    def transform(self, input_data: Any) -> Any:
        """
        Transformacja danych
        """
        raise NotImplementedError("Metoda transform musi być zaimplementowana")


class gRPCServiceGenerator:
    """
    Generator usług gRPC dla komponentów pipeline
    """

    @staticmethod
    def generate_proto_for_function(func: Callable) -> str:
        """
        Automatyczne generowanie definicji protobuf dla funkcji

        :param func: Funkcja do analizy
        :return: Treść pliku .proto
        """
        logger.info(f"Generating proto definition for function: {func.__name__}")
        # Pobranie sygnnatury funkcji
        signature = inspect.signature(func)
        logger.debug(f"Function signature: {signature}")

        # Nazwa usługi bazowana na nazwie funkcji
        service_name = f"{func.__name__.capitalize()}Service"
        logger.debug(f"Service name: {service_name}")

        # Analiza parametrów wejściowych
        input_type = "google.protobuf.Struct"
        output_type = "google.protobuf.Struct"

        # Generowanie definicji protobuf
        proto_content = f"""
        syntax = "proto3";

        import "google/protobuf/struct.proto";

        package modularpipeline;

        service {service_name} {{
            rpc Transform(google.protobuf.Struct) returns (google.protobuf.Struct) {{}}
        }}
        """
        logger.debug(f"Generated proto content: {proto_content}")
        return proto_content

    @staticmethod
    def compile_proto(proto_content: str, output_dir: str = 'generated_protos'):
        """
        Kompilacja wygenerowanego pliku proto

        :param proto_content: Treść pliku proto
        :param output_dir: Katalog wyjściowy
        """
        logger.info(f"Compiling proto file to directory: {output_dir}")
        # Utworzenie katalogu
        os.makedirs(output_dir, exist_ok=True)
        logger.debug(f"Created output directory: {output_dir}")

        # Zapis pliku proto
        proto_path = os.path.join(output_dir, 'dynamic_service.proto')
        with open(proto_path, 'w') as f:
            f.write(proto_content)
        logger.debug(f"Wrote proto file to: {proto_path}")

        # Get the project root directory (where google/protobuf/struct.proto is located)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
        logger.debug(f"Project root directory: {project_root}")

        # Kompilacja proto
        protoc_args = [
            'grpc_tools.protoc',
            f'-I{output_dir}',
            f'-I{project_root}',  # Add project root to include path to find google/protobuf/struct.proto
            f'--python_out={output_dir}',
            f'--grpc_python_out={output_dir}',
            proto_path
        ]
        logger.debug(f"Protoc arguments: {protoc_args}")

        try:
            result = grpc_tools.protoc.main(protoc_args)
            if result == 0:
                logger.info("Proto compilation successful")
            else:
                logger.error(f"Proto compilation failed with exit code: {result}")
        except Exception as e:
            logger.exception(f"Error during proto compilation: {str(e)}")


class DynamicgRPCComponent(ModularPipelineInterface):
    """
    Dynamiczny komponent pipeline z interfejsem gRPC
    """

    def __init__(self, transform_func: Callable, port: int = None):
        """
        Inicjalizacja komponentu

        :param transform_func: Funkcja transformacji
        :param port: Określony port dla serwera gRPC (opcjonalny)
        """
        logger.info(f"Initializing dynamic gRPC component for function: {transform_func.__name__}")
        self.transform_func = transform_func

        # Użyj określonego portu lub znajdź dostępny, jeśli nie podano
        if port is not None:
            self.port = port
            logger.info(f"Using specified port {self.port} for gRPC service: {transform_func.__name__}")
        else:
            self.port = self._get_available_port()
            logger.info(f"Assigned random port {self.port} for gRPC service: {transform_func.__name__}")

        # Initialize server
        self.server = None

        # Generowanie usługi gRPC
        proto_content = gRPCServiceGenerator.generate_proto_for_function(transform_func)
        gRPCServiceGenerator.compile_proto(proto_content)
        logger.info(f"gRPC service generated for function: {transform_func.__name__}")

        # Start the gRPC server
        self._start_grpc_server()

    def _get_available_port(self):
        """Find an available port to use"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))  # Bind to a random available port
            return s.getsockname()[1]

    def _start_grpc_server(self):
        """Start a gRPC server for this component"""
        try:
            # Create a server
            self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

            # Add the service to the server
            # Note: In a real implementation, you would need to import the generated
            # service and add it to the server. For now, we'll just log it.
            service_name = f"{self.transform_func.__name__.capitalize()}Service"

            # Bind to the port
            server_address = f'[::]:{self.port}'
            self.server.add_insecure_port(server_address)

            # Start the server
            self.server.start()

            logger.info(f"Started gRPC server for {service_name} on port {self.port}")
        except Exception as e:
            logger.exception(f"Failed to start gRPC server for {self.transform_func.__name__}: {str(e)}")

    def stop_server(self):
        """Stop the gRPC server"""
        if self.server:
            logger.info(f"Stopping gRPC server for {self.transform_func.__name__} on port {self.port}")
            self.server.stop(0)  # Stop immediately
            self.server = None

    def validate_input(self, input_data: Any) -> bool:
        """
        Domyślna walidacja danych wejściowych
        """
        is_valid = isinstance(input_data, (dict, str, list))
        logger.debug(f"Input validation result: {is_valid} for data type: {type(input_data)}")
        return is_valid

    def transform(self, input_data: Any) -> Any:
        """
        Wywołanie funkcji transformacji
        """
        logger.info(f"Transforming data with function: {self.transform_func.__name__}")
        logger.debug(f"Input data: {input_data}")

        if not self.validate_input(input_data):
            error_msg = f"Invalid input data type: {type(input_data)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            result = self.transform_func(input_data)
            logger.debug(f"Transform result: {result}")
            return result
        except Exception as e:
            logger.exception(f"Error during transformation: {str(e)}")
            raise


class PipelineOrchestrator:
    """
    Orkiestracja potoków przetwarzania z dynamicznym generowaniem usług gRPC
    """

    def __init__(self):
        """
        Inicjalizacja orkiestratora
        """
        self.components: List[DynamicgRPCComponent] = []
        logger.info("Initialized Pipeline Orchestrator")

    def add_component(self, component: DynamicgRPCComponent):
        """
        Dodanie komponentu do potoku

        :param component: Komponent pipeline
        """
        self.components.append(component)
        logger.info(f"Added component to pipeline: {component.transform_func.__name__} (gRPC port: {component.port})")
        return self

    def execute_pipeline(self, initial_data: Any):
        """
        Wykonanie potoku przetwarzania

        :param initial_data: Dane początkowe
        :return: Wynik końcowy
        """
        logger.info("Starting pipeline execution")
        logger.debug(f"Initial data: {initial_data}")

        current_data = initial_data

        for i, component in enumerate(self.components):
            logger.info(f"Executing component {i+1}/{len(self.components)}: {component.transform_func.__name__} (gRPC port: {component.port})")
            try:
                current_data = component.transform(current_data)
                logger.debug(f"Component {i+1} output: {current_data}")
            except Exception as e:
                logger.error(f"Pipeline execution failed at component {i+1}: {str(e)}")
                raise

        logger.info("Pipeline execution completed successfully")
        return current_data

    def shutdown(self):
        """Shutdown all gRPC servers in the pipeline"""
        logger.info("Shutting down all gRPC servers in the pipeline")
        for component in self.components:
            component.stop_server()
