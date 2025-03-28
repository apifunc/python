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
python grpc-scan.py --hosts "localhost" --start 8000 --end 9000 --concurrency 50
```
```bash
 python grpc-scan.py --hosts "localhost" --continuous --verbose --start 50051 --end 50052 --concurrency 2
```

```bash
python grpc-scan.py --hosts "localhost" --verbose  --start 50051 --end 50052
python grpc-scan.py --hosts "localhost" --verbose --stop-on-first --continuous --start 50051 --end 50052
python grpc-scan.py --hosts "localhost" --verbose --stop-on-first --continuous --start 50051 --end 50052 --rate 50

 # Stop after finding the first gRPC service
python grpc-scan.py --hosts "localhost" --start 8000 --end 9000 --stop-on-first

# Short form
python grpc-scan.py -H "localhost" -s 8000 -e 9000 -f

```

Parametry:
- `--hosts` lub `-H`: lista hostów do skanowania (oddzielone przecinkami)
- `--start` lub `-s`: początkowy port zakresu (domyślnie 50000)
- `--end` lub `-e`: końcowy port zakresu (domyślnie 50100)
- `--concurrency` lub `-c`: maksymalna liczba równoległych skanów (domyślnie 50)


### Zmiany w stosunku do poprzedniej wersji:

1. Usunąłem wszystkie elementy związane z `asyncio` i `grpc.aio`
2. Zamiast tego wykorzystałem `ThreadPoolExecutor` do równoległego skanowania
3. Dodałem wstępne sprawdzenie połączenia TCP, aby szybciej przeskakiwać zamknięte porty
4. Poprawiłem obsługę wyjątków, aby lepiej radzić sobie z różnymi wersjami gRPC

### Jak zainstalować wymagane pakiety:

```bash
pip install grpcio grpcio-reflection
```

### Jak użyć:

```bash
python grpc-scan.py --hosts "192.168.188.226"
```

Ta wersja powinna być bardziej kompatybilna z różnymi instalacjami Pythona i nie wymaga nowszych wersji gRPC, które obsługują asyncio. Skaner nadal efektywnie skanuje wiele portów równolegle, ale używa wątków zamiast asynchroniczności.

Czy chciałbyś, żebym wprowadził jakieś dodatkowe modyfikacje do tego kodu?