# GDAL NetCDF Preprocessing Script

Processes multi-variable NetCDF files using **gdalwarp only**, regridding and clipping each subdataset (variable) to the Sahel region. Each variable is saved as a separate file organized by variable name within month folders, with metadata preserved.

## Overview

**Input**: NetCDF files with multiple subdatasets/variables  
**Output**: Individual NetCDF files organized by variable in `YYYY/MM/variable/` folders  
**Processing**: Warp to Sahel region (W: -20°, E: 55°, S: 10°, N: 20°), 0.1° resolution, bilinear resampling  
**Performance**: Parallel processing with 4 workers  
**Metadata**: Preserved from source files with `ncrename`

## Quick Start

```bash
# Run with input and output directories
cd gdal
./gdal_warp_translate.sh <input_dir> <output_dir>

# Example with test data
./gdal_warp_translate.sh ../testdata1 ../outputs/gdal_output
```

## Configuration

### **gdal.txt**
GDAL-specific parameters for warping and clipping:

```bash
# Grid resolution (degrees)
res_x=0.1
res_y=0.1

# Target extent (West, South, East, North) - Sahel region
# Covers from Mauritania/Senegal (West) to Ethiopia (East)
te_w=-20.0
te_s=10.0
te_e=55.0
te_n=20.0

# Resampling method: bilinear, nearest, cubic, mode, average
resample_method=bilinear

# No-data value in output
nodata=nan
```

## Output Structure

```
outputs/gdal_output/
└── 2010/                           # Year
    └── 01/                         # Month
        ├── var40/                  # Variable name
        │   ├── h141_2010010100_R01_var40.nc
        │   ├── h141_2010010200_R01_var40.nc
        │   └── ...
        ├── var41/
        ├── var42/
        └── var43/
└── gdal.log
```

**Filename pattern**: `{original_name}_{variable_name}.nc`  
**Metadata**: Variable names preserved with `ncrename`

## Key Commands Explained

### 1. **get_date() - Extract Date from Filename**
```bash
get_date() {
    grep -oE '(19|20)[0-9]{6}' <<< "$1" | head -1 || echo ""
}
```
**Function**: Extracts 8-digit date (YYYYMMDD) from filename  
**Example**: `h141_2010010100_R01.nc` → `20100101`  
**Purpose**: Creates YYYY/MM subdirectories from date patterns

**How it works**:
- `grep -oE '(19|20)[0-9]{6}'`: Matches century (19 or 20) + 6 digits (YYMMDD)
- `head -1`: Takes first match if multiple dates exist
- `|| echo ""`: Returns empty string if no date found

### 2. **gdalwarp - Direct Warp (No Translate)**
```bash
gdalwarp -overwrite -s_srs EPSG:4326 -t_srs EPSG:4326 -of NetCDF \
    -te $TE_W $TE_S $TE_E $TE_N \
    -tr $RES_X $RES_Y -r $RESAMPLE_METHOD \
    -dstnodata $NODATA "$sub" "$out"
```

**Key parameters**:

| Flag | Value | Meaning |
|------|-------|---------|
| `-s_srs EPSG:4326` | WGS84 | Source Spatial Reference System |
| `-t_srs EPSG:4326` | WGS84 | Target Spatial Reference System |
| `-of NetCDF` | Format | Output format (NetCDF) |
| `-te W S E N` | `-20 10 55 20` | Target Extent: West, South, East, North (Sahel region) |
| `-tr RES_X RES_Y` | `0.1 0.1` | Target Resolution in degrees |
| `-r bilinear` | Resampling | nearest, bilinear, cubic, mode, average |
| `-dstnodata nan` | No-data value | Value for missing/invalid data in output |
| `-overwrite` | — | Overwrite existing files |

**Sahel Region Extent**:
```bash
-te -20.0 10.0 55.0 20.0    # W=-20°, S=10°, E=55°, N=20°
```

**Processing directly from NetCDF subdatasets**:
- Input: `NETCDF:"/path/file.nc":var40`
- Output: NetCDF with warped data
- No intermediate GeoTIFF conversion needed

### 3. **Subdataset Detection - gdalinfo**
```bash
gdalinfo "$infile" 2>/dev/null | grep "SUBDATASET_.*_NAME="
```

**Output example**:
```
SUBDATASET_1_NAME=NETCDF:"/path/file.nc":var40
SUBDATASET_2_NAME=NETCDF:"/path/file.nc":var41
SUBDATASET_3_NAME=NETCDF:"/path/file.nc":var42
SUBDATASET_4_NAME=NETCDF:"/path/file.nc":var43
```

**Format**: `NETCDF:"file_path":variable_name`

### 4. **Variable Name Extraction**
```bash
get_var_name() { echo "$1" | awk -F':' '{print $NF}' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' ; }
```

**How it works**:
- `awk -F':' '{print $NF}'`: Split by colon, take last field
- Example: `NETCDF:"/path/file.nc":var40` → `var40`
- `sed`: Remove leading/trailing whitespace

### 5. **Metadata Preservation - ncrename**
```bash
ncrename -v "Band1","$var_name" "$output_file"
```

**Function**: Renames the output variable to preserve original name  
**Why**: GDAL creates "Band1" by default; this restores the original variable name  
**Example**: Renames `Band1` → `var40` to match source file

### 6. **Parallel Processing with xargs**
```bash
find "$IN" -type f \( -iname "*.nc" -o -iname "*.NC" \) ! -iname "test.nc" ! -iname "output.nc" -print0 | \
    xargs -0 -P 4 -I {} bash -c 'process_file "$@"' _ {}
```

**Parameters**:
- `find`: Search for *.nc files (case-insensitive)
- `! -iname "test.nc" ! -iname "output.nc"`: Exclude test files
- `-print0`: Use null delimiter (handles spaces in filenames safely)
- `xargs -0`: Read null-delimited input
- `-P 4`: Run 4 processes in parallel
- `-I {}`: Replace `{}` with filename argument

**Why null delimiters**: Prevents errors with spaces/special chars in filenames

## Processing Workflow

```
Input NetCDF with subdatasets (var40, var41, var42, var43)
        ↓
[For each subdataset in parallel]
        ↓
Extract date from filename (get_date)
        ↓
Create output directories (YYYY/MM/var_name/)
        ↓
gdalwarp: Direct warp from NetCDF subdataset to NetCDF
  - Reprojects to EPSG:4326
  - Clips to Sahel region (W: -20°, E: 55°, S: 10°, N: 20°)
  - Resamples to 0.1° × 0.1° resolution
        ↓
ncrename: Preserve variable name in output
        ↓
Save as {original_name}_{variable_name}.nc
        ↓
Log success/error to gdal.log
```

## Handling Subdatasets

Each input file may contain multiple variables:

**Example input file**: `h141_2010010100_R01.nc`

**Subdatasets** (discovered automatically):
```
SUBDATASET_1: var40  → Soil Moisture
SUBDATASET_2: var41  → Soil Temperature
SUBDATASET_3: var42  → SM Anomaly
SUBDATASET_4: var43  → ST Anomaly
```

**Output** (4 separate files):
```
var40/h141_2010010100_R01_var40.nc
var41/h141_2010010100_R01_var41.nc
var42/h141_2010010100_R01_var42.nc
var43/h141_2010010100_R01_var43.nc
```

## Logging

Log file location: `{output_folder}/gdal.log`

**Log example**:
```
Starting GDAL preprocessing at Mon Jan 26 14:06:09 UTC 2026
Input folder: /home/kzakir/dvcube/test/test_data/2010
Output folder: /home/kzakir/dvcube/test/outputs
Resampling method: bilinear
Resolution: 0.1x0.1
Bounds: W=-18.0 S=10.0 E=40.0 N=20.0

Processing h141_2010010100_R01.nc with 4 subdatasets
  Subdataset 1: var40 → var40/h141_2010010100_R01_var40.nc
  Subdataset 2: var41 → var41/h141_2010010100_R01_var41.nc
  Subdataset 3: var42 → var42/h141_2010010100_R01_var42.nc
  Subdataset 4: var43 → var43/h141_2010010100_R01_var43.nc
Successfully processed 4 subdatasets into separate files for h141_2010010100_R01.nc

Total files found: 5
Processing time: 4s
Finished at Mon Jan 26 14:06:14 UTC 2026
```

## Performance Optimization

| Setting | Current | Faster | Trade-off |
|---------|---------|--------|-----------|
| `parallel` | 4 | 8-16 | Needs more CPU/RAM |
| `resample_method` | bilinear | nearest | Less accurate |
| File size | Varies | Smaller | Lose precision |

**Tips**:
1. Increase `parallel` if CPU underutilized
2. Use `nearest` for quick preview, `bilinear` for final output
3. Process in batches if memory-constrained

## Error Handling

The script includes error checking:

| Error | Cause | Solution |
|-------|-------|----------|
| "Config file not found" | gdal.txt missing | Create gdal.txt in script directory |
| "input folder missing" | No path specified | Set input_folder in config.txt |
| "0 files found" | Wrong folder | Check input_folder path, verify *.nc files exist |
| "translation failed" | GDAL error | Check file format, run `gdalinfo file.nc` |
| "warping failed" | Regridding error | Check extent bounds and resampling method |

**Debug**: Check log file with `tail -50 gdal.log`

## Resampling Methods

| Method | Quality | Speed | Use Case |
|--------|---------|-------|----------|
| `nearest` | Low | Very Fast | Quick previews |
| `bilinear` | Good | Fast | Default choice |
| `cubic` | Very Good | Moderate | For smooth transitions |
| `mode` | Good | Fast | Categorical data |
| `average` | Good | Moderate | Averaged results |

## Troubleshooting

### No files processed
```bash
# Check input folder
ls -lh /home/kzakir/dvcube/test/test_data/2010/

# Check file permissions
chmod +r *.nc

# Check gdal can read them
gdalinfo h141_2010010100_R01.nc | head -20
```

### GDAL commands not found
```bash
# Install GDAL
sudo apt install gdal-bin

# Verify installation
gdalinfo --version
gdalwarp --version
```

### Processing too slow
```bash
# Edit config.txt - increase parallel workers
parallel = 8

# Or use faster resampling in gdal.txt
resample_method="nearest"
```

### Memory issues
```bash
# Monitor with htop
htop

# Reduce parallel workers to lower memory usage
# Edit config.txt
parallel = 2
```

## References

- [GDAL Official Docs](https://gdal.org/)
- [gdalwarp Documentation](https://gdal.org/programs/gdalwarp.html)
- [EPSG:4326 Reference](https://epsg.io/4326)
- [NetCDF Format](https://www.unidata.ucar.edu/software/netcdf/)
input_folder=/data/dv-data/2010
output_folder=/data/dv-data/gdal_output

# GDAL spatial processing parameters
res_x=0.1
res_y=0.1
te_w=-18.0
te_s=10.0
te_e=40.0
te_n=20.0
resample_method=bilinear

# NODATA value
nodata=nan

# Parallel processing
parallel=4
```

## Usage

### Process All Files

Using default configuration:
```bash
./gdal_preprocess.sh
```

With custom paths:
```bash
./gdal_preprocess.sh /path/to/input /path/to/output
```

With environment variable override:
```bash
RES_X=0.05 RES_Y=0.05 ./gdal_preprocess.sh
```

### Process Single File

Use the test script included:
```bash
./test_single_file.sh /path/to/file.nc
```

Or manually:
```bash
source config.txt
bash -c 'process_one "$1"' _ /path/to/file.nc
```

## Output Structure

Files are organized by date extracted from filename (format: YYYYMMDD):

```
/output_folder/
├── 2010/
│   ├── 01/
│   │   ├── data_20100115_processed.nc
│   │   └── data_20100125_processed.nc
│   ├── 02/
│   │   └── data_20100205_processed.nc
│   └── ...
└── gdal.log
```

Files without dates in filename are placed in the root output folder.

## Logging

The script creates a detailed log file at `${OUTPUT_FOLDER}/gdal.log`:

- Timestamp of processing start and finish
- Configuration parameters used
- Per-file processing status
- Variable names extracted and preserved
- Error messages for failed files
- Total processing time
- File count statistics

Example log output:
```
Starting GDAL preprocessing at Wed Jan 22 10:30:45 UTC 2026
Input folder: /data/dv-data/2010
Output folder: /data/dv-data/gdal_output
Resampling method: bilinear
Resolution: 0.1x0.1
Bounds: W=-18.0 S=10.0 E=40.0 N=20.0

Processed data_20100115.nc (var: temperature)
Processed data_20100125.nc (var: precipitation)
Processing data_20100205.nc with 3 subdatasets
  Subdataset 1 processed (var: sst)
  Subdataset 2 processed (var: sss)
  Subdataset 3 processed (var: wind)
Merged 3 subdatasets into data_20100205.nc

Total files found: 3
Processing time: 125s
Finished at Wed Jan 22 10:32:50 UTC 2026
```

## Variable Name Handling

The script preserves variable metadata by:

1. **Extracting variable names** from source NetCDF files using `ncdump`
2. **Skipping coordinate variables** (lat, lon, time, nbnds, etc.)
3. **Renaming GDAL's generic `Band1`** to the actual variable name using `ncrename`
4. **For subdatasets**: extracting names from HDF paths

This ensures output files maintain proper variable semantics.

## File Types Supported

- **Single variable NetCDF**: `.nc` files with one data variable
- **Multi-variable NetCDF**: Files with multiple variables are processed as subdatasets
- **HDF files**: Via GDAL's subdataset support

## Resampling Methods

Different resampling methods suit different data types:

- `nearest`: Categories, classifications (integer data)
- `bilinear`: Continuous data (default, good for temperature, precipitation)
- `cubic`: High-quality smooth resampling
- `mode`: Most frequent value
- `average`: Mean value (useful for aggregating)

## Performance Considerations

- **Parallel processing**: Set `parallel` to the number of CPU cores available
- **Resolution**: Finer resolution (`res_x`, `res_y`) takes longer
- **Bounding box**: Smaller regions process faster
- **Resampling method**: `nearest` is fastest, `cubic` is slowest

## Troubleshooting

### Files not being processed
- Check log file: `tail -f ${OUTPUT_FOLDER}/gdal.log`
- Verify file format: `gdalinfo file.nc`
- Check permissions: Files must be readable

### Variable names not preserved
- Ensure `ncdump` and `ncrename` are installed
- Check that input files are valid NetCDF
- Review log for specific errors

### Memory issues with large files
- Reduce `parallel` value
- Reduce output `res_x` and `res_y` (coarser resolution)
- Process in smaller batches

### Coordinate system issues
- Verify input SRS with: `gdalinfo -checksum file.nc | grep -i srs`
- May need to adjust `-s_srs` parameter in script

## Examples

### Process Africa region with 0.25° resolution
```bash
CONFIG_FILE=africa_config.txt ./gdal_preprocess.sh
```

Where `africa_config.txt`:
```bash
input_folder=/data/input
output_folder=/data/output/africa
res_x=0.25
res_y=0.25
te_w=-20.0
te_s=-40.0
te_e=55.0
te_n=37.0
resample_method=bilinear
nodata=-9999
parallel=8
```

### Test single file
```bash
./test_single_file.sh /data/input/mydata_20100115.nc
```

## See Also

- CDO Preprocessing: `../cdo/cdo_preprocess.sh`
- GDAL Documentation: https://gdal.org/
- CDO Manual: https://code.mpimet.mpg.de/projects/cdo/wiki
