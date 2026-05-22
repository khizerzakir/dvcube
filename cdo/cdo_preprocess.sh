#!/usr/bin/env bash
set -euo pipefail

# If invoked via sh, restart in bash before any bash-specific syntax is parsed.
if [ -z "${BASH_VERSION:-}" ]; then
    exec /usr/bin/env bash "$0" "$@"
fi

# CDO Preprocessing with Dynamic Grid Generation
# show only one usage with all options, and read some options from config.txt
# Usage: cdo_preprocess.sh -r 0.25 -i /data/raw -o /data/processed -d FAPAR --time-type subdaily --run-merge --overwrite

source ./config.txt
: "${IN:?input folder missing}" "${OUT:?output folder missing}" "${DATASET_TYPE:?dataset type missing}"
: "${WEST:?west missing}" "${SOUTH:?south missing}" "${EAST:?east missing}" "${NORTH:?north missing}"

TIME_TYPE="${TIME_TYPE:-subdaily}"   # daily | subdaily
RUN_MERGE=0
OVERWRITE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        -r|--resolution) RESOLUTION="$2"; shift 2 ;;
        -i|--input) IN="$2"; shift 2 ;;
        -o|--output) OUT="$2"; shift 2 ;;
        -d|--dataset) DATASET_TYPE="$2"; shift 2 ;;
        -t|--time-type) TIME_TYPE="$2"; shift 2 ;;
        -p|--parallel) PARALLEL="$2"; shift 2 ;;
        --run-merge) RUN_MERGE=1; shift ;;
        --overwrite) OVERWRITE=1; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
        *) echo "USAGE: $0 -r <resolution> -i <input_folder> -o <output_folder> -d <dataset_type> [-t <time_type>] [-p <parallel_processes>] [--run-merge] [--overwrite]"; exit 1 ;;
    esac
done

OUT="${OUT}/${DATASET_TYPE}"
RESOLUTION="${RESOLUTION:-${RES:-}}"
BUFFER="${BUFFER:-0.2}"
REMAP_METHOD="${REMAP_METHOD:-bilinear}"
PARALLEL="${PARALLEL:-4}"
TMPROOT="${TMPROOT:-/tmp/cdo_preprocess}"

[[ -n "$RESOLUTION" ]] || { echo "Error: resolution not specified"; exit 1; }
[[ "$TIME_TYPE" == "daily" || "$TIME_TYPE" == "subdaily" ]] || { echo "Error: invalid time type"; exit 1; }

mkdir -p "$OUT" "$TMPROOT"
LOG="${OUT}/cdo.log"
START_ALL=$(date +%s)

python3 generate_grid.py --resolution "$RESOLUTION" >/dev/null
GRID="./grid.txt"
[[ -f "$GRID" ]] || { echo "Error: grid.txt not generated"; exit 1; }

CLIP_WEST=$(awk -v w="$WEST" -v b="$BUFFER" 'BEGIN {print w - b}')
CLIP_EAST=$(awk -v e="$EAST" -v b="$BUFFER" 'BEGIN {print e + b}')
CLIP_SOUTH=$(awk -v s="$SOUTH" -v b="$BUFFER" 'BEGIN {print s - b}')
CLIP_NORTH=$(awk -v n="$NORTH" -v b="$BUFFER" 'BEGIN {print n + b}')

{
    echo "Preprocessing started at $(date)"
    echo "Input:  $IN"
    echo "Output: $OUT"
    echo "Dataset Type: $DATASET_TYPE"
    echo "Time Type: $TIME_TYPE"
    echo "Resolution: $RESOLUTION"
    echo "Remap Method: $REMAP_METHOD"
    echo "Clip Box: W=$CLIP_WEST, E=$CLIP_EAST, S=$CLIP_SOUTH, N=$CLIP_NORTH"
    echo "Parallel Processes: $PARALLEL"
    echo "---"
} > "$LOG"
process_cdo() {
    local file="$1" base yyyy mm dd outdir outfile tmp1 remap_op t0
    base="$(basename "$file")"
    # this step makes it adaptive to folder structure
    if [[ $base =~ ([0-9]{4})([0-9]{2})([0-9]{2}) ]]; then
        yyyy="${BASH_REMATCH[1]}"; mm="${BASH_REMATCH[2]}"; dd="${BASH_REMATCH[3]}"
    elif [[ $file =~ /([0-9]{4})/([0-9]{2})/([0-9]{2})/ ]]; then
        yyyy="${BASH_REMATCH[1]}"; mm="${BASH_REMATCH[2]}"; dd="${BASH_REMATCH[3]}"
    elif [[ $file =~ /([0-9]{4})/([0-9]{2})/ ]]; then
        yyyy="${BASH_REMATCH[1]}"; mm="${BASH_REMATCH[2]}"; dd="01"
    else
        echo "No date found in $file" >> "$LOG"
        return 1
    fi

    if [[ "$TIME_TYPE" == "daily" ]]; then
        outdir="${OUT}/${yyyy}/${mm}"
    else
        outdir="${OUT}/${yyyy}/${mm}/${dd}"
    fi

    mkdir -p "$outdir"
    outfile="${outdir}/${base%.nc}_processed.nc"

    if [[ -f "$outfile" && "$OVERWRITE" -eq 0 ]]; then
        echo "SKIP $outfile" >> "$LOG"
        return 0
    fi

    case "$REMAP_METHOD" in
        bilinear) remap_op="remapbil" ;;
        nearest) remap_op="remapnn" ;;
        *) remap_op="remapbil" ;;
    esac

    tmp=$(mktemp --tmpdir="$TMPROOT" cdo_XXXXXXXX.nc)
    trap 'rm -f "$tmp"' RETURN
    t0=$(date +%s)

    if cdo -L -f nc4 -z zip_4 -O \
        -sellonlatbox,"$CLIP_WEST","$CLIP_EAST","$CLIP_SOUTH","$CLIP_NORTH" \
        "$file" "$tmp" 2>>"$LOG" && \
       cdo -L -f nc4 -z zip_4 -O \
        -"${remap_op}","$GRID" \
        "$tmp" "$outfile" 2>>"$LOG"; then
        echo "OK $file ($(( $(date +%s) - t0 ))s)" >> "$LOG"
        return 0
    else
        rm -f "$outfile"
        echo "FAILED $file" >> "$LOG"
        return 1
    fi
}

print_failed_files() {
    local failed
    mapfile -t failed < <(grep "^FAILED " "$LOG" | sed 's/^FAILED //' | sort -u)
    [[ ${#failed[@]} -gt 0 ]] || return 0

    {
        echo "Failed files:"
        for file in "${failed[@]}"; do
            # Print base filename so timestamps such as 20100101 are easy to scan.
            echo "  - $(basename "$file")"
        done
    } | tee -a "$LOG"
}

run_daily () {
    local total ok fail skip
    total=$(find "$IN" -type f -name "*.nc" ! -name "*_processed.nc" | wc -l | tr -d ' ')
    echo "Found $total files to process" >> "$LOG"

    find "$IN" -type f -name "*.nc" ! -name "*_processed.nc" -print0 | \
        xargs -0 -P "$PARALLEL" -I {} bash -c 'process_cdo "$@"' _ {} || true

    ok=$(grep -c "^OK " "$LOG" || true)
    fail=$(grep -c "^FAILED " "$LOG" || true)
    skip=$(grep -c "^SKIP " "$LOG" || true)
    echo "Processing summary: Total=$total, OK=$ok, FAILED=$fail, SKIP=$skip" >> "$LOG"
    if [[ "$fail" -ne 0 ]]; then
        print_failed_files
        echo "Some files failed to process. Check $LOG for details."
        exit 1
    fi
    }

run_subdaily () {
    local total ok fail skip
    total=$(find "$IN" -type f -name "*.nc" ! -name "*_processed.nc" | wc -l | tr -d ' ')
    echo "Found $total files to process" >> "$LOG"

    find "$IN" -type f -name "*.nc" ! -name "*_processed.nc" -print0 | \
        xargs -0 -P "$PARALLEL" -I {} bash -c 'process_cdo "$@"' _ {} || true

    ok=$(grep -c "^OK " "$LOG" || true)
    fail=$(grep -c "^FAILED " "$LOG" || true)
    skip=$(grep -c "^SKIP " "$LOG" || true)
    produced=$(find "$OUT" -type f -name "*_processed.nc" | wc -l | tr -d ' ')
    echo "Processing summary: Total=$total, OK=$ok, FAILED=$fail, SKIP=$skip, Produced=$produced" >> "$LOG"
    if [[ "$fail" -ne 0 ]]; then
        print_failed_files
        echo "Some files failed to process. Check $LOG for details."
        exit 1
    fi
    [[ "$RUN_MERGE" -eq 1 ]] || return 0
    [[ "$produced" -gt 0 ]] || { echo "No files produced, skipping merge step."; return 0; }

    bash ./cdo_merge_daily.sh -i "$OUT" -o "${OUT}_daily_15min" -p "$PARALLEL" ${OVERWRITE:+--overwrite}

}

export -f process_cdo
export OUT LOG GRID REMAP_METHOD TIME_TYPE PARALLEL OVERWRITE TMPROOT
export CLIP_WEST CLIP_EAST CLIP_SOUTH CLIP_NORTH

if [[ "$TIME_TYPE" == "daily" ]]; then
    run_daily
else
    run_subdaily
fi

END_ALL=$(date +%s)
ELAPSED=$((END_ALL - START_ALL))
DAYS=$((ELAPSED / 86400))
HOURS=$(((ELAPSED % 86400) / 3600))
MINUTES=$(((ELAPSED % 3600) / 60))
SECONDS=$((ELAPSED % 60))

{
    echo "---"
    echo "Preprocessing completed at $(date)"
    printf "Total time: %d day(s), %02d hour(s), %02d minute(s), %02d second(s) (%s seconds)\n" \
        "$DAYS" "$HOURS" "$MINUTES" "$SECONDS" "$ELAPSED"

} >> "$LOG"
echo "Preprocessing finished. Total time: ${DAYS}d-${HOURS}h-${MINUTES}m-${SECONDS}s. See $LOG for details."