#!/bin/bash
# Run xarray preprocessing with dvcube conda environment

eval "$(conda shell.bash hook)"
conda activate dvcube

# Use command-line arguments if provided, otherwise use defaults
INPUT="${1:-.}" 
OUTPUT="${2:-./xarray_outputs}"
CONFIG="${3:-./config.txt}"

python "$(dirname "$0")/xarray_preprocess.py" "$INPUT" "$OUTPUT" "$CONFIG"
