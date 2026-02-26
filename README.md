## Preprocessing Workflow

Preprocess climate data using **CDO** (temporal) and **GDAL** (spatial) tools, then build Zarr cubes with Xarray.

**Data Flow:**
```
data/testdata1 & testdata2 
  ↓ (CDO & GDAL processing)
outputs/cdo_output/ & outputs/gdal_output/
  ↓ (Zarr cube construction)
cube_example/test_cube.ipynb
```

---

## Project Structure

```
test/
├── data/                     # Raw input data
│   ├── testdata1/           # Single-variable dataset (rzsm)
│   └── testdata2/           # Multi-variable dataset (metref)
├── cdo/                      # CDO preprocessing
│   ├── cdo_preprocess.sh    # Main script
│   └── config.txt           # Configuration
├── gdal/                     # GDAL preprocessing
│   ├── gdal_warp_translate.sh  # Main script
│   └── config.txt           # Configuration
├── outputs/                  # Processed data
│   ├── cdo_output/
│   └── gdal_output/
├── cube_example/            # Zarr cube builder
│   └── test_cube.ipynb      # Notebook to create cubes
├── requirements.txt
└── README.md
```

---

## Prerequisites

### System Libraries

Install required system tools and libraries:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y gdal-bin cdo nco
```

**macOS (Homebrew):**
```bash
brew install gdal cdo nco
```

**CentOS/RHEL:**
```bash
sudo yum install -y gdal gdal-devel cdo nco
```

### Python Dependencies

Using **UV** (recommended):

```bash
cd /path/to/test
uv sync
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

### Activate Virtual Environment

```bash
source cube-sample/bin/activate
```

---

## Running Preprocessing

### Named Arguments Quick Reference

Both scripts use **named arguments** (flags). You can override individual settings while keeping others from config:

| Flag | Long Form | Purpose |
|------|-----------|---------|
| `-r` | `--resolution` | Grid resolution (required for GDAL) |
| `-i` | `--input` | Input data folder (optional, defaults to config) |
| `-o` | `--output` | Output folder (optional, defaults to config) |
| `-d` | `--dataset` | Dataset type: `metref` or `rzsm` (optional) |

### CDO - Temporal Aggregation & Clipping

**Using config defaults:**
```bash
cd cdo
chmod +x cdo_preprocess.sh
./cdo_preprocess.sh
```

**Override resolution only (keep other settings from config):**
```bash
./cdo_preprocess.sh -r 0.05
```

**Override resolution and dataset type:**
```bash
./cdo_preprocess.sh -r 0.05 -d rzsm
```

**Override everything:**
```bash
./cdo_preprocess.sh -r 0.05 -i ../data/testdata2 -o ../outputs/cdo_output -d metref
```

### GDAL - Resampling & Clipping

**Using config defaults (requires resolution):**
```bash
cd gdal
chmod +x gdal_warp_translate.sh
./gdal_warp_translate.sh -r 0.1
```

**Override resolution and dataset type:**
```bash
./gdal_warp_translate.sh -r 0.1 -d rzsm
```

**Override everything:**
```bash
./gdal_warp_translate.sh -r 0.1 -i ../data/testdata1 -o ../outputs/gdal_output -d rzsm
```

### Zarr Cube Creation

Open and run the notebook to build Zarr cubes from processed data:
```bash
cd cube_example
jupyter notebook test_cube.ipynb
```

The notebook uses data from `outputs/cdo_output/` and `outputs/gdal_output/`.

---

## Acknowledgments

This project is inspired by the [D&V Cube Prototype](https://user.eumetsat.int/resources/user-guides/prototype-drought-and-vegetation-data-cube-guide) by EUMETSAT. 

The Climate data from [LSA-SAF](https://lsa-saf.eumetsat.int/en/). If you are using LSA SAF data in publications, follow LSA SAF attribution guidance and CC BY 4.0 requirements.

This project leverages open-source tools for climate data processing:

- **CDO** - Climate Data Operators ([https://code.mpimet.mpg.de/projects/cdo](https://code.mpimet.mpg.de/projects/cdo))
- **GDAL** - Geospatial Data Abstraction Library ([https://gdal.org/](https://gdal.org/))
- **NCO** - NetCDF Operators ([http://nco.sourceforge.net/](http://nco.sourceforge.net/))
- **Xarray** - Data structures for N-dimensional arrays ([http://xarray.pydata.org/](http://xarray.pydata.org/))
- **Zarr** - Cloud-native array storage ([https://zarr.dev/](https://zarr.dev/))
