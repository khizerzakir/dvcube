# Kerchunk + Xvec Workflow for Climate Data

This guide documents a complete workflow for:

- Creating Kerchunk references from local NetCDF files
- Combining individual references into one virtual dataset
- Opening the virtual dataset with Xarray
- Calculating zonal statistics with Xvec
- Building a vector cube with geometry and descriptive zone attributes
- Plotting maps
- Filtering by zone category, city name, or zone ID
- Plotting city-level time series
- Avoiding common Xvec/Xarray alignment errors

---

## 1. Recommended folder structure

Store the NetCDF files and generated Kerchunk references under one data root:

```text
testdata1/
├── 01/
│   └── file_1.nc
|   └── file_2.nc  
|   └── ...     
├── 02/
│   └── file_1.nc
|   └── file_2.nc 
│   └── ...
└── kerchunk/
    ├── single/
    │   ├── file_1_nc.json
    │   ├── file_2_nc.json
    │   └── ...
    └── multi/
        └── combined_refs.json
```

The user only provides the NetCDF data directory. The script automatically creates:

```python
kerchunk_dir = data_path / "kerchunk"
single_dir = kerchunk_dir / "single"
multi_dir = kerchunk_dir / "multi"
```

---

# Part I — Creating Kerchunk references

Extract the concatenation coordinate

This helper decodes the `time` coordinate without assuming one fixed CF time-unit convention.

```python
def _extract_concat_coordinate(index: int, z, var: str, fn: str):
    """
    Extract coordinate values for concatenation without assuming
    one specific CF time-unit format.
    """
...
```


## Create safe JSON filenames

The output JSON name is derived from the relative NetCDF path.

```python
def make_safe_name(nc_path: Path, data_path: Path) -> str:
    """
    Create a unique JSON filename from the NetCDF file's relative path.

    Example
    -------
    testdata1/2010/01/file.nc
    becomes
    2010_01_file_nc.json
    """
    relative_path = nc_path.relative_to(data_path)

    safe_name = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        str(relative_path),
    )

    return f"{safe_name}.json"
```


## Create one Kerchunk reference per NetCDF file

```python
def make_single_ref(
    nc_path: Path,
    single_dir: Path,
    data_path: Path,
) -> Path:
    """
    Create one Kerchunk reference JSON for one NetCDF file.
    """
...
```

### Important path note

This line stores the absolute local path of the NetCDF file:

```python
target_url = nc_path.resolve().as_uri()
```

For example:

```text
file:///home/kzakir/test/data/test_data/testdata1/01/01/file.nc
```

If the NetCDF directory is moved later, the generated references will still point to the old location.


Combine all individual references

```python
def combine_single_refs(
    single_dir: Path,
    multi_dir: Path,
) -> Path:
    """
    Combine all individual Kerchunk references into one JSON file.
    """
   ...
```


Run the complete Kerchunk workflow

```python
func {create_kerchunk_references}
**/home/kzakir/test/cube-sample/bin/python kerchunks.py**
```


# Part II — Opening the virtual Kerchunk dataset
Open the combined reference JSON

```python
from pathlib import Path

import xarray as xr

ref_json = Path(
    "path/to/multi_refs.json"
).resolve()

if not ref_json.exists():
    raise FileNotFoundError(ref_json)

ds = xr.open_dataset(
    "reference://",
    engine="zarr",
    backend_kwargs={
        "consolidated": False,
        "storage_options": {
            "fo": str(ref_json),
            "remote_protocol": "file",
        },
    },
)

ds
```

---

## Common Kerchunk path error

A typical error is:

```text
ReferenceNotReachable
FileNotFoundError
```

This usually means the JSON file was created when the NetCDF files were stored in another directory.

Example:

```text
Current reference JSON:
    /home/kzakir/test/data/test_data/testdata1/kerchunk/...

Referenced NetCDF path:
    /home/kzakir/dvcube/test/data/test_data/testdata1/...
```

The JSON is valid, but its internal file URLs are stale.

### Preferred solution

Regenerate the Kerchunk references from the current NetCDF location.

### Alternative solution

Replace the old path prefix in the existing JSON.

```python
from pathlib import Path
import json

ref_json = Path(
    "/home/kzakir/test/data/test_data/testdata1/"
    "kerchunk/multi/combined_refs.json"
)

old_root = (
    "file:///home/kzakir/dvcube/test/data/"
    "test_data/testdata1"
)

new_root = (
    "file:///home/kzakir/test/data/"
    "test_data/testdata1"
)

with ref_json.open("r", encoding="utf-8") as file:
    references = json.load(file)

ref_mapping = references.get("refs", references)

changed = 0

for key, value in ref_mapping.items():
    if (
        isinstance(value, list)
        and len(value) >= 1
        and isinstance(value[0], str)
        and value[0].startswith(old_root)
    ):
        value[0] = value[0].replace(
            old_root,
            new_root,
            1,
        )
        changed += 1

for key, value in references.get("templates", {}).items():
    if isinstance(value, str) and value.startswith(old_root):
        references["templates"][key] = value.replace(
            old_root,
            new_root,
            1,
        )
        changed += 1

fixed_json = ref_json.with_name(
    "combined_refs_fixed.json"
)

with fixed_json.open("w", encoding="utf-8") as file:
    json.dump(references, file)

print(f"Updated references: {changed}")
print(f"Fixed JSON: {fixed_json}")
```

---

## Inspect all referenced source files

```python
import json
from pathlib import Path
from urllib.parse import urlparse

with Path(ref_json).open("r", encoding="utf-8") as file:
    references = json.load(file)

ref_mapping = references.get("refs", references)

target_urls = sorted({
    value[0]
    for value in ref_mapping.values()
    if (
        isinstance(value, list)
        and value
        and isinstance(value[0], str)
    )
})

for url in target_urls[:20]:
    local_path = Path(urlparse(url).path)

    print(
        "EXISTS" if local_path.exists() else "MISSING",
        local_path,
    )
```


# Part III — Preparing vector zones

Read and clean the zone geometries

Assume the source GeoDataFrame contains:

```text
geometry
zone_id
city_name
zone_cat
```

Prepare the zone layer:

```python
import geopandas as gpd
import numpy as np

zones = units[
    [
        "zone_id",
        "city_name",
        "zone_cat",
        "geometry",
    ]
].copy()

zones = zones.loc[
    zones.geometry.notna()
    & ~zones.geometry.is_empty
    & zones.geometry.is_valid
].reset_index(drop=True)

zones["city_name"] = zones["city_name"].astype(str)
zones["zone_cat"] = zones["zone_cat"].astype(str).str.lower()

if "zone_id" not in zones.columns:
    zones["zone_id"] = np.arange(len(zones))
```

Match raster and vector CRS

```python
print("Vector CRS:", zones.crs)
print("Raster CRS:", ds_sahel.rio.crs)

if zones.crs != ds_sahel.rio.crs:
    zones = zones.to_crs(ds_sahel.rio.crs)
```

The CRS must match before calculating zonal statistics.


# Part IV — Xvec zonal statistics

Calculate the zonal mean for one variable

```python
stats = ds_sahel["var40"].xvec.zonal_stats(
    zones.geometry,
    x_coords="lon",
    y_coords="lat",
    stats="mean",
    method="exactextract",
    name="zone",
    index=False,
)

stats = stats.rename("var40_mean")
```

---

## Calculate zonal means for several variables

Run zonal statistics on an Xarray Dataset rather than repeating the operation variable by variable.

```python
stats_ds = ds_sahel[
    [
        "var40",
        "var41",
        "var42",
    ]
].xvec.zonal_stats(
    zones.geometry,
    x_coords="lon",
    y_coords="lat",
    stats="mean",
    method="exactextract",
    name="zone",
    index=False,
)
```

Rename the output variables if desired:

```python
stats_ds = stats_ds.rename(
    {
        "var40": "var40_mean",
        "var41": "var41_mean",
        "var42": "var42_mean",
    }
)
```

Add city and zone information to the vector cube

```python
stats_ds = stats_ds.assign_coords(
    zone_id=(
        "zone",
        zones["zone_id"].to_numpy(),
    ),
    city_name=(
        "zone",
        zones["city_name"].to_numpy(),
    ),
    zone_cat=(
        "zone",
        zones["zone_cat"].to_numpy(),
    ),
)
```

The resulting structure is approximately:

```text
<xarray.Dataset>

Dimensions:
    zone
    time

Coordinates:
  * zone       (zone) GeometryIndex
  * time       (time) datetime64[ns]
    zone_id    (zone) int64
    city_name  (zone) object
    zone_cat   (zone) object

Data variables:
    var40_mean  (zone, time)
    var41_mean  (zone, time)
    var42_mean  (zone, time)
```

The `zone` coordinate should remain the geometry-backed Xvec index.

Do not overwrite it with a normal pandas index.

Avoid:

```python
stats_ds = stats_ds.assign_coords(
    zone=zones.index
)
```

---

## Optional combined mean across variables

Only calculate this when `var40`, `var41`, and `var42` represent comparable measurements with compatible units.

```python
stats_ds["combined_mean"] = (
    stats_ds[
        [
            "var40_mean",
            "var41_mean",
            "var42_mean",
        ]
    ]
    .to_array(dim="source_variable")
    .mean(
        dim="source_variable",
        skipna=True,
    )
)
```

---

# Part V — Why a sparse `zone_cat × city_name` cube may fail

Problem with `set_index(...).to_xarray()`

This pattern creates a rectangular cube:

```python
zones_cube = (
    zones
    .set_index(["zone_cat", "city_name"])
    .to_xarray()
)
```

If each city belongs to only one category, Xarray creates every possible combination of:

```text
zone_cat × city_name
```

Most combinations do not exist and contain missing geometries.

Exactextract then receives invalid or missing geometry objects and may raise:

```text
RuntimeError: Failed to parse geometry
```

For static administrative zones, the recommended structure is:

```text
zone
├── geometry
├── zone_id
├── city_name
├── zone_cat
└── variables through time
```

This is cleaner than forcing `zone_cat` and `city_name` into separate dimensions.

---

# Part VI — Alignment-safe zone filtering

Why `AlignmentError` occurs

An error such as:

```text
AlignmentError:
cannot align objects on coordinate 'zone'
because of conflicting indexes
```

usually means Xarray is trying to combine:

- an Xvec `GeometryIndex`, and
- a regular `PandasIndex`

on the same `zone` dimension.

This may happen when using:

```python
data.where(condition_from_another_object, drop=True)
```

or when merging arrays whose `zone` indexes were constructed differently.

The safest approach is to build a NumPy boolean mask from the same object and then use positional `.isel()`.

---

## Reusable alignment-safe zone selector

```python

def select_vector_zones(
    data,
    *,
    cities=None,
    zone_categories=None,
    zone_ids=None,
    zone_dim="zone",
):
    """
    Filter an Xvec vector cube without triggering coordinate alignment.
    """
...
```

Examples:

```python
urban = select_vector_zones(
    stats_ds,
    zone_categories="urban",
)
```

```python
selected_cities = select_vector_zones(
    stats_ds,
    cities=[
        "Bambey",
        "Bignona",
        "Ziguinchor",
    ],
)
```

```python
selected_zones = select_vector_zones(
    stats_ds,
    zone_ids=[
        112,
        113,
        150,
    ],
)
```

---

# Part VII — Compact Xvec map plotting

Reusable compact map function

The following function:

- Accepts an Xarray Dataset or DataArray
- Filters by `zone_cat`, `city_name`, and `zone_id`
- Selects time by index or date
- Removes Xvec's default vertical colorbar
- Adds one shared horizontal colorbar
- Reduces gaps between map panels
- Returns the selected data

`plot_zonal_maps` - `plot_city_timeseries` - `plot_city_variables`


## Map examples

### All urban zones

```python
fig, axes, selected = plot_zonal_maps(
    stats_ds,
    variable="var40_mean",
    zone_cat="urban",
    time_index=slice(0, 15),
    col_wrap=3,
    title="var40 zonal means for urban zones",
    colorbar_label="Mean var40",
)
```

### One city

```python
fig, axes, selected = plot_zonal_maps(
    stats_ds,
    variable="var40_mean",
    city_name="Bambey",
    time_index=slice(0, 15),
    col_wrap=3,
)
```

### Several cities

```python
fig, axes, selected = plot_zonal_maps(
    stats_ds,
    variable="var40_mean",
    city_name=[
        "Bambey",
        "Bignona",
        "Ziguinchor",
    ],
    time_index=slice(0, 15),
    col_wrap=3,
)
```

### Select a date range

```python
fig, axes, selected = plot_zonal_maps(
    stats_ds,
    variable="var40_mean",
    zone_cat="urban",
    time_range=(
        "2010-01-01",
        "2010-01-15",
    ),
    col_wrap=5,
)
```

### City time-series examples


```python
fig, ax, selected = plot_city_timeseries(
    stats_ds,
    variable="var40_mean",
    cities="Bambey",
    start="2010-01-01",
    end="2010-05-31",
    ylabel="Mean var40",
)
```

### Several cities

```python
fig, ax, selected = plot_city_timeseries(
    stats_ds,
    variable="var40_mean",
    cities=[
        "Bambey",
        "Bignona",
        "Ziguinchor",
    ],
    start="2010-01-01",
    end="2010-05-31",
    ylabel="Mean var40",
    title="var40 zonal mean for selected cities",
)
```

### Filter to urban cities

```python
fig, ax, selected = plot_city_timeseries(
    stats_ds,
    variable="var40_mean",
    cities=[
        "Bambey",
        "Bignona",
        "Ziguinchor",
    ],
    zone_categories="urban",
)
```

### Add a rolling mean

```python
fig, ax, selected = plot_city_timeseries(
    stats_ds,
    variable="var40_mean",
    cities=[
        "Bambey",
        "Bignona",
        "Ziguinchor",
    ],
    rolling_window=7,
    ylabel="Seven-step rolling mean",
)
```


### Multiple Variables

```python
fig, ax, selected = plot_city_variables(
    stats_ds,
    city="Bambey",
    variables=[
        "var40_mean",
        "var41_mean",
        "var42_mean",
    ],
    start="2010-01-01",
    end="2010-05-31",
)
```

Only place several variables on one y-axis when their units and scales are compatible.

---

# Part X — Convert the vector cube to a GeoDataFrame

Export one timestamp

```python
one_date_gdf = (
    stats_ds["var40_mean"]
    .isel(time=0)
    .xvec.to_geodataframe(
        name="var40_mean"
    )
)

one_date_gdf.head()
```

The output should include:

```text
geometry
zone_id
city_name
zone_cat
var40_mean
```

---

Export all times in long format

```python
long_gdf = (
    stats_ds["var40_mean"]
    .xvec.to_geodataframe(
        name="var40_mean",
        long=True,
    )
)

long_gdf.head()
```

This is useful for:

- GeoParquet export
- Tabular plotting
- DuckDB analysis
- Joining with mobility observations
- Building dashboards

---

# Part XI — Common errors and fixes

`ValueError: cannot insert geometry, already exists`

Cause:

```python
plot_data.xvec.plot(
    geometry="geometry"
)
```

when the DataArray already has a geometry-backed dimension called `geometry`.

Fix:

```python
plot_data.xvec.plot(
    col="time",
    legend=False,
)
```

For a DataArray, allow Xvec to infer the geometry coordinate.

---

`RuntimeError: Failed to parse geometry`

Typical causes:

- Missing geometry values
- Empty geometry values
- Invalid polygons
- Sparse multidimensional geometry cube
- Geometry created from an incomplete `zone_cat × city_name` grid

Clean the GeoDataFrame:

```python
zones = zones.loc[
    zones.geometry.notna()
    & ~zones.geometry.is_empty
    & zones.geometry.is_valid
].reset_index(drop=True)
```

Prefer a one-dimensional `zone` geometry coordinate.

---

## Vertical colorbar remains visible

Use:

```python
legend=False
```

and explicitly remove any extra figure axes:

```python
map_axes = list(
    np.atleast_1d(axes).ravel()
)

for extra_axis in list(fig.axes):
    if not any(extra_axis is axis for axis in map_axes):
        fig.delaxes(extra_axis)
```

Then construct a new horizontal colorbar using `ScalarMappable`.

---

`AlignmentError` on the `zone` coordinate

Avoid combining objects with different index types on `zone`.

Problematic example:

```python
urban = stats_ds.where(
    another_cube["zone_cat"] == "urban",
    drop=True,
)
```

Recommended approach:

```python
urban_mask = (
    np.asarray(stats_ds["zone_cat"].values)
    == "urban"
)

urban = stats_ds.isel(
    zone=np.flatnonzero(urban_mask)
)
```

Or use:

```python
urban = select_vector_zones(
    stats_ds,
    zone_categories="urban",
)
```

---

# Part XII — Recommended full workflow

End-to-end example

```python
# ---------------------------------------------------------
# 1. Open Kerchunk dataset
# ---------------------------------------------------------
ds = xr.open_dataset(
    "reference://",
    engine="zarr",
    backend_kwargs={
        "consolidated": False,
        "storage_options": {
            "fo": str(ref_json),
            "remote_protocol": "file",
        },
    },
)

# ---------------------------------------------------------
# 2. Spatially subset the raster dataset
# ---------------------------------------------------------
ds_sahel = ds.sel(
    lon=slice(west, east),
    lat=slice(north, south),
)

# ---------------------------------------------------------
# 3. Prepare vector zones
# ---------------------------------------------------------
zones = units[
    [
        "zone_id",
        "city_name",
        "zone_cat",
        "geometry",
    ]
].copy()

zones = zones.loc[
    zones.geometry.notna()
    & ~zones.geometry.is_empty
    & zones.geometry.is_valid
].reset_index(drop=True)

zones["zone_cat"] = (
    zones["zone_cat"]
    .astype(str)
    .str.lower()
)

if zones.crs != ds_sahel.rio.crs:
    zones = zones.to_crs(
        ds_sahel.rio.crs
    )

# ---------------------------------------------------------
# 4. Calculate all zonal means
# ---------------------------------------------------------
stats_ds = ds_sahel[
    [
        "var40",
        "var41",
        "var42",
    ]
].xvec.zonal_stats(
    zones.geometry,
    x_coords="lon",
    y_coords="lat",
    stats="mean",
    method="exactextract",
    name="zone",
    index=False,
)

# ---------------------------------------------------------
# 5. Rename variables
# ---------------------------------------------------------
stats_ds = stats_ds.rename(
    {
        "var40": "var40_mean",
        "var41": "var41_mean",
        "var42": "var42_mean",
    }
)

# ---------------------------------------------------------
# 6. Add zone metadata
# ---------------------------------------------------------
stats_ds = stats_ds.assign_coords(
    zone_id=(
        "zone",
        zones["zone_id"].to_numpy(),
    ),
    city_name=(
        "zone",
        zones["city_name"].astype(str).to_numpy(),
    ),
    zone_cat=(
        "zone",
        zones["zone_cat"].astype(str).to_numpy(),
    ),
)

# ---------------------------------------------------------
# 7. Plot compact urban maps
# ---------------------------------------------------------
fig, axes, urban_plot = plot_zonal_maps(
    stats_ds,
    variable="var40_mean",
    zone_cat="urban",
    time_index=slice(0, 15),
    col_wrap=3,
    title="var40 mean for urban zones",
    colorbar_label="Mean var40",
)

# ---------------------------------------------------------
# 8. Plot selected city time series
# ---------------------------------------------------------
fig, ax, selected_ts = plot_city_timeseries(
    stats_ds,
    variable="var40_mean",
    cities=[
        "Bambey",
        "Bignona",
        "Ziguinchor",
    ],
    start="2010-01-01",
    end="2010-05-31",
)
```

---

## Performance recommendations

For larger datasets:

```python
ds = xr.open_dataset(
    "reference://",
    engine="zarr",
    chunks={
        "time": 10,
        "lat": 500,
        "lon": 500,
    },
    backend_kwargs={
        "consolidated": False,
        "storage_options": {
            "fo": str(ref_json),
            "remote_protocol": "file",
        },
    },
)
```

Before plotting or calculating global color limits, subset the data:

```python
plot_data = stats_ds[
    "var40_mean"
].isel(
    time=slice(0, 15)
)
```

Avoid computing minimum and maximum over the full dataset when only a small time range will be plotted.

## Note:

This is a work in progress. If you have any comments of suggestions, please feel free to create an issue and contribute. 
