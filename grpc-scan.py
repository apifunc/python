import argparse
import socket
import sys
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Set, Tuple, Optional

import grpc
from grpc_reflection.v1alpha import reflection_pb2, reflection_pb2_grpc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("apifunc")


class GrpcServiceInfo:
    """Class to store information about discovered gRPC services"""

    def __init__(self, host: str, port: int, services: List[str]):
        self.host = host
        self.port = port
        self.services = services
        self.discovery_time = time.time()

    def __str__(self) -> str:
        return f"{self.host}:{self.port} - {len(self.services)} services"

    def get_endpoint(self) -> str:
        return f"{self.host}:{self.port}"

    def get_details(self) -> str:
        """Return detailed information about this gRPC service"""
        details = [f"gRPC Service at {self.host}:{self.port}"]
        details.append(f"Discovered at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.discovery_time))}")
        details.append(f"Available services ({len(self.services)}):")
        for service in self.services:
            details.append(f"  - {service}")
        return "\n".join(details)


class GrpcScanner:
    """Scanner for gRPC services with detailed logging"""

    def __init__(self, hosts: List[str], start_port: int = 50000, end_port: int = 50100,
                 concurrency: int = 50, verbose: bool = False):
        self.hosts = hosts
        self.port_range = list(range(start_port, end_port + 1))
        self.concurrency = concurrency

        # Configure logger
        self.logger = logger
        if verbose:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)

        self.discovered_services: Dict[str, GrpcServiceInfo] = {}

    def is_port_open(self, host: str, port: int) -> bool:
        """Quick check if a port is open using TCP socket."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        try:
            result = sock.connect_ex((host, port))
            if result == 0:
                self.logger.debug(f"TCP port {port} on {host} is open")
            return result == 0
        except socket.error as e:
            self.logger.debug(f"Socket error checking {host}:{port} - {str(e)}")
            return False
        finally:
            sock.close()

    def scan_grpc_port(self, host: str, port: int) -> Optional[GrpcServiceInfo]:
        """Scan a specific port for gRPC services using reflection."""
        self.logger.debug(f"Checking {host}:{port} for gRPC services...")

        if not self.is_port_open(host, port):
            return None

        self.logger.info(f"🔌 TCP port open at {host}:{port}, checking for gRPC...")

        try:
            channel = grpc.insecure_channel(f"{host}:{port}")
            # Set a deadline for connection attempts
            try:
                self.logger.debug(f"Attempting to establish gRPC channel to {host}:{port}")
                grpc.channel_ready_future(channel).result(timeout=2)
                self.logger.debug(f"Successfully established gRPC channel to {host}:{port}")
            except grpc.FutureTimeoutError:
                self.logger.debug(f"Timeout establishing gRPC channel to {host}:{port}")
                channel.close()
                return None

            # Try to use reflection to list services
            stub = reflection_pb2_grpc.ServerReflectionStub(channel)
            services = []

            try:
                # List services using reflection
                self.logger.debug(f"Querying reflection service at {host}:{port}")
                request = reflection_pb2.ServerReflectionRequest(
                    list_services=""
                )
                responses = stub.ServerReflection(iter([request]))

                for response in responses:
                    if response.HasField("list_services_response"):
                        for service in response.list_services_response.service:
                            services.append(service.name)
                        break

                channel.close()
                if services:
                    self.logger.info(f"✅ Found gRPC server at {host}:{port} with {len(services)} services")
                    return GrpcServiceInfo(host, port, services)
                self.logger.debug(f"No services found via reflection at {host}:{port}")
                return None
            except grpc.RpcError as e:
                self.logger.debug(f"RPC error querying reflection at {host}:{port}: {str(e)}")
                channel.close()
                return None
        except Exception as e:
            self.logger.debug(f"Unexpected error scanning {host}:{port}: {str(e)}")
            return None

    def scan_once(self) -> Dict[str, GrpcServiceInfo]:
        """Perform one complete scan of all hosts and ports."""
        found_services: Dict[str, GrpcServiceInfo] = {}

        self.logger.info(f"Starting scan of {len(self.hosts)} host(s) across {len(self.port_range)} ports")

        with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
            futures = []

            for host in self.hosts:
                for port in self.port_range:
                    futures.append(executor.submit(self.scan_grpc_port, host, port))

            for future in futures:
                service_info = future.result()
                if service_info:
                    endpoint = service_info.get_endpoint()
                    found_services[endpoint] = service_info
                    self.logger.info(f"📋 Service details for {endpoint}:")
                    for service in service_info.services:
                        self.logger.info(f"  - {service}")

        return found_services

    def scan_continuous(self) -> Dict[str, GrpcServiceInfo]:
        """Continuously scan until at least one service is found."""
        found_services: Dict[str, GrpcServiceInfo] = {}
        scan_count = 0

        self.logger.info("Continuous scanning enabled. Will scan until a service is found.")
        while not found_services:
            scan_count += 1
            self.logger.info(f"\n🔄 Starting scan iteration #{scan_count}...")
            found_services = self.scan_once()

            if found_services:
                self.logger.info(f"🎉 Found gRPC services after {scan_count} iterations!")
                break

            self.logger.info(f"No services found in iteration #{scan_count}. Continuing...")
            time.sleep(1)  # Small delay between scans to avoid hammering the network

        return found_services

    def print_summary(self, services: Dict[str, GrpcServiceInfo], elapsed: float, scan_count: int = 1):
        """Print a summary of discovered services."""
        self.logger.info("\n📊 --- Scan Summary ---")
        self.logger.info(
            f"Scanned {len(self.hosts)} host(s) on {len(self.port_range)} port(s) in {elapsed:.2f} seconds")
        if scan_count > 1:
            self.logger.info(f"Performed {scan_count} scan iterations")
        self.logger.info(f"Found {len(services)} gRPC server(s)")

        if services:
            self.logger.info("\n🔍 Discovered gRPC Services:")
            for endpoint, service_info in services.items():
                self.logger.info(f"\n📡 {endpoint}:")
                for service in service_info.services:
                    self.logger.info(f"  ↪ {service}")
        else:
            self.logger.info("No gRPC services were found during the scan.")


def scan_for_grpc_services(hosts: List[str], start_port: int = 50000, end_port: int = 50100,
                           concurrency: int = 50, continuous: bool = False, verbose: bool = False) -> Dict[
    str, GrpcServiceInfo]:
    """
    Main function to scan for gRPC services.

    Args:
        hosts: List of hosts to scan
        start_port: Starting port number
        end_port: Ending port number
        concurrency: Maximum number of concurrent scans
        continuous: Whether to scan continuously until a service is found
        verbose: Whether to enable verbose logging

    Returns:
        Dictionary of discovered services
    """
    scanner = GrpcScanner(hosts, start_port, end_port, concurrency, verbose)

    start_time = time.time()
    scan_count = 1

    if continuous:
        discovered_services = scanner.scan_continuous()
        scan_count = 1  # We don't know the exact count from the scanner
    else:
        discovered_services = scanner.scan_once()

    elapsed = time.time() - start_time
    scanner.print_summary(discovered_services, elapsed, scan_count)

    return discovered_services


def main():
    parser = argparse.ArgumentParser(description='Scan for gRPC services')
    parser.add_argument('--hosts', '-H', type=str, default='localhost',
                        help='Comma-separated list of hosts to scan')
    parser.add_argument('--start', '-s', type=int, default=50000,
                        help='Start port for scanning range')
    parser.add_argument('--end', '-e', type=int, default=50100,
                        help='End port for scanning range')
    parser.add_argument('--concurrency', '-c', type=int, default=50,
                        help='Maximum number of concurrent scans')
    parser.add_argument('--continuous', action='store_true',
                        help='Continuously scan until a service is found')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    args = parser.parse_args()

    hosts = [h.strip() for h in args.hosts.split(',')]

    logger.info(f"🔍 APIFunc gRPC Scanner")
    logger.info(f"Targets: {', '.join(hosts)}")
    logger.info(f"Port range: {args.start}-{args.end}")

    scan_for_grpc_services(
        hosts=hosts,
        start_port=args.start,
        end_port=args.end,
        concurrency=args.concurrency,
        continuous=args.continuous,
        verbose=args.verbose
    )


if __name__ == "__main__":
    main()
