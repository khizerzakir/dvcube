#!/usr/bin/env bash
set -euo pipefail

# CDO Preprocessing - Compact Version
# Workflow: Buffer Clip → Remap → Project → Final Clip

source ./config.txt

: "${IN:?input folder missing}" "${OUT:?output folder missing}" "${GRID:?grid file missing}"
: "${WEST:?west missing}" "${SOUTH:?south missing}" "${EAST:?east missing}" "${NORTH:?north missing}"

BUFFER="${BUFFER:-0.2}" REMAP_METHOD="${REMAP_METHOD:-bilinear}" PARALLEL="${PARALLEL:-4}"
CLIP_WEST=$(awk -v w="$WEST" -v b="$BUFFER" 'BEGIN {print w - b}')
CLIP_EAST=$(awk -v e="$EAST" -v b="$BUFFER" 'BEGIN {print e + b}')
CLIP_SOUTH=$(awk -v s="$SOUTH" -v b="$BUFFER" 'BEGIN {print s - b}')
CLIP_NORTH=$(awk -v n="$NORTH" -v b="$BUFFER" 'BEGIN {print n + b}')

LOG="${OUT}/cdo.log" && mkdir -p "$OUT" && echo "CDO pipeline at $(date)" >> "$LOG"

process_cdo() {
    local file="$1" base ymd yyyy mm outdir outfile tmp1 tmp2 start end remap_op
    base="$(basename "$file")"
    [[ $base =~ ([0-9]{4})([0-9]{2})([0-9]{2}) ]] || { echo "No date in $base" >> "$LOG"; return 0; }
    yyyy="${BASH_REMATCH[1]}" mm="${BASH_REMATCH[2]}"
    outdir="${OUT}/$yyyy/$mm" && mkdir -p "$outdir" && outfile="${outdir}/${base}_processed.nc"
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
    echo "✓ $base ($(( $(date +%s) - start ))s)" >> "$LOG" || \
    echo "✗ $base failed" >> "$LOG"
}

export -f process_cdo
export OUT LOG CLIP_WEST CLIP_EAST CLIP_SOUTH CLIP_NORTH WEST SOUTH EAST NORTH GRID REMAP_METHOD

find "$IN" -type f -name "*.nc" -print0 | xargs -0 -P "$PARALLEL" -I {} bash -c 'process_cdo "$@"' _ {}

echo "Finished at $(date)" >> "$LOG"
