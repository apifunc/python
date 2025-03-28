Stworzę dla Ciebie skaner usług gRPC w języku Python. Skaner będzie podobny funkcjonalnie do wersji Go, ale wykorzysta biblioteki Pythona do wykonania tego zadania.

Stworzyłem dla Ciebie skaner usług gRPC w Pythonie. Ten skrypt wykorzystuje asyncio do efektywnego równoległego skanowania wielu portów i hostów.

### Główne funkcje skanera:

1. Wykrywa serwery gRPC korzystające z mechanizmu refleksji
2. Listuje wszystkie dostępne usługi na znalezionych serwerach
3. Obsługuje równoległe skanowanie wielu portów
4. Może skanować wiele hostów jednocześnie
5. Wyświetla czytelne podsumowanie wyników

### Wymagania:

```
pip install grpcio grpcio-tools
```

### Jak używać:

```bash
python grpc-scan.py --hosts "192.168.1.10,192.168.1.11" --start 8000 --end 9000 --concurrency 50
```

Parametry:
- `--hosts` lub `-H`: lista hostów do skanowania (oddzielone przecinkami)
- `--start` lub `-s`: początkowy port zakresu (domyślnie 50000)
- `--end` lub `-e`: końcowy port zakresu (domyślnie 50100)
- `--concurrency` lub `-c`: maksymalna liczba równoległych skanów (domyślnie 50)

Skaner będzie wykrywał tylko usługi gRPC, które mają włączoną refleksję, co jest typowe dla środowisk deweloperskich, ale może być wyłączone w środowiskach produkcyjnych ze względów bezpieczeństwa.