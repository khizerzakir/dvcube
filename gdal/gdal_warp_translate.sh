#!/usr/bin/env bash
set -euo pipefail

# GDAL Warp Script with Dynamic Resolution
# Usage: ./gdal_warp_translate.sh -r <resolution>                                   (from config.txt, override resolution)
# Usage: ./gdal_warp_translate.sh -r 0.05 -d rzsm                                   (from config.txt, override resolution and dataset)
# Usage: ./gdal_warp_translate.sh -r 0.05 -i /in -o /out -d rzsm                   (override all)

[[ -f "./config.txt" ]] || { echo "Error: config.txt not found"; exit 1; }
source "./config.txt"
: "${DATASET_TYPE:?dataset type missing}"

# Parse named arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -r|--resolution) RESOLUTION="$2"; shift 2 ;;
        -i|--input) input_folder="$2"; shift 2 ;;
        -o|--output) output_folder="$2"; shift 2 ;;
        -d|--dataset) DATASET_TYPE="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; echo "Usage: $0 -r RESOLUTION [-i INPUT] [-o OUTPUT] [-d DATASET_TYPE]"; exit 1 ;;
    esac
done

# Check if resolution was provided
if [ -z "${RESOLUTION:-}" ]; then
    echo "Usage: $0 -r RESOLUTION [-i INPUT] [-o OUTPUT] [-d DATASET_TYPE]"
    echo "Example: $0 -r 0.05"
    echo "Example: $0 -r 0.05 -d rzsm"
    echo "Example: $0 -r 0.05 -i /path/to/input -o /path/to/output -d rzsm"
    exit 1
fi

# Use provided or default paths
IN="${input_folder}"
OUT="${output_folder}/${DATASET_TYPE}"

[[ -f "./gdal.txt" ]] || { echo "Error: gdal.txt not found"; exit 1; }
source "./gdal.txt"

RES_X="$RESOLUTION"
RES_Y="$RESOLUTION"
TE_W="${TE_W:-$te_w}"
TE_S="${TE_S:-$te_s}"
TE_E="${TE_E:-$te_e}"
TE_N="${TE_N:-$te_n}"
RESAMPLE_METHOD="${RESAMPLE_METHOD:-$resample_method}"
NODATA="${NODATA:-$nodata}"

LOG="${OUT}/gdal.log" && mkdir -p "$OUT" && echo "Starting GDAL warp at $(date)" >> "$LOG"

# Extract date (YYYYMMDD) and subdatasets from file
get_date() { grep -oE '(19|20)[0-9]{6}' <<< "$1" | head -1 || echo ""; }
get_subdatasets() { gdalinfo "$1" 2>/dev/null | grep "SUBDATASET_.*_NAME=" | awk -F'=' '{print $2}' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' || true; }
get_var_name() { echo "$1" | awk -F':' '{print $NF}' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' ; }

# Warp subdataset
warp_sub() {
    local sub="$1" var="$2" out="$3"
    gdalwarp -overwrite -s_srs EPSG:4326 -t_srs EPSG:4326 -of NetCDF \
        -te "$TE_W" "$TE_S" "$TE_E" "$TE_N" \
        -tr "$RES_X" "$RES_Y" -r "$RESAMPLE_METHOD" -dstnodata "$NODATA" "$sub" "$out" 2>>"$LOG" && \
    ncrename -v "Band1","$var" "$out" 2>>"$LOG" || true
}

# Process file
process_file() {
    local file="$1" base ymd yyyy mm outdir subs var vdir
    base="$(basename "$file")"
    ymd="$(get_date "$base")" && outdir="${OUT}/${ymd:0:4}/${ymd:4:2}"
    [[ -z "$ymd" ]] && outdir="$OUT" && echo "WARNING: No date in $base" >> "$LOG"
    
    subs="$(get_subdatasets "$file")"
    [[ -z "$subs" ]] && return 0
    
    while read -r sub; do
        var="$(get_var_name "$sub")" && vdir="${outdir}/${var}" && mkdir -p "$vdir"
        warp_sub "$sub" "$var" "${vdir}/${base%.*}_${var}_processed.nc" && echo "  $var → ${vdir##*/}/" >> "$LOG" || echo "ERROR: $var failed" >> "$LOG"
    done <<< "$subs"
}

export -f process_file get_date get_subdatasets get_var_name warp_sub
export OUT LOG RES_X RES_Y TE_W TE_S TE_E TE_N RESAMPLE_METHOD NODATA

start=$(date +%s)
find "$IN" -type f \( -iname "*.nc" -o -iname "*.NC" \) ! -iname "test.nc" ! -iname "output.nc" -print0 | \
    xargs -0 -P 4 -I {} bash -c 'process_file "$@"' _ {}
echo "" >> "$LOG" && echo "Finished at $(date) - Time: $(($(date +%s)-start))s" >> "$LOG"