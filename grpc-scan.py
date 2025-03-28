import argparse
import socket
import time
import grpc
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from grpc_reflection.v1alpha import reflection_pb2, reflection_pb2_grpc

def quick_port_check(host, port):
    """Ultra-fast TCP port check"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.001)  # 1ms timeout
            result = s.connect_ex((host, port))
            return result == 0
    except:
        return False

def scan_port(host, port, verbose=False):
    # First do an ultra-fast check
    if not quick_port_check(host, port):
        return None

    # If port is open, consider it a potential gRPC service
    try:
        # Use very short timeouts for gRPC
        options = [
            ('grpc.connect_timeout_ms', 100),  # 100ms connect timeout
            ('grpc.keepalive_timeout_ms', 100)
        ]
        channel = grpc.insecure_channel(f"{host}:{port}", options=options)

        # Short deadline for connection
        try:
            grpc.channel_ready_future(channel).result(timeout=0.1)  # 100ms timeout
        except grpc.FutureTimeoutError:
            if verbose:
                print(f"Timeout connecting to gRPC server at {host}:{port}")
            return None

        # Try to use reflection to list services
        stub = reflection_pb2_grpc.ServerReflectionStub(channel)
        services = []

        try:
            # List services using reflection with timeout
            request = reflection_pb2.ServerReflectionRequest(list_services="")

            # The correct method is ServerReflectionInfo, not ServerReflection
            responses = stub.ServerReflectionInfo(iter([request]))

            # Only process the first response with a timeout
            for response in responses:
                if response.HasField("list_services_response"):
                    for service in response.list_services_response.service:
                        services.append(service.name)
                    break
                # Break after first response or short timeout
                break
        except Exception as e:
            if verbose:
                print(f"Error listing services on {host}:{port} - {str(e)}")

            # Even if we can't list services, if the port is open and accepts gRPC connections,
            # we'll consider it a gRPC service for the purpose of stop-on-first
            return {
                "host": host,
                "port": port,
                "services": ["<Unable to list services via reflection>"],
                "error": str(e)
            }

        if services:
            return {
                "host": host,
                "port": port,
                "services": services
            }

    except Exception as e:
        if verbose:
            print(f"Error connecting to gRPC server at {host}:{port} - {str(e)}")

    return None

def batch_scan(host_ports, verbose=False, max_workers=100, stop_on_first=False):
    """Scan a batch of host:port combinations in parallel"""
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_hostport = {
            executor.submit(scan_port, host, port, verbose): (host, port)
            for host, port in host_ports
        }

        # Process results as they complete
        for future in as_completed(future_to_hostport):
            result = future.result()
            if result:
                results.append(result)
                if stop_on_first:
                    # Cancel all pending futures if we need to stop on first result
                    for f in future_to_hostport:
                        if not f.done():
                            f.cancel()
                    break

    return results

def main():
    parser = argparse.ArgumentParser(description="Ultra-fast scanner for gRPC services")
    parser.add_argument("--hosts", "-H", default="localhost", help="Comma-separated list of hosts to scan")
    parser.add_argument("--start", "-s", type=int, default=50000, help="Start port")
    parser.add_argument("--end", "-e", type=int, default=50100, help="End port")
    parser.add_argument("--concurrency", "-c", type=int, default=500, help="Max concurrent scans")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--continuous", action="store_true", help="Continuous scanning")
    parser.add_argument("--rate", "-r", type=float, default=0,
                        help="Scan rate in samples per second (0 for maximum speed)")
    parser.add_argument("--batch-size", "-b", type=int, default=1000,
                        help="Batch size for scanning")
    parser.add_argument("--stop-on-first", "-f", action="store_true",
                        help="Stop scanning after finding the first gRPC service")

    args = parser.parse_args()

    hosts = [host.strip() for host in args.hosts.split(",")]
    port_range = range(args.start, args.end + 1)

    print(f"Scanning ports {args.start}-{args.end} on hosts: {', '.join(hosts)}")
    print(f"Concurrency: {args.concurrency}")
    if args.rate > 0:
        print(f"Scan rate: {args.rate} samples per second")
    else:
        print("Scan rate: Maximum speed")
    if args.stop_on_first:
        print("Will stop after finding the first gRPC service")
    if args.continuous and args.stop_on_first:
        print("Continuous scanning until a gRPC service is found")

    scan_count = 0
    while True:
        scan_count += 1
        if args.continuous:
            print(f"\n--- Scan cycle #{scan_count} ---")

        found_services = []
        start_time = time.time()
        total_ports = len(hosts) * (args.end - args.start + 1)
        scanned = 0

        # Create batches of host:port combinations
        all_host_ports = [(host, port) for host in hosts for port in port_range]

        # Process in batches to avoid creating too many threads at once
        for i in range(0, len(all_host_ports), args.batch_size):
            batch = all_host_ports[i:i+args.batch_size]

            # Apply rate limiting if needed
            if args.rate > 0:
                expected_time = scanned / args.rate
                elapsed = time.time() - start_time
                if elapsed < expected_time:
                    time.sleep(expected_time - elapsed)

            # Scan the batch
            batch_results = batch_scan(batch, args.verbose, args.concurrency, args.stop_on_first)
            found_services.extend(batch_results)
            scanned += len(batch)

            # Progress update
            elapsed = time.time() - start_time
            if elapsed > 0:
                rate = scanned / elapsed
                print(f"\rScanned {scanned}/{total_ports} ports ({rate:.2f} ports/sec)", end="")

            # Stop scanning if we found a service and stop_on_first is enabled
            if args.stop_on_first and found_services:
                break

        print()  # New line after progress

        # Print results
        if found_services:
            print("\nFound gRPC services:")
            for service in found_services:
                print(f"\n{service['host']}:{service['port']}")
                if "error" in service:
                    print(f"  Error: {service['error']}")
                for svc in service['services']:
                    print(f"  - {svc}")

            # If we found services and stop_on_first is enabled, we're done
            if args.stop_on_first:
                break
        else:
            print("\nNo gRPC services found.")

        scan_time = time.time() - start_time
        print(f"\nScan completed in {scan_time:.2f} seconds")
        if scan_time > 0:
            print(f"Average scan rate: {total_ports/scan_time:.2f} ports/second")

        # If not continuous, we're done
        if not args.continuous:
            break

        # If continuous and stop_on_first but we found services, we're done
        if args.continuous and args.stop_on_first and found_services:
            break

        print("\nStarting next scan cycle...")
        # Apply rate limiting if needed
        if args.rate > 0:
            expected_time = scanned / args.rate
            elapsed = time.time() - start_time
            if elapsed < expected_time:
                time.sleep(expected_time - elapsed)
        else:
            time.sleep(1)  # Sleep for 1 second to avoid overwhelming the network

if __name__ == "__main__":
    main()
