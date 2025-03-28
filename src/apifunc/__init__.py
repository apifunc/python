"""
pifunc - Framework mikroserwisowy z wieloma protokołami komunikacyjnymi.
"""

from functools import wraps
import inspect
import sys
import os
import signal
import importlib
from typing import Any, Callable, Dict, List, Optional, Set, Type
import logging

# Konfiguracja loggera
logger = logging.getLogger("pifunc")
handler = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Importowanie klienta
try:
    from pifunc.pifunc_client import PiFuncClient
except ImportError:
    class PiFuncClient:
        def __init__(self, base_url="", protocol=""):
            self.base_url = base_url
            self.protocol = protocol

        def call(self, service_name, args=None, **kwargs):
            logger.warning(f"PiFuncClient stub called for {service_name}")
            return {}

__version__ = "0.1.2"
__all__ = ["service", "client", "run_services", "load_module_from_file", "PiFuncClient",
           "http", "websocket", "grpc", "mqtt", "zeromq", "redis", "amqp", "graphql", "cron"]

# Rejestry usług i klientów
_SERVICE_REGISTRY = {}
_CLIENT_REGISTRY = {}
_ADAPTER_CLASSES = {}

# Dostępne protokoły
_AVAILABLE_PROTOCOLS = ["http", "cron", "websocket", "grpc", "mqtt", "zeromq", "redis", "amqp", "graphql"]

# Włączone protokoły z zmiennej środowiskowej
_env_protocols = os.environ.get("PIFUNC_PROTOCOLS", "")
_ENABLED_PROTOCOLS = set(_env_protocols.lower().split(",")) if _env_protocols else None


# Narzędzia do obsługi protokołów

def _get_protocol_class_name(protocol_name):
    """Zwraca poprawną nazwę klasy dla protokołu."""
    if protocol_name in ["http", "cron", "grpc", "mqtt", "amqp"]:
        return f"{protocol_name.upper()}Adapter"
    return f"{protocol_name.capitalize()}Adapter"


def _import_adapter(protocol_name):
    """Importuje adapter protokołu tylko gdy jest potrzebny."""
    if protocol_name in _ADAPTER_CLASSES:
        return _ADAPTER_CLASSES[protocol_name]

    # Pomijamy protokoły wyłączone przez zmienną środowiskową
    if _ENABLED_PROTOCOLS is not None and protocol_name not in _ENABLED_PROTOCOLS:
        logger.info(f"Protocol {protocol_name} is disabled by PIFUNC_PROTOCOLS environment variable")
        return None

    adapter_module_name = f"pifunc.adapters.{protocol_name}_adapter"
    adapter_class_name = _get_protocol_class_name(protocol_name)

    try:
        module = importlib.import_module(adapter_module_name)
        adapter_class = getattr(module, adapter_class_name)
        _ADAPTER_CLASSES[protocol_name] = adapter_class
        return adapter_class
    except (ImportError, AttributeError) as e:
        logger.warning(f"Could not import {adapter_module_name}: {e}")
        return None


def _get_used_protocols():
    """Zwraca zbiór protokołów używanych przez zarejestrowane usługi."""
    used_protocols = set()
    for metadata in _SERVICE_REGISTRY.values():
        used_protocols.update(metadata.get("protocols", []))
    return used_protocols


# Dekoratory protokołów

def _create_protocol_decorator(protocol_name, **default_config):
    """Fabryka dekoratorów dla protokołów."""

    def decorator(*args, **kwargs):
        # Obsługa przypadku gdy dekorator jest używany bez argumentów
        if len(args) == 1 and callable(args[0]):
            func = args[0]
            config = default_config.copy()

            @wraps(func)
            def wrapper(*wargs, **wkwargs):
                return func(*wargs, **wkwargs)

            setattr(wrapper, f"_pifunc_{protocol_name}", config)
            return wrapper

        # Obsługa przypadku gdy dekorator jest używany z argumentami
        config = default_config.copy()
        config.update(kwargs)
        if args:
            config["path"] = args[0]  # dla http, websocket itp.

        def inner_decorator(func):
            @wraps(func)
            def wrapper(*wargs, **wkwargs):
                return func(*wargs, **wkwargs)

            setattr(wrapper, f"_pifunc_{protocol_name}", config)
            return wrapper

        return inner_decorator

    return decorator


# Generowanie dekoratorów dla protokołów
http = _create_protocol_decorator("http", path="/api/{func_name}", method="GET")
websocket = _create_protocol_decorator("websocket", event="{func_name}")
grpc = _create_protocol_decorator("grpc", service_name=None, method=None, streaming=False)
mqtt = _create_protocol_decorator("mqtt", topic="{func_name}", qos=0)
zeromq = _create_protocol_decorator("zeromq", socket_type="REP", identity=None)
redis = _create_protocol_decorator("redis", channel=None, pattern=None, command=None)
amqp = _create_protocol_decorator("amqp", queue=None, exchange="", routing_key=None, exchange_type="direct")
graphql = _create_protocol_decorator("graphql", field_name=None, is_mutation=False, description=None)
cron = _create_protocol_decorator("cron", interval=None, at=None, cron_expression=None)


def client(**protocol_configs):
    """
    Dekorator służący do rejestracji funkcji jako klienta usługi.

    Wymaga podania dokładnie jednej konfiguracji protokołu, np:
    @client(http={"path": "/api/products"}) lub @client(grpc={})

    Args:
        **protocol_configs: Konfiguracje dla protokołu w formie http={...}, grpc={...} itp.
    """
    # Sprawdzamy czy podano dokładnie jeden protokół
    if len(protocol_configs) != 1:
        raise ValueError("Musisz podać dokładnie jeden protokół, np. @client(http={...})")

    # Wyciągamy nazwę protokołu i jego konfigurację
    protocol_name = list(protocol_configs.keys())[0]
    config = protocol_configs[protocol_name]

    # Opcjonalny parametr 'service'
    service = config.pop("service", None) if isinstance(config, dict) else None

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        target_service = service or func.__name__

        metadata = {
            "name": func.__name__,
            "target_service": target_service,
            "function": func,
            "module": func.__module__,
            "file": inspect.getfile(func),
            "_is_client_function": True,
            "protocol": protocol_name,  # Dodajemy protokół
            protocol_name: config  # Dodajemy konfigurację
        }

        _CLIENT_REGISTRY[func.__name__] = metadata
        wrapper._pifunc_client = metadata
        return wrapper

    return decorator


def service(name=None, description=None, **protocol_configs):
    """
    Dekorator służący do rejestracji funkcji jako usługi dostępnej przez protokoły.

    Protokoły są automatycznie wykrywane na podstawie podanych konfiguracji.
    Przykład: @service(http={"path": "/api"}, cron={"interval": "1m"})

    Args:
        name: Nazwa usługi (domyślnie nazwa funkcji).
        description: Opis usługi (domyślnie docstring funkcji).
        **protocol_configs: Konfiguracje dla poszczególnych protokołów.
    """
    # Wykrywamy protokoły z konfiguracji
    protocols = [protocol for protocol in protocol_configs.keys()
                 if protocol in _AVAILABLE_PROTOCOLS]

    # Przypadek, gdy dekorator używany jest bez nawiasów
    if callable(name):
        func = name
        return service()(func)

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        service_name = name or func.__name__
        service_description = description or func.__doc__ or ""

        # Filtrujemy protokoły według zmiennej środowiskowej
        enabled_protocols = protocols
        if _ENABLED_PROTOCOLS:
            enabled_protocols = [p for p in protocols if p in _ENABLED_PROTOCOLS]

        # Jeśli nie określono protokołów, używamy wszystkich dostępnych
        if not enabled_protocols:
            available_protocols = _AVAILABLE_PROTOCOLS
            if _ENABLED_PROTOCOLS:
                available_protocols = [p for p in _AVAILABLE_PROTOCOLS if p in _ENABLED_PROTOCOLS]
            enabled_protocols = available_protocols

        signature = inspect.signature(func)

        metadata = {
            "name": service_name,
            "description": service_description,
            "function": func,
            "module": func.__module__,
            "file": inspect.getfile(func),
            "signature": {
                "parameters": {},
                "return_annotation": None
            },
            "protocols": enabled_protocols
        }

        # Dodajemy informacje o parametrach
        for param_name, param in signature.parameters.items():
            metadata["signature"]["parameters"][param_name] = {
                "annotation": param.annotation if param.annotation != inspect.Parameter.empty else None,
                "default": None if param.default == inspect.Parameter.empty else param.default
            }

        # Dodajemy informację o typie zwracanym
        metadata["signature"]["return_annotation"] = (
            signature.return_annotation if signature.return_annotation != inspect.Parameter.empty else None
        )

        # Zbieramy konfiguracje ze wszystkich dekoratorów protokołów
        for protocol in _AVAILABLE_PROTOCOLS:
            attr_name = f"_pifunc_{protocol}"
            if hasattr(func, attr_name):
                metadata[protocol] = getattr(func, attr_name)

        # Dodajemy konfiguracje przekazane jako argumenty
        for protocol, config in protocol_configs.items():
            if protocol in _AVAILABLE_PROTOCOLS:
                metadata[protocol] = config

        # Sprawdzamy, czy funkcja jest klientem
        if hasattr(func, '_pifunc_client'):
            metadata["client"] = func._pifunc_client
            metadata["_is_client_function"] = True

        _SERVICE_REGISTRY[service_name] = metadata
        wrapper._pifunc_service = metadata
        return wrapper

    return decorator


def run_services(**config):
    """
    Uruchamia wszystkie zarejestrowane usługi z podaną konfiguracją.

    Automatycznie wykrywa, które protokoły są używane, bez potrzeby
    jawnego określania ich w tablicy 'protocols'.

    Args:
        **config: Konfiguracja dla poszczególnych protokołów i ogólne ustawienia.
                 Np. http={"port": 8080}, watch=True
    """
    adapters = {}
    clients = {}

    # Ustawienie zmiennej środowiskowej ma priorytet
    env_protocols = os.environ.get("PIFUNC_PROTOCOLS", "")
    explicitly_enabled = set(env_protocols.lower().split(",")) if env_protocols else set()

    # Protokoły z konfiguracji
    config_protocols = set(k for k in config.keys() if k in _AVAILABLE_PROTOCOLS)

    # Protokoły używane przez zarejestrowane usługi
    service_protocols = _get_used_protocols()

    # Ustalamy, które protokoły będą używane
    if explicitly_enabled:
        # Jeśli zmienna środowiskowa jest ustawiona, używamy tylko tych protokołów
        required_protocols = explicitly_enabled.intersection(_AVAILABLE_PROTOCOLS)
    else:
        # W przeciwnym razie używamy protokołów z konfiguracji i zarejestrowanych usług
        required_protocols = config_protocols.union(service_protocols)

    logger.info(f"Enabled protocols: {', '.join(required_protocols)}")

    # Dynamicznie importujemy potrzebne adaptery
    for protocol in required_protocols:
        adapter_class = _import_adapter(protocol)
        if adapter_class:
            adapters[protocol] = adapter_class()
            logger.info(f"Loaded adapter for protocol: {protocol}")

    # Konfigurujemy adaptery
    for protocol, adapter in adapters.items():
        adapter_config = config.get(protocol, {})
        adapter.setup(adapter_config)

    # Tworzymy klientów dla protokołów
    for protocol, adapter in adapters.items():
        if protocol == "http":
            host = config.get("http", {}).get("host", "localhost")
            port = config.get("http", {}).get("port", 8080)
            base_url = f"http://{host}:{port}"
            clients[protocol] = PiFuncClient(base_url=base_url, protocol=protocol)
        elif protocol == "grpc":
            host = config.get("grpc", {}).get("host", "localhost")
            port = config.get("grpc", {}).get("port", 50051)
            base_url = f"{host}:{port}"
            clients[protocol] = PiFuncClient(base_url=base_url, protocol=protocol)
        elif protocol == "zeromq":
            host = config.get("zeromq", {}).get("host", "localhost")
            port = config.get("zeromq", {}).get("port", 5555)
            base_url = f"{host}:{port}"
            clients[protocol] = PiFuncClient(base_url=base_url, protocol=protocol)
        elif protocol == "amqp":
            host = config.get("amqp", {}).get("host", "localhost")
            port = config.get("amqp", {}).get("port", 5672)
            base_url = f"{host}:{port}"
            clients[protocol] = PiFuncClient(base_url=base_url, protocol=protocol)
        elif protocol == "graphql":
            host = config.get("graphql", {}).get("host", "localhost")
            port = config.get("graphql", {}).get("port", 8082)
            base_url = f"http://{host}:{port}/graphql"
            clients[protocol] = PiFuncClient(base_url=base_url, protocol=protocol)

    # Przygotowujemy konfigurację CRON z klientami
    if "cron" in adapters:
        cron_config = config.get("cron", {}).copy()
        cron_config["clients"] = clients
        adapters["cron"].setup(cron_config)

    # Rejestrujemy funkcje w adapterach
    for service_name, metadata in _SERVICE_REGISTRY.items():
        # Filtrujemy protokoły usługi według dostępnych adapterów
        enabled_protocols = set(metadata.get("protocols", [])).intersection(adapters.keys())

        for protocol in enabled_protocols:
            try:
                adapters[protocol].register_function(metadata["function"], metadata)
            except Exception as e:
                logger.error(f"Error registering {service_name} for {protocol}: {e}")

    # Rejestrujemy funkcje klienckie w adapterze CRON
    if "cron" in adapters:
        for client_name, metadata in _CLIENT_REGISTRY.items():
            if "_is_client_function" in metadata:
                adapters["cron"].register_function(metadata["function"], metadata)

    # Uruchamiamy adaptery
    for protocol, adapter in adapters.items():
        try:
            adapter.start()
        except Exception as e:
            logger.error(f"Error starting {protocol} adapter: {e}")

    # Włączamy monitoring plików, jeśli potrzeba
    if config.get("watch", False):
        _start_file_watcher(adapters)

    # Konfigurujemy obsługę sygnałów do graceful shutdown
    def handle_signal(signum, frame):
        logger.info("Zatrzymywanie serwerów...")
        for adapter in adapters.values():
            adapter.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    logger.info(f"Uruchomiono {len(_SERVICE_REGISTRY)} usług przez {len(adapters)} protokołów.")

    # Blokujemy główny wątek
    try:
        while True:
            if hasattr(signal, 'pause'):
                signal.pause()
            else:
                import time
                time.sleep(3600)
    except KeyboardInterrupt:
        handle_signal(None, None)


def _start_file_watcher(adapters):
    """Uruchamia wątek monitorujący zmiany w plikach."""
    import threading
    import time

    def watch_files():
        file_times = {}

        # Zbieramy pliki, w których zdefiniowane są usługi
        for metadata in _SERVICE_REGISTRY.values():
            file_path = metadata.get("file")
            if file_path and os.path.exists(file_path):
                file_times[file_path] = os.path.getmtime(file_path)

        while True:
            # Sprawdzamy, czy któryś plik został zmodyfikowany
            changed = False
            for file_path in list(file_times.keys()):
                try:
                    mtime = os.path.getmtime(file_path)
                    if file_times[file_path] < mtime:
                        logger.info(f"Plik {file_path} został zmodyfikowany. Przeładowywanie...")
                        file_times[file_path] = mtime
                        changed = True
                except:
                    pass

            if changed:
                for adapter in adapters.values():
                    adapter.stop()
                os.execv(sys.executable, [sys.executable] + sys.argv)

            time.sleep(1)

    thread = threading.Thread(target=watch_files, daemon=True)
    thread.start()


def load_module_from_file(file_path):
    """Ładuje moduł z pliku."""
    module_name = os.path.basename(file_path).replace('.py', '')
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module