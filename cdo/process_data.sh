#!/usr/bin/env bash
set -euo pipefail
usage() {
    echo "Usage: $0 -i <input_folder> -o <output_folder> -d <dataset_type> -t <time_type> [-r 0.05] [-p <parallel_processes>] [--merge] [--overwrite]"
    exit 1
}

RESOLUTION="0.05"
PARALLEL=4
OVERWRITE=0
RUN_MERGE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        -i|--input) IN="$2"; shift 2 ;;
        -o|--output) OUT="$2"; shift 2 ;;
        -d|--dataset) DATASET_TYPE="$2"; shift 2 ;;
        -t|--time-type) TIME_TYPE="$2"; shift 2 ;;
        -r|--resolution) RESOLUTION="$2"; shift 2 ;;
        -p|--parallel) PARALLEL="$2"; shift 2 ;;
        --merge) RUN_MERGE=1; shift ;;
        --overwrite) OVERWRITE=1; shift ;;
        -h|--help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

[[ -n "${IN:-}" && -n "${OUT:-}" && -n "${DATASET_TYPE:-}" && -n "${TIME_TYPE:-}" ]] || usage
[[ "$TIME_TYPE" == "daily" || "$TIME_TYPE" == "subdaily" ]] || { echo "Error: invalid time type"; exit 1; }
[[ -d "$IN" ]] || { echo "Error: input folder does not exist"; exit 1; }

START_ALL=$(date +%s)
cmd=(./cdo_preprocess.sh
    -r "$RESOLUTION"
    -i "$IN"
    -o "$OUT"
    -d "$DATASET_TYPE"
    -t "$TIME_TYPE"
    -p "$PARALLEL"
)
[[ $RUN_MERGE -eq 1 ]] && cmd+=(--run-merge)
[[ $OVERWRITE -eq 1 ]] && cmd+=(--overwrite)

"${cmd[@]}"

END_ALL=$(date +%s)
ELAPSED=$((END_ALL - START_ALL))
printf "Total time: %02d:%02d:%02d (%s seconds)\n" \
    "$((ELAPSED / 3600))" "$((ELAPSED % 3600 / 60))" "$((ELAPSED % 60))" "$ELAPSED"
