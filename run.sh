#!/bin/bash

VENV_DIR=".venv"
echo "Checking environment setup..."
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found. Creating '$VENV_DIR' now."
    python3 -m venv "$VENV_DIR"
else
    echo "Virtual environment '$VENV_DIR' already exists. Using existing environment."
fi

source "$VENV_DIR/bin/activate"
#Core packages
CORE_PKGS=("pandas" "geopandas" "fiona")

#Google API client libraries & Excel tools
GOOGLE_PKGS=("google-api-python-client" "google-auth" "google-auth-oauthlib" "openpyxl")

ALL_PKGS=("${CORE_PKGS[@]}" "${GOOGLE_PKGS[@]}")

echo "Checking Python dependencies..."

for pkg in "${ALL_PKGS[@]}"; do
    # Check if pip show returns details about the package (suppressing output)
    if python3 -m pip show "$pkg" > /dev/null 2>&1; then
        echo "$pkg is already installed."
    else
        echo "$pkg not found. Installing now."
        python3 -m pip install "$pkg"
    fi
done

python3 main.py
read -p "Press Enter to exit"
