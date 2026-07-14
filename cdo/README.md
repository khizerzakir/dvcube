# CDO preprocessing

This folder contains a small CDO-based preprocessing pipeline for NetCDF files. The main script is `cdo_preprocess.sh`, which clips input data to a Sahel bounding box, remaps it to a generated lon/lat grid, and writes processed files into a date-based output tree.

## Scripts

- `cdo_preprocess.sh` is the main entry point.
- `process_data.sh` is a convenience wrapper that validates arguments and forwards them to `cdo_preprocess.sh`.
- `cdo_merge_daily.sh` merges processed `.nc` files within each output directory into a single `merged_YYYYMMDD.nc` file.
- `generate_grid.py` generates `grid.txt` from the domain definition in `config_resolution.yaml`.

## Requirements

- `bash`
- `python3`
- `cdo`
- `PyYAML` for `generate_grid.py`

## Configuration

`config.txt` is sourced by `cdo_preprocess.sh` and provides the default runtime settings:

- `IN`: input folder
- `OUT`: output folder
- `DATASET_TYPE`: output subfolder name
- `RES`: default resolution in degrees
- `PARALLEL`: number of parallel workers
- `REMAP_METHOD`: `bilinear` or `nearest`
- `BUFFER`: clip margin in degrees
- `WEST`, `SOUTH`, `EAST`, `NORTH`: processing bounds

`config_resolution.yaml` defines the grid domain used by `generate_grid.py`:

- `lon_min`, `lon_max`
- `lat_min`, `lat_max`
- example dataset resolutions such as `metref` at `0.05` and `sm` at `0.1`

## Main workflow

`cdo_preprocess.sh` accepts these options:

- `-r, --resolution <value>`
- `-i, --input <folder>`
- `-o, --output <folder>`
- `-d, --dataset <name>`
- `-t, --time-type daily|subdaily`
- `-p, --parallel <n>`
- `--run-merge`
- `--overwrite`

If a value is not passed on the command line, the script falls back to `config.txt`. The script then:

1. Generates `grid.txt` with `python3 generate_grid.py --resolution <value>`.
2. Clips each input `.nc` file to the buffered domain.
3. Remaps the clipped file to the generated grid.
4. Writes the result as `<name>_processed.nc`.
5. Logs progress to `cdo.log` in the dataset output folder.

For `daily` mode, output is written to `OUT/<dataset>/<YYYY>/<MM>/`.
For `subdaily` mode, output is written to `OUT/<dataset>/<YYYY>/<MM>/<DD>/`.

## Example usage

Run with the values from `config.txt`:

```bash
cd /home/kzakir/dvcube/test/cdo
./cdo_preprocess.sh
```

Override the resolution, input, output, and dataset:

```bash
./cdo_preprocess.sh -r 0.05 -i /path/to/input -o /path/to/output -d FAPAR -t daily
```

Use the wrapper script instead:

```bash
./process_data.sh -i /path/to/input -o /path/to/output -d FAPAR -t subdaily -r 0.1 --merge
```

## Grid generation

`generate_grid.py` reads `config_resolution.yaml` and writes `grid.txt`.

```bash
python3 generate_grid.py --resolution 0.05
python3 generate_grid.py --resolution 0.1 --output custom_grid.txt
```

The grid size is calculated from the configured domain and the requested resolution. The script uses an inclusive endpoint calculation, so the number of cells is:

```text
xsize = round((lon_max - lon_min) / resolution) + 1
ysize = round((lat_max - lat_min) / resolution) + 1
```

## Merge step

`cdo_merge_daily.sh` groups `.nc` files by their containing directory and creates one merged file per directory:

- input: `-i <folder>`
- output: `-o <folder>`
- parallelism: `-p <n>`
- optional overwrite: `--overwrite`

This is called automatically by `cdo_preprocess.sh` only when `--run-merge` is set and the time type is `subdaily`.

## Output layout

```text
<OUT>/<DATASET_TYPE>/
├── cdo.log
├── 2010/
│   ├── 01/
│   │   ├── file_201001010000_processed.nc
│   │   └── ...
│   └── 02/
└── ...
```

When merge is enabled, a second tree is written next to the main output directory, using the suffix `_daily_15min`.
