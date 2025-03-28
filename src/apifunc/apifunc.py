import os
import sys
import inspect
import importlib
import json
from typing import Any, Dict, List, Optional, Callable, Type
import logging

import grpc
from concurrent import futures
import grpc_tools.protoc

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))


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
        # Pobranie sygnnatury funkcji
        signature = inspect.signature(func)

        # Nazwa usługi bazowana na nazwie funkcji
        service_name = f"{func.__name__.capitalize()}Service"

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

        return proto_content

    @staticmethod
    def compile_proto(proto_content: str, output_dir: str = 'generated_protos'):
        """
        Kompilacja wygenerowanego pliku proto

        :param proto_content: Treść pliku proto
        :param output_dir: Katalog wyjściowy
        """
        # Utworzenie katalogu
        os.makedirs(output_dir, exist_ok=True)

        # Zapis pliku proto
        proto_path = os.path.join(output_dir, 'dynamic_service.proto')
        with open(proto_path, 'w') as f:
            f.write(proto_content)

        # Get the project root directory (where google/protobuf/struct.proto is located)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
        
        # Kompilacja proto
        protoc_args = [
            'grpc_tools.protoc',
            f'-I{output_dir}',
            f'-I{project_root}',  # Add project root to include path to find google/protobuf/struct.proto
            f'--python_out={output_dir}',
            f'--grpc_python_out={output_dir}',
            proto_path
        ]

        grpc_tools.protoc.main(protoc_args)


class DynamicgRPCComponent(ModularPipelineInterface):
    """
    Dynamiczny komponent pipeline z interfejsem gRPC
    """

    def __init__(self, transform_func: Callable):
        """
        Inicjalizacja komponentu

        :param transform_func: Funkcja transformacji
        """
        self.transform_func = transform_func

        # Generowanie usługi gRPC
        proto_content = gRPCServiceGenerator.generate_proto_for_function(transform_func)
        gRPCServiceGenerator.compile_proto(proto_content)

    def validate_input(self, input_data: Any) -> bool:
        """
        Domyślna walidacja danych wejściowych
        """
        return isinstance(input_data, (dict, str, list))

    def transform(self, input_data: Any) -> Any:
        """
        Wywołanie funkcji transformacji
        """
        if not self.validate_input(input_data):
            raise ValueError("Nieprawidłowe dane wejściowe")

        return self.transform_func(input_data)


class PipelineOrchestrator:
    """
    Orkiestracja potoków przetwarzania z dynamicznym generowaniem usług gRPC
    """

    def __init__(self):
        """
        Inicjalizacja orkiestratora
        """
        self.components: List[DynamicgRPCComponent] = []

    def add_component(self, component: DynamicgRPCComponent):
        """
        Dodanie komponentu do potoku

        :param component: Komponent pipeline
        """
        self.components.append(component)
        return self

    def execute_pipeline(self, initial_data: Any):
        """
        Wykonanie potoku przetwarzania

        :param initial_data: Dane początkowe
        :return: Wynik końcowy
        """
        current_data = initial_data

        for component in self.components:
            current_data = component.transform(current_data)

        return current_data



