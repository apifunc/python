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
from jinja2 import Template
import weasyprint
from google.protobuf.struct_pb2 import Struct
import google.protobuf
import time
import threading


class ApiFuncConfig:
    """Configuration class for ApiFuncFramework."""

    def __init__(self, proto_dir: str = None, generated_dir: str = None, port: int = 50051):
        """
        Initialize ApiFuncConfig.

        Args:
            proto_dir (str): Directory for proto files.
            generated_dir (str): Directory for generated code.
            port (int): Port for the gRPC server.
        """
        self.proto_dir = proto_dir or os.path.abspath("./proto")
        self.generated_dir = generated_dir or os.path.abspath("./generated")
        self.port = port


class ApiFuncFramework:
    """Framework for creating gRPC services from functions."""

    def __init__(self, config: ApiFuncConfig):
        """
        Initialize ApiFuncFramework.

        Args:
            config (ApiFuncConfig): Configuration object.
        """
        self.config = config
        self.registered_functions = {}
        self.logger = logging.getLogger(__name__)

    def register_function(self, func: Callable, proto_dir: str, generated_dir: str):
        """
        Register a function to be exposed as a gRPC service.

        Args:
            func (Callable): The function to register.
            proto_dir (str): Directory for proto files.
            generated_dir (str): Directory for generated code.
        """
        self.logger.info(f"Registering function: {func.__module__}.{func.__name__}")

        self.registered_functions[func.__name__] = func
        self._generate_proto(func, proto_dir)
        self._compile_proto(func, proto_dir, generated_dir)

    def _generate_proto(self, func: Callable, proto_dir: str):
        """
        Generate a .proto file for the given function.

        Args:
            func (Callable): The function to generate a .proto file for.
            proto_dir (str): Directory for proto files.
        """
        os.makedirs(proto_dir, exist_ok=True)
        proto_file_path = os.path.join(proto_dir, f"{func.__name__}.proto")
        self.logger.info(f"Generated proto file: {proto_file_path}")

        with open(proto_file_path, "w") as f:
            f.write(self._generate_proto_content(func))

    def _generate_proto_content(self, func: Callable) -> str:
        """
        Generate the content of the .proto file.

        Args:
            func (Callable): The function to generate a .proto file for.

        Returns:
            str: The content of the .proto file.
        """
        service_name = func.__name__.title().replace("_", "")
        proto_content = f"""
        syntax = "proto3";
        package apifunc;
        import "google/protobuf/struct.proto";

        service {service_name} {{
            rpc Transform (google.protobuf.Struct) returns (google.protobuf.Struct) {{}}
        }}
        """
        return proto_content

    def _compile_proto(self, func: Callable, proto_dir: str, generated_dir: str):
        """
        Compile the .proto file to generate gRPC code.

        Args:
            func (Callable): The function to compile the .proto file for.
            proto_dir (str): Directory for proto files.
            generated_dir (str): Directory for generated code.
        """
        proto_file_path = os.path.join(proto_dir, f"{func.__name__}.proto")
        os.makedirs(generated_dir, exist_ok=True)
        self.logger.info(f"Generated gRPC code for: {func.__name__}")

        # Get the path to the directory containing struct.proto
        protobuf_include = os.path.dirname(google.protobuf.__file__)

        protoc_args = [
            'grpc_tools.protoc',
            f'-I{proto_dir}',  # Pass each include path as a separate -I argument
            f'-I{protobuf_include}',  # Pass each include path as a separate -I argument
            f'--python_out={generated_dir}',
            f'--grpc_python_out={generated_dir}',
            proto_file_path
        ]

        # Execute protoc command
        try:
            grpc_tools.protoc.main(protoc_args)
        except SystemExit as e:
            if e.code != 0:
                raise RuntimeError(f"protoc failed with exit code {e.code}") from e

    def _create_server(self):
        """
        Create a gRPC server.

        Returns:
            grpc.Server: The created gRPC server.
        """
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        return server

    def start_server(self, func: Callable, proto_dir: str, generated_dir: str, port: int):
        """
        Start the gRPC server.

        Args:
            func (Callable): The function to start the server for.
            proto_dir (str): Directory for proto files.
            generated_dir (str): Directory for generated code.
            port (int): The port to listen on.
        """
        self.logger.info(f"Starting server for: {func.__name__}")
        server = self._create_server()
        self._add_servicer_to_server(server, func, generated_dir)
        server.add_insecure_port(f'[::]:{port}')
        server.start()
        return server

    def _add_servicer_to_server(self, server, func: Callable, generated_dir: str):
        """
        Add the servicer to the gRPC server.

        Args:
            server (grpc.Server): The gRPC server.
            func (Callable): The function to add the servicer for.
            generated_dir (str): Directory for generated code.
        """
        # Add the generated directory to sys.path
        sys.path.insert(0, generated_dir)

        module_name = f"{func.__name__}_pb2_grpc"
        module_path = os.path.join(generated_dir, f"{func.__name__}_pb2_grpc.py")
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        servicer_class_name = f"{func.__name__.title().replace('_', '')}Servicer"
        servicer_class = getattr(module, servicer_class_name)

        add_to_server_func_name = f"add_{func.__name__.title().replace('_', '')}Servicer_to_server"
        add_to_server_func = getattr(module, add_to_server_func_name)

        class Servicer(servicer_class):
            def Transform(self, request, context):
                input_data = json.loads(request.SerializeToString())
                output_data = func(input_data)
                response = Struct()
                response.update(output_data)
                return response

        add_to_server_func(Servicer(), server)


class DynamicgRPCComponent:
    """
    Dynamic gRPC component for the pipeline.
    """

    def __init__(self, transform_func: Callable, proto_dir: str, generated_dir: str, port: int):
        """
        Initialize the DynamicgRPCComponent.

        Args:
            transform_func (Callable): The transformation function.
            proto_dir (str): Directory for proto files.
            generated_dir (str): Directory for generated code.
            port (int): The port for the gRPC server.
        """
        self.transform_func = transform_func
        self.proto_dir = proto_dir
        self.generated_dir = generated_dir
        self.logger = logging.getLogger(__name__)
        self.grpc_module = self._load_grpc_module()
        self.port = port
        self.server = None

    def _load_grpc_module(self):
        """
        Load the generated gRPC module.

        Returns:
            module: The generated gRPC module.
        """
        # Add the generated directory to sys.path
        sys.path.insert(0, self.generated_dir)

        module_name = f"{self.transform_func.__name__}_pb2_grpc"
        module_path = os.path.join(self.generated_dir, f"{self.transform_func.__name__}_pb2_grpc.py")
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    def process(self, data: Any) -> Any:
        """
        Process the data using the transformation function.

        Args:
            data (Any): The input data.

        Returns:
            Any: The processed data.
        """
        return self.transform_func(data)

    def start_grpc_server(self):
        config = ApiFuncConfig(port=self.port)
        framework = ApiFuncFramework(config)
        framework.register_function(self.transform_func, self.proto_dir, self.generated_dir)
        self.server = framework.start_server(self.transform_func, self.proto_dir, self.generated_dir, self.port)
        return self.server


class PipelineOrchestrator:
    """
    Orchestrates the pipeline of components.
    """

    def __init__(self):
        """
        Initialize the PipelineOrchestrator.
        """
        self.components: List[DynamicgRPCComponent] = []
        self.servers: List[grpc.Server] = []

    def add_component(self, component: DynamicgRPCComponent):
        """
        Add a component to the pipeline.

        Args:
            component (DynamicgRPCComponent): The component to add.
        """
        self.components.append(component)
        return self

    def execute_pipeline(self, initial_data: Any):
        """
        Execute the pipeline.

        Args:
            initial_data (Any): The initial data.

        Returns:
            Any: The result of the pipeline.
        """
        current_data = initial_data

        for component in self.components:
            current_data = component.process(current_data)

        return current_data

    def start_servers(self):
        for component in self.components:
            server = component.start_grpc_server()
            self.servers.append(server)

    def stop_servers(self):
        for server in self.servers:
            server.stop(0)


# Przykson_data: Dict) -> str:
    """
    Transformacja JSON do HTML
    """
    html_template = """
    <html>
    <body>
        <h1>Raport</h1>
        <table>
            {% for key, value in data.items() %}
            <tr>
                <td>{{ key }}</td>
                <td>{{ value }}</td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """

    template = Template(html_template)
    return template.render(data=json_data)


def html_to_pdf(html_content: str) -> bytes:
    """
    Konwersja HTML do PDF
    """
    return weasyprint.HTML(string=html_content).write_pdf()


def example_usage(output_file: str = 'raport.pdf'):
    """
    Przykżycie modularnego frameworka pipeline
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("Starting the apifunc example pipeline with two services...")

    sample_data = {
        "nazwa": "Przykładowy Raport",
        "data": "2023-11-20",
        "wartość": 123.45
    }

    proto_dir_json_html = os.path.abspath("./proto/json_html")
    generated_dir_json_html = os.path.abspath("./generated/json_html")
    proto_dir_html_pdf = os.path.abspath("./proto/html_pdf")
    generated_dir_html_pdf = os.path.abspath("./generated/html_pdf")

    logger.info(f"Proto files directory: {proto_dir_json_html}")
    logger.info(f"Generated code directory: {generated_dir_json_html}")
    logger.info(f"Proto files directory: {proto_dir_html_pdf}")
    logger.info(f"Generated code directory: {generated_dir_html_pdf}")

    # Tworzenie komponentów
    json_to_html_component = DynamicgRPCComponent(json_to_html, proto_dir=proto_dir_json_html,
                                                  generated_dir=generated_dir_json_html, port=50051)
    html_to_pdf_component = DynamicgRPCComponent(html_to_pdf, proto_dir=proto_dir_html_pdf,
                                                 generated_dir=generated_dir_html_pdf, port=50052)

    # Tworzenie orkiestratora
    pipeline = PipelineOrchestrator()

    # Dodawanie komponentdo potoku
    pipeline.add_component(json_to_html_component).add_component(html_to_pdf_component)

    # Start the servers in separate threads
    pipeline.start_servers()

    logger.info(f"Starting JSON-to-HTML server on port 50051")
    logger.info(f"Starting HTML-to-PDF server on port 50052")

    # Run the servers in background threads
    def run_server(server, name):
        try:
            server.wait_for_termination()
        except Exception as e:
            logger.error(f"{name} server error: {e}")

    threads = []
    for i, server in enumerate(pipeline.servers):
        thread = threading.Thread(target=run_server, args=(server, f"Server {i+1}"))
        threads.append(thread)
        thread.start()
        logger.info(f"Server {i+1} running in background thread")

    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("All services have been shut down.")
        pipeline.stop_servers()
        for thread in threads:
            thread.join()

    # Wykonanie potoku
    # result = pipeline.execute_pipeline(sample_data)

    # Zapis do pliku
    # with open(output_file, 'wb') as f:
    #     f.write(result)

    # logger.info(f"Raport zapisany do pliku: {output_file}")


if __name__ == "__main__":
    example_usage()