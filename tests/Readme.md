
# Tests notes

This folder contains the regression test for the kerchunk workflow.

## What is covered

- generating one kerchunk reference JSON per NetCDF file
- combining multiple single-file references into one multi-file reference JSON
- handling time-coordinate values safely during the combine step

## Run the test

From the project root:

```bash
cd /home/kzakir/dvcube/test
/home/kzakir/dvcube/test/cube-sample/bin/python -m unittest tests/test_kerchunks.py
```

## Common failures and fixes

### 1. Wrong Python environment

If you see `ModuleNotFoundError` or similar import errors, use the project virtual environment explicitly:

```bash
cd /home/kzakir/dvcube/test
source cube-sample/bin/activate
```

Or run the script directly with the venv Python:

```bash
cd /home/kzakir/dvcube/test
/home/kzakir/dvcube/test/cube-sample/bin/python cube_example/kerchunks.py
```

### 2. Kerchunk combine step crashes

If the combine step fails with errors related to `NoneType` or object dtypes, use the updated workflow in [../cube_example/kerchunks.py](../cube_example/kerchunks.py). It decodes time coordinates safely before creating the combined reference JSON.

### 3. No NetCDF files found

If the workflow reports that no `.nc` files were found, verify the input path:

```bash
find ../data/test_data/testdata1 -name '*.nc' | head
```

## Expected output

After a successful run, you should see:

- single reference JSON files under [../data/test_data/testdata1/kerchunk_refs/single](../data/test_data/testdata1/kerchunk_refs/single)
- a combined reference JSON file at [../data/test_data/testdata1/kerchunk_refs/combined/combined_refs.json](../data/test_data/testdata1/kerchunk_refs/combined/combined_refs.json)
