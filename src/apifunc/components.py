"""
Component definitions for ApiFuncFramework
"""

import time
import inspect
import logging
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

class BaseComponent:
    """Base class for all pipeline components"""

    def __init__(self, name: Optional[str] = None):
        self.name = name or self.__class__.__name__

    def process(self, input_data: Any) -> Any:
        """Process input data and return output"""
        raise NotImplementedError("Subclasses must implement process method")

class DynamicgRPCComponent(BaseComponent):
    """Component that dynamically generates gRPC services"""

    def __init__(self,
                 func: Callable,
                 name: Optional[str] = None,
                 proto_dir: Optional[str] = None,
                 generated_dir: Optional[str] = None):
        """
        Initialize a dynamic gRPC component

        Args:
            func: The function to expose as a gRPC service
            name: Optional name for the component (defaults to function name)
            proto_dir: Directory to store proto files
            generated_dir: Directory to store generated code
        """
        super().__init__(name or func.__name__)
        self.func = func
        self.proto_dir = proto_dir
        self.generated_dir = generated_dir
        self.signature = inspect.signature(func)

    def process(self, input_data: Any) -> Any:
        """Process input data using the wrapped function"""
        # Get the function signature
        sig = inspect.signature(self.func)
        param_count = len(sig.parameters)

        # If the function expects a single parameter and we have a dict,
        # pass the whole dict as a single argument
        if param_count == 1 and isinstance(input_data, dict):
            return self.func(input_data)
        # If the function expects multiple parameters and we have a dict,
        # unpack the dict as keyword arguments
        elif param_count > 1 and isinstance(input_data, dict):
            return self.func(**input_data)
        # Otherwise, pass the input data as is
        else:
            return self.func(input_data)

# Keep the main thread running to allow the server threads to continue
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    logger.info("Shutting down...")
