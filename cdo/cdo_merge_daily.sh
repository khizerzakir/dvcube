#!/usr/bin/env bash
set -euo pipefail

IN=""
OUT=""
PARALLEL=4
OVERWRITE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        -i|--input) IN="$2"; shift 2 ;;
        -o|--output) OUT="$2"; shift 2 ;;
        -p|--parallel) PARALLEL="$2"; shift 2 ;;
        --overwrite) OVERWRITE=1; shift ;;
        *) echo "USAGE: $0 -i <input_folder> -o <output_folder> [-p <parallel_processes>] [--overwrite]"; exit 1 ;;
    esac
done

[[ -n "$IN" ]] || { echo "Error: input folder missing"; exit 1; }
[[ -n "$OUT" ]] || { echo "Error: output folder missing"; exit 1; }

mkdir -p "$OUT"
LOG="${OUT}/cdo_merge.log"
START_ALL=$(date +%s)
{
    echo "Merging started at $(date)"
    echo "Input:  $IN"
    echo "Output: $OUT"
    echo "Parallel Processes: $PARALLEL"
    echo "Overwrite: $OVERWRITE"
} | tee "$LOG"

mapfile -t DIRS < <(find "$IN" -type f -name "*.nc" -printf '%h\n' | sort -u)

[[ ${#DIRS[@]} -eq 0 ]] && { echo "Error: no .nc files found in input folder"; exit 1; }

merge_one() {
    local dir="$1" rel ymd outdir outfile tmp t0
    mapfile -t files < <(find "$dir" -maxdepth 1 -type f -name "*.nc" | sort)
    [[ ${#files[@]} -gt 0 ]] || return 0
    rel="${dir#$IN/}"
    ymd="${rel//\/}"
    outdir="$OUT/$(dirname "$rel")"
    outfile="$outdir/merged_${ymd}.nc"

    if [[ -f "$outfile" && $OVERWRITE -eq 0 ]]; then
        echo "Skipping existing file: $outfile"
        return 0
    fi
    mkdir -p "$outdir"
    tmp=$(mktemp --tmpdir=/tmp merge_XXXXXX.nc)
    trap 'rm -f "$tmp"' RETURN
    t0=$(date +%s)

    if cdo -L -f nc4 -z zip4 -O mergetime "${files[@]}" "$tmp" 2>>"$LOG" && \
       cdo -L -f nc4 -z zip4 -O timsort "$tmp" "$outfile" 2>>"$LOG"; then
       echo "OK $dir ($(( $(date +%s) - t0 ))s)" >> "$LOG"
    else
       rm -f "$outfile"
       echo "FAILED $dir" >> "$LOG"
       return 1
    fi
} 

export -f merge_one
export IN OUT LOG OVERWRITE
printf "%s\n" "${DIRS[@]}" | xargs -P "$PARALLEL" -I {} bash -c 'merge_one "$@"' _ {} || true

OK=$(grep -c "^OK " "$LOG" || true)
FAILED=$(grep -c "^FAILED " "$LOG" || true)
SKIP=$(grep -c "^SKIP " "$LOG" || true)

END_ALL=$(date +%s)
ELAPSED=$((END_ALL - START_ALL))
{
    echo "Merging completed at $(date)"
    echo "Total directories: ${#DIRS[@]}"
    echo "OK: $OK"
    echo "FAILED: $FAILED"
    echo "SKIP: $SKIP"
    echo "Total time: %02d:%02d:%02d" $(($ELAPSED/3600)) $(($ELAPSED%3600/60)) $(($ELAPSED%60))
} >> "$LOG"

[[ "$FAILED" -eq 0 ]] || { echo "Some directories failed to merge. Check $LOG for details."; exit 1; }