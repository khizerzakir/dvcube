# GDAL preprocessing

This folder contains a GDAL-based workflow for processing NetCDF files with multiple subdatasets. The main script, `gdal_warp_translate.sh`, reads configuration from `config.txt` and `gdal.txt`, warps each discovered subdataset to a Sahel bounding box, and writes one output file per variable.

## Files

- `gdal_warp_translate.sh` is the main processing script.
- `config.txt` defines the default input folder, output folder, dataset type, and the GDAL config file to source.
- `gdal.txt` stores the target grid resolution, bounding box, resampling method, and nodata value.

## Requirements

- `bash`
- `gdalinfo`
- `gdalwarp`
- `ncrename`

## How it works

`gdal_warp_translate.sh` does the following:

1. Sources `config.txt` and checks that `DATASET_TYPE` is set.
2. Accepts optional overrides for resolution, input folder, output folder, and dataset type.
3. Sources `gdal.txt` and maps its values into the runtime variables used by GDAL.
4. Finds NetCDF files in the input folder, excluding `test.nc` and `output.nc`.
5. Uses `gdalinfo` to discover subdatasets inside each file.
6. Extracts a date from the filename to build a `YYYY/MM/` output path.
7. Warps each subdataset with `gdalwarp` using the configured extent, resolution, resampling method, and nodata value.
8. Renames the default `Band1` variable to the original subdataset name with `ncrename`.
9. Logs progress to `gdal.log` in the output folder.

The script runs file processing in parallel with `xargs -P <parallel>`, using the `parallel` value from `config.txt` and falling back to `4` when it is not set.

## Configuration

`config.txt` sets the defaults used by the script:

- `input_folder`: input directory, relative to the `gdal/` folder
- `output_folder`: base output directory
- `DATASET_TYPE`: dataset label appended to the output path
- `parallel`: worker count used by `xargs`
- `source_gdal`: path to the GDAL parameter file, defaulting to `gdal.txt`

`gdal.txt` controls the GDAL behavior:

- `res_x`, `res_y`: target resolution in degrees
- `te_w`, `te_s`, `te_e`, `te_n`: Sahel bounding box
- `resample_method`: GDAL resampling method, such as `bilinear`
- `nodata`: output nodata value

## Usage

Run with the defaults from `config.txt`:

```bash
cd /home/kzakir/dvcube/test/gdal
./gdal_warp_translate.sh -r 0.1
```

Override the dataset type:

```bash
./gdal_warp_translate.sh -r 0.1 -d metref
```

Override input and output folders too:

```bash
./gdal_warp_translate.sh -r 0.1 -i /path/to/input -o /path/to/output -d rzsm
```

## Output layout

Processed files are written to:

```text
<output_folder>/<DATASET_TYPE>/<YYYY>/<MM>/<variable>/
```

Each output file follows this pattern:

```text
<original_name>_<variable>_processed.nc
```

Example:

```text
outputs/gdal_output/rzsm/2010/01/var40/h141_2010010100_R01_var40_processed.nc
```

## Notes

- The script expects dates in the input filename, such as `20100101`.
- If no date is found, the file is written directly under the output root.
- The script uses `EPSG:4326` for both source and target SRS.
- If you want a different parallelism level, change `parallel` in `config.txt`.
