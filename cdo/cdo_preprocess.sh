#!/usr/bin/env bash
set -euo pipefail

# CDO Preprocessing with Dynamic Grid Generation
# Usage: ./cdo_preprocess.sh                                     (reads all from config.txt)
# Usage: ./cdo_preprocess.sh -r 0.05                             (override resolution only)
# Usage: ./cdo_preprocess.sh -r 0.05 -d rzsm                     (override resolution and dataset type)
# Usage: ./cdo_preprocess.sh -r 0.05 -i /in -o /out -d metref    (override all)

source ./config.txt
: "${IN:?input folder missing}" "${OUT:?output folder missing}" "${DATASET_TYPE:?dataset type missing}"
: "${WEST:?west missing}" "${SOUTH:?south missing}" "${EAST:?east missing}" "${NORTH:?north missing}"

# Parse named arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -r|--resolution) RESOLUTION="$2"; shift 2 ;;
        -i|--input) IN="$2"; shift 2 ;;
        -o|--output) OUT="$2"; shift 2 ;;
        -d|--dataset) DATASET_TYPE="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; echo "Usage: $0 [-r RESOLUTION] [-i INPUT] [-o OUTPUT] [-d DATASET_TYPE]"; exit 1 ;;
    esac
done

# Apply dataset type to output path
OUT="${OUT}/${DATASET_TYPE}"

# If resolution not provided, read from config.txt RES variable
if [ -z "${RESOLUTION:-}" ]; then
    if [[ -v RES ]]; then
        RESOLUTION="$RES"
    else
        echo "Usage: $0 [-r RESOLUTION] [-i INPUT] [-o OUTPUT] [-d DATASET_TYPE]"
        echo "Example: $0 -r 0.05"
        echo "Example: $0 -r 0.05 -d rzsm"
        echo "Example: $0 -r 0.05 -i /path/to/input -o /path/to/output -d metref"
        exit 1
    fi
fi

# Generate grid dynamically using generate_grid.py
if [[ ! -f "generate_grid.py" ]]; then
    echo "Error: generate_grid.py not found"
    exit 1
fi
python3 generate_grid.py --resolution "$RESOLUTION" > /dev/null 2>&1 || { echo "Error generating grid"; exit 1; }
GRID="./grid.txt"
[[ -f "$GRID" ]] || { echo "Error: grid.txt not generated"; exit 1; }

BUFFER="${BUFFER:-0.2}" REMAP_METHOD="${REMAP_METHOD:-bilinear}" PARALLEL="${PARALLEL:-4}"
CLIP_WEST=$(awk -v w="$WEST" -v b="$BUFFER" 'BEGIN {print w - b}')
CLIP_EAST=$(awk -v e="$EAST" -v b="$BUFFER" 'BEGIN {print e + b}')
CLIP_SOUTH=$(awk -v s="$SOUTH" -v b="$BUFFER" 'BEGIN {print s - b}')
CLIP_NORTH=$(awk -v n="$NORTH" -v b="$BUFFER" 'BEGIN {print n + b}')

LOG="${OUT}/cdo.log" && mkdir -p "$OUT" && echo "CDO pipeline at $(date) - Resolution: $RESOLUTION" >> "$LOG"

start_time=$(date +%s)

process_cdo() {
    local file="$1" base ymd yyyy mm outdir outfile tmp1 tmp2 start end remap_op
    base="$(basename "$file")"
    [[ $base =~ ([0-9]{4})([0-9]{2})([0-9]{2}) ]] || { echo "No date in $base" >> "$LOG"; return 0; }
    yyyy="${BASH_REMATCH[1]}" mm="${BASH_REMATCH[2]}"
    outdir="${OUT}/$yyyy/$mm" && mkdir -p "$outdir" && outfile="${outdir}/${base%.nc}_processed.nc"
    [[ -f "$outfile" ]] && return 0
    
    tmp1=$(mktemp) && tmp2=$(mktemp)
    trap 'rm -f "$tmp1" "$tmp2"' RETURN
    start=$(date +%s)
    
    # Map remap method to CDO operator
    case "$REMAP_METHOD" in
        bilinear) remap_op="remapbil" ;;
        nearest) remap_op="remapnn" ;;
        *) remap_op="remapbil" ;;
    esac
    
    # Step 1: Buffer clip (larger area)
    cdo -L -f nc4 -O -sellonlatbox,"$CLIP_WEST","$CLIP_EAST","$CLIP_SOUTH","$CLIP_NORTH" "$file" "$tmp1" 2>>"$LOG" && \
    # Step 2: Remap to grid
    cdo -L -f nc4 -O -${remap_op},"$GRID" "$tmp1" "$tmp2" 2>>"$LOG" && \
    # Step 3: Final exact clip
    cdo -L -f nc4 -O -sellonlatbox,"$WEST","$EAST","$SOUTH","$NORTH" "$tmp2" "$outfile" 2>>"$LOG" && \
    echo "$base ($(( $(date +%s) - start ))s)" >> "$LOG" || \
    echo "$base failed" >> "$LOG"
}

export -f process_cdo
export OUT LOG CLIP_WEST CLIP_EAST CLIP_SOUTH CLIP_NORTH WEST SOUTH EAST NORTH GRID REMAP_METHOD

find "$IN" -type f -name "*.nc" -print0 | xargs -0 -P "$PARALLEL" -I {} bash -c 'process_cdo "$@"' _ {}

echo "" >> "$LOG"
echo "Finished at $(date) - Time: $(($(date +%s)-start_time))s" >> "$LOG"
