## Pre-Processing

This repo is dedicated to compare and test 3 different tools, including GDAL, CDO, and Xarray to preprocess our climate data. We will use a small subset of our raw data that we got from EUMETSAT archival data lake:LSAF. 

### Data

We have A-`testdata1` and B-`testdata2` for our testing. "A" has only one variable, while "B" has multi variables.


### Strategy

- For temporal aggregation: We will use CDO
- For resampling: We will use GDAL 
- For cube construction: We will use Xarry and virtualzarr

### Approach

We will combine the capabilities of three key technologies:

1. **CDO** - Temporal aggregation and clipping
2. **GDAL** - Reprojection and resampling
3. **Xarray** - Zarr cube creation

### Benchmarking & Comparison

We will compare all three technologies to test and benchmark their performance on:
- **Single variable datasets** - Performance with simple data structures
- **Multi-variable datasets** - Performance with complex, multi-dimensional data

This comparison will help us identify the most efficient approach for processing climate data at scale.

---

## Project Structure

```
test/
├── cdo/                      # CDO temporal aggregation & clipping
│   ├── cdo_preprocess.sh    # Main CDO processing script
│   ├── config.txt           # CDO configuration file
│   └── grid.txt             # Grid definition for CDO
├── gdal/                     # GDAL reprojection & resampling
│   ├── gdal_warp_translate.sh  # Main GDAL processing script
│   ├── config.txt           # GDAL configuration file
│   ├── gdal.txt             # GDAL parameters (resolution, bounds, resampling method)
│   └── README.md            # GDAL-specific documentation
├── xarray/                   # Xarray Zarr cube creation
│   ├── xarray_preprocess.py # Main Xarray processing script
│   ├── run_preprocessing.sh # Wrapper script for Xarray
│   └── config.txt           # Xarray configuration file
├── testdata1/               # Single-variable test dataset
├── testdata2/               # Multi-variable test dataset
├── outputs/                 # Processing output directory
├── pyproject.toml          # UV project configuration
├── uv.lock                 # Dependency lock file
└── README.md               # This file
```

---

## Setup Instructions

### 1. Install Dependencies

Using **UV** (recommended):

```bash
cd /path/to/test
uv sync
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

### 2. Activate Virtual Environment (if using venv)

```bash
source cube-sample/bin/activate
```

---

## Running Each Tool

### CDO - Temporal Aggregation & Clipping

**Location:** `cdo/`

**Configuration:** Edit `cdo/config.txt` with your input/output paths and parameters

**Run the script:**

```bash
cd cdo
chmod +x cdo_preprocess.sh
./cdo_preprocess.sh
```

Or specify input and output directories:

```bash
./cdo_preprocess.sh <input_dir> <output_dir>
```

**Output:** Processed files in `outputs/cdo_output/`

---

### GDAL - Reprojection & Resampling

**Location:** `gdal/`

**Configuration:** 
- Edit `gdal/config.txt` for input/output paths
- Edit `gdal/gdal.txt` for GDAL parameters (resolution, bounds, resampling method)

**Run the script:**

```bash
cd gdal
chmod +x gdal_warp_translate.sh
./gdal_warp_translate.sh <input_dir> <output_dir>
```

**Example:**

```bash
./gdal_warp_translate.sh ../testdata1 ../outputs/gdal_output
```

**Output:** Processed files organized by date in `outputs/gdal_output/YYYY/MM/`

---

### Xarray - Zarr Cube Creation

**Location:** `xarray/`

**Configuration:** Edit `xarray/config.txt` with your settings

**Run the script:**

```bash
cd xarray
chmod +x run_preprocessing.sh
./run_preprocessing.sh <input_dir> <output_dir> <config_file>
```

**Example:**

```bash
./run_preprocessing.sh ../testdata1 ../outputs/xarray_outputs ./config.txt
```

Or run Python directly:

```bash
python xarray_preprocess.py
```

**Output:** Zarr cubes in `outputs/xarray_outputs/`

---

## Testing with Sample Data

Test datasets are included in the project:

- **`testdata1/`** - Single-variable dataset (for CDO and GDAL testing)
- **`testdata2/`** - Multi-variable dataset (for comprehensive benchmarking)

**Quick test:**

```bash
# CDO test
cd cdo && ./cdo_preprocess.sh ../testdata1 ../outputs/cdo_output

# GDAL test
cd ../gdal && ./gdal_warp_translate.sh ../testdata1 ../outputs/gdal_output

# Xarray test
cd ../xarray && ./run_preprocessing.sh ../testdata1 ../outputs/xarray_outputs
```

---

## Output Locations

- **CDO:** `outputs/cdo_output/` - Processed NetCDF files
- **GDAL:** `outputs/gdal_output/YYYY/MM/` - Organized by date
- **Xarray:** `outputs/xarray_outputs/` - Zarr format cubes

---

## Logs

Each tool generates a log file in its output directory:
- `outputs/cdo_output/cdo.log`
- `outputs/gdal_output/gdal.log`

Check these logs to monitor progress and troubleshoot issues.

