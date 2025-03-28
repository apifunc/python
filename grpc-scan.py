#!/usr/bin/env python3
import argparse
import sys
import time
import socket
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Dict

import grpc
from grpc._channel import _Rendezvous


# Potrzebne będą pakiety:
# pip install grpcio grpcio-reflection

class GrpcServiceInfo:
    def __init__(self, address: str, port: int, services: List[str] = None):
        self.address = address
        self.port = port
        self.services = services or []

    def __str__(self) -> str:
        return f"{self.address}:{self.port} - {len(self.services)} usług"


def scan_grpc_service(host: str, port: int, timeout: int = 3) -> Optional[GrpcServiceInfo]:
    """Skanuje pojedynczy port pod kątem usług gRPC z włączoną refleksją"""
    target = f"{host}:{port}"

    # Najpierw sprawdź, czy port jest w ogóle otwarty, aby uniknąć długiego oczekiwania
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex((host, port))
    sock.close()

    if result != 0:
        # Port jest zamknięty, nie ma sensu sprawdzać gRPC
        return None

    try:
        # Tworzymy kanał komunikacji z serwerem gRPC
        options = [('grpc.enable_http_proxy', 0)]
        channel = grpc.insecure_channel(target, options=options)

        # Dodajemy timeout
        grpc.channel_ready_future(channel).result(timeout=timeout)

        try:
            # Importujemy reflection dopiero tutaj, aby uniknąć błędów importu
            from grpc_reflection.v1alpha.reflection_pb2 import ServerReflectionRequest
            from grpc_reflection.v1alpha.reflection_pb2_grpc import ServerReflectionStub

            # Tworzymy klienta refleksji
            stub = ServerReflectionStub(channel)

            # Przygotowujemy zapytanie o listę usług
            request = ServerReflectionRequest(list_services="")

            # Wykonujemy zapytanie (synchronicznie)
            responses = list(stub.ServerReflection([request]))

            # Przetwarzamy odpowiedź
            services = []
            for response in responses:
                if response.HasField("list_services_response"):
                    services = [service.name for service in response.list_services_response.service]
                    break

            # Zamykamy kanał
            channel.close()

            # Jeśli znaleźliśmy usługi, zwracamy informacje
            if services:
                return GrpcServiceInfo(host, port, services)

        except ImportError:
            print("Brak modułu grpc_reflection. Zainstaluj go używając: pip install grpcio-reflection", file=sys.stderr)
            sys.exit(1)

    except grpc.FutureTimeoutError:
        # Timeout - port otwarty, ale to nie jest serwer gRPC
        pass
    except (grpc.RpcError, _Rendezvous) as e:
        # RpcError - ignorujemy, oznacza najczęściej brak usługi gRPC
        pass
    except Exception as e:
        if "Channel closed!" not in str(e):  # Ignorujemy błędy zamknięcia kanału
            print(f"Błąd podczas skanowania {target}: {str(e)}", file=sys.stderr)

    return None


def scan_port_range(host: str, start_port: int, end_port: int, max_workers: int) -> List[GrpcServiceInfo]:
    """Skanuje zakres portów równolegle z ograniczeniem współbieżności"""
    results = []
    ports = range(start_port, end_port + 1)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Funkcja pomocnicza do wyświetlania wyników w miarę ich znajdowania
        def process_result(port, future):
            result = future.result()
            if result:
                print(f"Znaleziono usługi gRPC na {host}:{port}")
                for service in result.services:
                    print(f"  - {service}")
                results.append(result)

        # Uruchamiamy zadania skanowania portów
        futures = {}
        for port in ports:
            future = executor.submit(scan_grpc_service, host, port)
            futures[future] = port

        # Pobieramy wyniki w miarę ich zakończenia
        for future in futures:
            port = futures[future]
            try:
                process_result(port, future)
            except Exception as e:
                print(f"Błąd podczas przetwarzania wyników dla {host}:{port}: {str(e)}", file=sys.stderr)

    return results


def scan_hosts(hosts: List[str], start_port: int, end_port: int, max_workers: int) -> Dict[str, List[GrpcServiceInfo]]:
    """Skanuje wiele hostów, każdy z nich w zadanym zakresie portów"""
    results = {}

    for host in hosts:
        print(f"\nRozpoczynam skanowanie {host} (porty {start_port}-{end_port})...")
        start_time = time.time()

        host_results = scan_port_range(host, start_port, end_port, max_workers)
        results[host] = host_results

        duration = time.time() - start_time
        print(f"Zakończono skanowanie {host}: znaleziono {len(host_results)} usług gRPC ({duration:.2f}s)")

    return results


def print_summary(results: Dict[str, List[GrpcServiceInfo]]):
    """Wyświetla podsumowanie wyników skanowania"""
    print("\n=== Podsumowanie skanowania ===")

    total_services = sum(len(host_results) for host_results in results.values())
    print(f"Przeskanowano {len(results)} hostów, znaleziono {total_services} aktywnych usług gRPC")

    for host, host_results in results.items():
        if host_results:
            print(f"\n{host}:")
            for info in host_results:
                print(f"  Port {info.port}:")
                for service in info.services:
                    print(f"    - {service}")


def main():
    parser = argparse.ArgumentParser(description="Skaner usług gRPC")
    parser.add_argument("--hosts", "-H", default="localhost",
                        help="Lista hostów do skanowania (oddzielone przecinkami)")
    parser.add_argument("--start", "-s", type=int, default=50000, help="Początkowy port zakresu")
    parser.add_argument("--end", "-e", type=int, default=50100, help="Końcowy port zakresu")
    parser.add_argument("--concurrency", "-c", type=int, default=50, help="Maksymalna liczba równoległych skanów")
    args = parser.parse_args()

    hosts = [host.strip() for host in args.hosts.split(",")]

    if args.end < args.start:
        print("Błąd: port końcowy musi być większy lub równy portowi początkowemu", file=sys.stderr)
        sys.exit(1)

    results = scan_hosts(hosts, args.start, args.end, args.concurrency)
    print_summary(results)


if __name__ == "__main__":
    main()