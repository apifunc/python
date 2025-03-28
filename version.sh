#!/bin/bash
# Usuń poprzednie pliki
rm -rf *.egg-info
rm -rf dist
rm -rf build

# Zainstaluj w trybie edytowalnym
pip install -e .
python increment_init.py -f src/pifunc/__init__.py
python increment_setup.py
python changelog.py
#python increment.py
bash git.sh
bash publish.sh


# publish.sh
#!/bin/bash
echo "Starting publication process..."

# Sprawdź czy jesteśmy w virtualenv
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Aktywuj najpierw virtualenv!"
    exit 1
fi

# Upewnij się że mamy najnowsze narzędzia
pip install --upgrade pip build twine

# Usuń stare buildy
rm -rf dist/ build/ *.egg-info/

# Zbuduj paczkę
echo "Building package..."
python -m build

# Sprawdź paczkę
echo "Checking package..."
twine check dist/*

# Opublikuj na PyPI
echo "Publishing to PyPI..."
twine upload dist/*

echo "Publication complete!"