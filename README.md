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

### CDO - Temporal Aggregation & Clipping

**With config:**
```bash
cd cdo
chmod +x cdo_preprocess.sh
./cdo_preprocess.sh                    # Uses config.txt defaults
```

**Without config (custom resolution):**
```bash
./cdo_preprocess.sh 0.05 ../data/testdata2 ../outputs/cdo_output
```

### GDAL - Resampling & Clipping

**With config:**
```bash
cd gdal
chmod +x gdal_warp_translate.sh
./gdal_warp_translate.sh 0.1           # Uses config.txt paths
```

**Without config (explicit paths):**
```bash
./gdal_warp_translate.sh 0.1 ../data/testdata1 ../outputs/gdal_output
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

This project leverages open-source tools for climate data processing:

- **CDO** - Climate Data Operators ([https://code.mpimet.mpg.de/projects/cdo](https://code.mpimet.mpg.de/projects/cdo))
- **GDAL** - Geospatial Data Abstraction Library ([https://gdal.org/](https://gdal.org/))
- **NCO** - NetCDF Operators ([http://nco.sourceforge.net/](http://nco.sourceforge.net/))
- **Xarray** - Data structures for N-dimensional arrays ([http://xarray.pydata.org/](http://xarray.pydata.org/))
- **Zarr** - Cloud-native array storage ([https://zarr.dev/](https://zarr.dev/))
