#!/usr/bin/env bash
set -euo pipefail

# GDAL Warp Script
# Usage: ./gdal_warp_translate.sh [input_dir] [output_dir]
# If no arguments provided, reads from config.txt

# Load config file if arguments not provided
if [[ $# -eq 0 ]]; then
    [[ -f "./config.txt" ]] || { echo "Error: config.txt not found"; exit 1; }
    source "./config.txt"
    IN="$input_folder"
    OUT="$output_folder"
else
    IN="${1:?ERROR: input directory required}"
    OUT="${2:?ERROR: output directory required}"
fi

[[ -f "./gdal.txt" ]] || { echo "Error: gdal.txt not found"; exit 1; }
source "./gdal.txt"

RES_X="${RES_X:-$res_x}"
RES_Y="${RES_Y:-$res_y}"
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
        warp_sub "$sub" "$var" "${vdir}/${base%.nc}_${var}_processed.nc" && echo "  $var → ${vdir##*/}/" >> "$LOG" || echo "ERROR: $var failed" >> "$LOG"
    done <<< "$subs"
}

export -f process_file get_date get_subdatasets get_var_name warp_sub
export OUT LOG RES_X RES_Y TE_W TE_S TE_E TE_N RESAMPLE_METHOD NODATA

start=$(date +%s)
find "$IN" -type f \( -iname "*.nc" -o -iname "*.NC" \) ! -iname "test.nc" ! -iname "output.nc" -print0 | \
    xargs -0 -P 4 -I {} bash -c 'process_file "$@"' _ {}
echo "" >> "$LOG" && echo "Finished at $(date) - Time: $(($(date +%s)-start))s" >> "$LOG"
