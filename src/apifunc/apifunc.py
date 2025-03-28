import os
import sys
import grpc
from concurrent import futures
import importlib
import inspect
import logging
import subprocess
from typing import Any, Callable, Dict, List, Optional
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default directories for proto files and generated code
DEFAULT_PROTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proto")
DEFAULT_GENERATED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated")

def generate_proto_for_function(func: Callable, proto_dir: Optional[str] = None) -> str:
    """
    Generate a .proto file for the given function

    Args:
        func: Function to generate proto for
        proto_dir: Directory to store the proto file

    Returns:
        Path to the generated proto file
    """
    proto_dir = proto_dir or DEFAULT_PROTO_DIR
    os.makedirs(proto_dir, exist_ok=True)

    func_name = func.__name__
    proto_file_path = os.path.join(proto_dir, f"{func_name}.proto")

    # Get function signature
    sig = inspect.signature(func)

    # Generate proto content
    proto_content = f"""syntax = "proto3";

package apifunc;

service {func_name.capitalize()}Service {{
  rpc Execute ({func_name.capitalize()}Request) returns ({func_name.capitalize()}Response);
}}

message {func_name.capitalize()}Request {{
"""

    # Add parameters to request message
    for i, (param_name, param) in enumerate(sig.parameters.items()):
        proto_content += f"  string {param_name} = {i+1};\n"

    proto_content += f"""}}

message {func_name.capitalize()}Response {{
  string result = 1;
}}
"""

    # Write proto file
    with open(proto_file_path, 'w') as f:
        f.write(proto_content)

    logger.info(f"Generated proto file: {proto_file_path}")
    return proto_file_path

class ApiFuncConfig:
    """Configuration class for ApiFuncFramework"""

    def __init__(self,
                 proto_dir: Optional[str] = None,
                 generated_dir: Optional[str] = None,
                 port: int = 50051,
                 max_workers: int = 10):
        """
        Initialize configuration with default values

        Args:
            proto_dir: Directory to store .proto files
            generated_dir: Directory to store generated gRPC code
            port: Default port for gRPC server
            max_workers: Maximum number of workers for gRPC server
        """
        self.proto_dir = proto_dir or DEFAULT_PROTO_DIR
        self.generated_dir = generated_dir or DEFAULT_GENERATED_DIR
        self.port = port
        self.max_workers = max_workers

        # Create directories if they don't exist
        os.makedirs(self.proto_dir, exist_ok=True)
        os.makedirs(self.generated_dir, exist_ok=True)

        # Add generated directory to Python path for imports
        if self.generated_dir not in sys.path:
            sys.path.append(self.generated_dir)

        logger.info(f"Proto files directory: {self.proto_dir}")
        logger.info(f"Generated code directory: {self.generated_dir}")

class ApiFuncFramework:
    """Main framework class for ApiFuncFramework"""

    def __init__(self, config: Optional[ApiFuncConfig] = None):
        """
        Initialize the framework

        Args:
            config: Configuration object
        """
        self.config = config or ApiFuncConfig()
        self.services = {}
        self.server = None
        self.components = []

    def register_function(self, func: Callable) -> None:
        """
        Register a Python function as a gRPC service

        Args:
            func: Function to register
        """
        # Import here to avoid circular imports
        from apifunc.components import DynamicgRPCComponent

        # Create a component for this function
        component = DynamicgRPCComponent(
            func,
            proto_dir=self.config.proto_dir,
            generated_dir=self.config.generated_dir
        )

        # Register the component
        self._register_grpc_component(component)
        self.components.append(component)

    def _register_grpc_component(self, component):
        """
        Register a gRPC component with the framework

        Args:
            component: Component to register
        """
        # Get function metadata
        func_name = component.func.__name__
        module_name = component.func.__module__

        logger.info(f"Registering function: {module_name}.{func_name}")

        # Generate proto file for this function
        proto_file = generate_proto_for_function(
            component.func,
            proto_dir=self.config.proto_dir
        )

        # Generate gRPC code from proto file
        self._generate_grpc_code(proto_file)

        # Register the service
        self.services[func_name] = {
            'component': component,
            'proto_file': proto_file,
        }

    def _generate_grpc_code(self, proto_file: str) -> None:
        """
        Generate Python gRPC code from proto file

        Args:
            proto_file: Path to proto file
        """
        proto_filename = os.path.basename(proto_file)
        proto_name = os.path.splitext(proto_filename)[0]

        cmd = [
            sys.executable, "-m", "grpc_tools.protoc",
            f"--proto_path={self.config.proto_dir}",
            f"--python_out={self.config.generated_dir}",
            f"--grpc_python_out={self.config.generated_dir}",
            proto_file
        ]

        try:
            subprocess.check_call(cmd)
            logger.info(f"Generated gRPC code for: {proto_name}")

            # Create __init__.py if it doesn't exist
            init_file = os.path.join(self.config.generated_dir, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, 'w') as f:
                    f.write("# Generated by ApiFuncFramework\n")

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to generate gRPC code: {e}")
            raise

    def start_server(self):
        """Start the gRPC server in a background thread"""
        server = self._create_server()
        server_thread = threading.Thread(target=server.start)
        server_thread.daemon = True  # Make thread exit when main thread exits
        server_thread.start()
        return server

    def _create_service_class(self, service_name: str, component) -> type:
        """
        Create a service implementation class for the given component

        Args:
            service_name: Name of the service
            component: Component implementation

        Returns:
            Service implementation class
        """
        # Import the generated pb2 module
        try:
            pb2_module = importlib.import_module(f"{service_name}_pb2")
            pb2_grpc_module = importlib.import_module(f"{service_name}_pb2_grpc")
        except ImportError:
            # Try with full path
            base_dir = os.path.basename(self.config.generated_dir)
            pb2_module = importlib.import_module(f"{base_dir}.{service_name}_pb2")
            pb2_grpc_module = importlib.import_module(f"{base_dir}.{service_name}_pb2_grpc")

        # Get the servicer class
        servicer_class = getattr(pb2_grpc_module, f"{service_name.capitalize()}ServiceServicer")

        # Create a new class that inherits from the servicer class
        class ServiceImplementation(servicer_class):
            def Execute(self, request, context):
                # Extract parameters from request
                params = {}
                for field in request.DESCRIPTOR.fields:
                    params[field.name] = getattr(request, field.name)

                # Call the component's process method
                result = component.process(params)

                # Create response
                response_class = getattr(pb2_module, f"{service_name.capitalize()}Response")
                response = response_class(result=str(result))

                return response

        return ServiceImplementation

# Main function for direct execution
def main():
    # Example usage
    config = ApiFuncConfig()
    framework = ApiFuncFramework(config)

    # Example function to register
    def hello(name):
        return f"Hello, {name}!"

    framework.register_function(hello)
    server = framework.start_server()

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == "__main__":
    main()
