#!/usr/bin/env python3
import argparse
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Set, Tuple

import grpc
from grpc_reflection.v1alpha import reflection_pb2, reflection_pb2_grpc


# Potrzebne będą pakiety:
# pip install grpcio grpcio-reflection

class GrpcServiceInfo:
    def __init__(self, address: str, port: int, services: List[str] = None):
        self.address = address
        self.port = port
        self.services = services or []

    def __str__(self) -> str:
        return f"{self.address}:{self.port} - {len(self.services)} usług"


def parse_args():
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
    return parser.parse_args()

def is_port_open(host: str, port: int) -> bool:
    """Quick check if a port is open using TCP socket."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    try:
        result = sock.connect_ex((host, port))
        return result == 0
    except socket.error:
        return False
    finally:
        sock.close()

def scan_grpc_port(host: str, port: int) -> Tuple[bool, List[str]]:
    """Scan a specific port for gRPC services using reflection."""
    if not is_port_open(host, port):
        return False, []

    try:
        channel = grpc.insecure_channel(f"{host}:{port}")
        # Set a deadline for connection attempts
        try:
            grpc.channel_ready_future(channel).result(timeout=2)
        except grpc.FutureTimeoutError:
            channel.close()
            return False, []

        # Try to use reflection to list services
        stub = reflection_pb2_grpc.ServerReflectionStub(channel)
        services = []

        try:
            # List services using reflection
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
                return True, services
            return False, []
        except grpc.RpcError:
            channel.close()
            return False, []
    except Exception as e:
        return False, []

def scan_once(hosts, port_range, concurrency):
    """Perform one complete scan of all hosts and ports."""
    found_services = {}

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []

        for host in hosts:
            for port in port_range:
                futures.append(executor.submit(scan_grpc_port, host, port))

        for i, future in enumerate(futures):
            host_idx = i // len(port_range)
            port_idx = i % len(port_range)
            host = hosts[host_idx]
            port = port_range[port_idx]

            success, services = future.result()
            if success:
                found_services[f"{host}:{port}"] = services

    return found_services

def main():
    args = parse_args()
    hosts = [h.strip() for h in args.hosts.split(',')]
    port_range = list(range(args.start, args.end + 1))

    print(f"Scanning {len(hosts)} host(s) on ports {args.start}-{args.end}")
    start_time = time.time()

    found_services = {}
    scan_count = 0

    if args.continuous:
        print("Continuous scanning enabled. Will scan until a service is found.")
        while not found_services:
            scan_count += 1
            print(f"\nStarting scan iteration #{scan_count}...")
            found_services = scan_once(hosts, port_range, args.concurrency)

            if found_services:
                print(f"Found gRPC services after {scan_count} iterations!")
                break

            print(f"No services found in iteration #{scan_count}. Continuing...")
            time.sleep(1)  # Small delay between scans to avoid hammering the network
    else:
        found_services = scan_once(hosts, port_range, args.concurrency)

    elapsed = time.time() - start_time

    # Print summary
    print("\n--- Scan Summary ---")
    print(f"Scanned {len(hosts)} host(s) on {len(port_range)} port(s) in {elapsed:.2f} seconds")
    if args.continuous:
        print(f"Performed {scan_count} scan iterations")
    print(f"Found {len(found_services)} gRPC server(s)")

    for addr, services in found_services.items():
        print(f"\n{addr}:")
        for service in services:
            print(f"  - {service}")

if __name__ == "__main__":
    main()