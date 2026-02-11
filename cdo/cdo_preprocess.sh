#!/usr/bin/env bash
set -euo pipefail

# usage: cdo_proprocess.sh config.txt

# config.txt

CONFIG_FILE="./config.txt"

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Config file '$CONFIG_FILE' not found."
    exit 1
fi

source "$CONFIG_FILE"

mkdir -p "$OUT"
LOG="${OUT%/}/cdo.log"

# Validate required parameters
: "${IN:?input folder missing}"
: "${OUT:?output folder missing}"   
: "${GRID:?grid file missing}"
: "${WEST:?bounding box west missing}"
: "${SOUTH:?bounding box south missing}"
: "${EAST:?bounding box east missing}"
: "${NORTH:?bounding box north missing}"
: "${RES:?resolution missing}"

BUFFER="${BUFFER:-0.0}"  # default buffer if not set
REMAP_METHOD="${REMAP_METHOD:-bilinear}"  # default remap method if not set

CLIP_WEST=$(awk -v w="$WEST" -v b="$BUFFER" 'BEGIN {print w - b}')
CLIP_EAST=$(awk -v e="$EAST" -v b="$BUFFER" 'BEGIN {print e + b}')
CLIP_SOUTH=$(awk -v s="$SOUTH" -v b="$BUFFER" 'BEGIN {print s - b}')
CLIP_NORTH=$(awk -v n="$NORTH" -v b="$BUFFER" 'BEGIN {print n + b}')

PARALLEL="${PARALLEL:-4}"

# Clear previous log
echo "Starting CDO preprocessing pipeline at $(date)" > "$LOG"
echo "GRID file: $GRID" >> "$LOG"
echo "Bounding box: $CLIP_WEST, $CLIP_EAST, $CLIP_SOUTH, $CLIP_NORTH" >> "$LOG"
echo "Resolution: $RES" >> "$LOG"
echo "Remap method: $REMAP_METHOD" >> "$LOG"
echo "Buffer: $BUFFER" >> "$LOG"
echo "" >> "$LOG"

# Export variables for subshells created by xargs
export OUT GRID LOG CLIP_WEST CLIP_EAST CLIP_SOUTH CLIP_NORTH RES REMAP_METHOD BUFFER

find "$IN" -type f -name "*.nc" | while read -r file; do

    BASENAME=$(basename "$file")

    if [[ $BASENAME =~ ([0-9]{4})([0-9]{2})([0-9]{2}) ]]; then
        YEAR="${BASH_REMATCH[1]}"
        MONTH="${BASH_REMATCH[2]}"
        DAY="${BASH_REMATCH[3]}"
    else
        echo "WARNING: No date found in filename $BASENAME, skipping." >> "$LOG"
        continue
    fi

    OUTDIR="${OUT%/}/$YEAR/$MONTH"
    mkdir -p "$OUTDIR"
    OUTFILE="${OUTDIR}/${BASENAME}_processed.nc"
    if [[ -f "$OUTFILE" ]]; then
        continue  # Skip existing files
    fi

tmpfile=$(mktemp temp_clip_XXXXXX.nc)
remapped_file=$(mktemp temp_remapped_XXXXXX.nc)
echo "Processing $BASENAME ..." >> "$LOG"
start=$(date +%s)

# Step 1: Buffered clip (larger area to reduce compute)
cdo -L -f nc4 -O -sellonlatbox,"$CLIP_WEST","$CLIP_EAST","$CLIP_SOUTH","$CLIP_NORTH" \
    "$file" "$tmpfile" 2>&1 >> "$LOG"

# Step 2: Remap to target grid
case "$REMAP_METHOD" in
    bilinear)
        cdo -L -f nc4 -O -remapbil,"$GRID" "$tmpfile" "$remapped_file" 2>&1 >> "$LOG"
        ;;
    nearest)
        cdo -L -f nc4 -O -remapnn,"$GRID" "$tmpfile" "$remapped_file" 2>&1 >> "$LOG"
        ;;
    *)
        echo "ERROR: Unknown remap method '$REMAP_METHOD' for $BASENAME" >> "$LOG"
        rm -f "$tmpfile" "$remapped_file"
        continue
        ;;
esac

# Step 3: Final exact clip
cdo -L -f nc4 -O -sellonlatbox,"$WEST","$EAST","$SOUTH","$NORTH" \
    "$remapped_file" "$OUTFILE" 2>&1 >> "$LOG"

# Cleanup temp files
rm -f "$tmpfile" "$remapped_file"

end=$(date +%s)
elapsed=$((end - start))
echo "Finished $BASENAME in ${elapsed}s" >> "$LOG"

done


