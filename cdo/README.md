# CDO Preprocessing with Dynamic Grid Generation

Unified CDO preprocessing with dynamic grid generation based on resolution parameter.

## Quick Start

### Option 1: Use Default Resolution (from config.txt)
```bash
./cdo_preprocess.sh
```
Uses `RES` variable from `config.txt` (default: 0.05)

### Option 2: Specify Resolution
```bash
./cdo_preprocess.sh 0.05
./cdo_preprocess.sh 0.1
```
Overrides default resolution and auto-generates grid

### Option 3: Custom Input/Output Paths
```bash
./cdo_preprocess.sh 0.05 /path/to/input /path/to/output
```

## How It Works

1. **config.txt** - Contains `RES` variable (default resolution), input/output paths, and domain bounds
2. **config_resolution.yaml** - Contains domain boundaries and dataset resolutions (reference only)
3. **generate_grid.py** - Reads config and generates `grid.txt` dynamically based on resolution
4. **cdo_preprocess.sh** - Main preprocessing script that:
   - Accepts resolution as parameter (or reads from config.txt)
   - Auto-generates grid.txt using generate_grid.py
   - Runs CDO processing pipeline
   - Outputs results to configured output directory

## Available Resolutions

Edit `config.txt` `RES` variable to change default resolution:
```bash
RES=0.05    # METREF resolution (smaller = higher detail, slower)
RES=0.1     # SM resolution (larger = lower detail, faster)
RES=0.02    # Custom high-resolution processing
```

## Usage Examples

### Basic Usage (uses default from config.txt)

In this case you need to make changes in your config file 
```bash
cd /home/kzakir/dvcube/test/cdo
./cdo_preprocess.sh
```

otherwise, you can use the following configuration as well

### METREF Processing (0.05° resolution)
```bash
./cdo_preprocess.sh 0.05
```
- Auto-generates grid with 1500×200 cells
- Processes all .nc files in `testdata1`
- Outputs to `outputs/cdo_output`

### SM Processing (0.1° resolution)
```bash
./cdo_preprocess.sh 0.1
```
- Auto-generates grid with 750×100 cells
- Processes all .nc files
- Outputs to `outputs/cdo_output`

### Custom Resolution with Custom Paths
```bash
./cdo_preprocess.sh 0.02 ../inputs/custom_data ../outputs/custom_output
```
- Uses 0.02° resolution
- Reads from `../inputs/custom_data`
- Outputs to `../outputs/custom_output`

## Grid Calculation

Formula used by `generate_grid.py`:
```
xsize = (lon_max - lon_min) / resolution
ysize = (lat_max - lat_min) / resolution
```

Example calculations:
```
Resolution 0.05°:
  xsize = (55 - (-20)) / 0.05 = 1500
  ysize = (20 - 10) / 0.05 = 200
  Total cells = 300,000

Resolution 0.1°:
  xsize = (55 - (-20)) / 0.1 = 750
  ysize = (20 - 10) / 0.1 = 100
  Total cells = 75,000

Resolution 0.02°:
  xsize = (55 - (-20)) / 0.02 = 3750
  ysize = (20 - 10) / 0.02 = 500
  Total cells = 1,875,000
```

## Processing Pipeline

What happens when you run `./cdo_preprocess.sh 0.05`:

1. **Resolution Parameter** → Uses 0.05 (or reads from config.txt if not specified)
2. **Config Loading** → Reads `config.txt` for IN, OUT, domain bounds
3. **Grid Generation** → Calls `python3 generate_grid.py --resolution 0.05`
   - Creates `grid.txt` with calculated xsize/ysize
4. **CDO Processing** (for each .nc file in parallel):
   - Step 1: Buffer clip (add 0.2° margin around domain)
   - Step 2: Remap to grid using bilinear interpolation
   - Step 3: Final exact clip to domain bounds
5. **Output** → Organized by year/month: `outputs/cdo_output/YYYY/MM/`
6. **Logging** → Progress saved to `outputs/cdo_output/cdo.log`

## Advanced: Manual Grid Generation

If you only want to generate grid without processing:
```bash
python3 generate_grid.py --resolution 0.05
python3 generate_grid.py --resolution 0.1 --output custom_grid.txt
```

## Configuration Files

### config.txt
```bash
IN=../testdata1              # Input folder path
OUT=../outputs/cdo_output    # Output folder path
RES=0.05                     # Default resolution
PARALLEL=4                   # Number of parallel processes
REMAP_METHOD=bilinear        # CDO remapping method
BUFFER=0.2                   # Buffer zone around domain (degrees)
WEST=-20.0                   # Domain bounds (Sahel region)
SOUTH=10.0
EAST=55.0
NORTH=20.0
```

### config_resolution.yaml
```yaml
domain:
  lon_min: -20.0             # Western boundary
  lon_max: 55.0              # Eastern boundary
  lat_min: 10.0              # Southern boundary
  lat_max: 20.0              # Northern boundary
datasets:
  metref:
    resolution: 0.05         # METREF dataset resolution
  sm:
    resolution: 0.1          # SM dataset resolution
```

## Troubleshooting

### "Error generating grid"
- Ensure `config_resolution.yaml` exists with proper domain values
- Check that `generate_grid.py` is executable: `chmod +x generate_grid.py`

### "Error: input folder missing"
- Set `IN` in `config.txt` or provide explicit path: `./cdo_preprocess.sh 0.05 /path/in /path/out`

### Processing is slow
- Reduce resolution (0.1 instead of 0.05)
- Increase parallel processes: Edit `PARALLEL=8` in config.txt
- Check available disk space for output

## Output Structure

```
outputs/cdo_output/
├── 2010/
│   ├── 01/
│   │   ├── filename_201001010000.nc_processed.nc
│   │   ├── filename_201001020000.nc_processed.nc
│   │   └── ...
│   ├── 02/
│   └── ...
└── cdo.log                  # Processing log with timestamps and times
```
