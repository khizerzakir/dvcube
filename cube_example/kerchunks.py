import re
from pathlib import Path

import fsspec
import numpy as np
import ujson

from kerchunk.combine import MultiZarrToZarr
from kerchunk.hdf import SingleHdf5ToZarr


def _extract_concat_coordinate(index: int, z, var: str, fn: str):
    """Extract coordinate values for concatenation without assuming CF time units."""
    if var not in z:
        raise KeyError(f"Coordinate '{var}' not found in {fn}")

    coord = z[var]
    values = coord[...]

    if hasattr(values, "dtype") and values.dtype.kind in {"M", "m"}:
        return values

    units = coord.attrs.get("units")

    if units:
        try:
            import cftime

            decoded = cftime.num2date(
                values,
                units=units,
                calendar=coord.attrs.get("calendar", "standard"),
            )

            decoded = np.asarray(decoded).ravel()

            converted = []
            for item in decoded:
                if hasattr(item, "datetime"):
                    converted.append(item.datetime)
                elif hasattr(item, "to_datetime"):
                    converted.append(item.to_datetime())
                else:
                    converted.append(item)

            try:
                return np.asarray(converted, dtype="datetime64[ns]")
            except (TypeError, ValueError):
                return np.asarray(
                    [str(item) for item in converted],
                    dtype=object,
                )

        except Exception:
            pass

    if isinstance(values, np.ndarray) and values.dtype == object:
        converted = []

        for item in values.ravel():
            if hasattr(item, "datetime"):
                converted.append(item.datetime)
            elif hasattr(item, "to_datetime"):
                converted.append(item.to_datetime())
            else:
                converted.append(item)

        try:
            return np.asarray(converted, dtype="datetime64[ns]")
        except (TypeError, ValueError):
            return np.asarray(
                [str(item) for item in converted],
                dtype=object,
            )

    return values


def make_safe_name(nc_path: Path, data_path: Path) -> str:
    """
    Create a unique JSON filename based on the NetCDF file's relative path.

    Example:
        data/2010/01/file.nc
        becomes:
        2010_01_file_nc.json
    """
    relative_path = nc_path.relative_to(data_path)
    safe_name = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        str(relative_path),
    )

    return f"{safe_name}.json"


def make_single_ref(
    nc_path: Path,
    single_dir: Path,
    data_path: Path,
) -> Path:
    """Create one Kerchunk reference JSON for a NetCDF file."""
    single_dir.mkdir(parents=True, exist_ok=True)

    output_json = single_dir / make_safe_name(
        nc_path=nc_path,
        data_path=data_path,
    )

    target_url = nc_path.resolve().as_uri()

    with fsspec.open(target_url, mode="rb") as file_obj:
        translator = SingleHdf5ToZarr(
            file_obj,
            target_url,
            inline_threshold=300,
        )
        references = translator.translate()

    with output_json.open("w", encoding="utf-8") as handle:
        ujson.dump(references, handle)

    return output_json


def combine_single_refs(
    single_dir: Path,
    multi_dir: Path,
) -> Path:
    """Combine all single Kerchunk references into one reference JSON."""
    multi_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(single_dir.glob("*.json"))

    if not json_files:
        raise FileNotFoundError(
            f"No single-reference JSON files found in {single_dir}."
        )

    print(f"\nCombining {len(json_files)} reference JSON files...")

    mzz = MultiZarrToZarr(
        path=[str(file.resolve()) for file in json_files],
        remote_protocol="file",
        concat_dims=["time"],
        identical_dims=["lat", "lon"],
        inline_threshold=0,
        coo_map={
            "time": _extract_concat_coordinate,
        },
        coo_dtypes={
            "time": "datetime64[ns]",
        },
    )

    combined_references = mzz.translate()
    combined_json = multi_dir / "combined_refs.json"

    with combined_json.open("w", encoding="utf-8") as handle:
        ujson.dump(combined_references, handle)

    print(f"Combined reference created: {combined_json}")

    return combined_json


def create_kerchunk_references(data_path: str | Path) -> Path:
    """
    Create single and combined Kerchunk references.

    Output structure:

        data_path/
        └── kerchunk/
            ├── single/
            └── multi/
    """
    data_path = Path(data_path).expanduser().resolve()

    if not data_path.exists():
        raise FileNotFoundError(
            f"Data directory does not exist: {data_path}"
        )

    if not data_path.is_dir():
        raise NotADirectoryError(
            f"The supplied path is not a directory: {data_path}"
        )

    kerchunk_dir = data_path / "kerchunk"
    single_dir = kerchunk_dir / "single"
    multi_dir = kerchunk_dir / "multi"

    single_dir.mkdir(parents=True, exist_ok=True)
    multi_dir.mkdir(parents=True, exist_ok=True)

    nc_files = sorted(data_path.rglob("*.nc"))

    if not nc_files:
        raise FileNotFoundError(
            f"No NetCDF files found inside {data_path}."
        )

    print(f"Data directory:       {data_path}")
    print(f"Single references:    {single_dir}")
    print(f"Combined reference:   {multi_dir}")
    print(f"NetCDF files found:   {len(nc_files)}\n")

    generated_files = []

    for index, nc_file in enumerate(nc_files, start=1):
        print(
            f"[{index}/{len(nc_files)}] "
            f"Processing: {nc_file.relative_to(data_path)}"
        )

        output_json = make_single_ref(
            nc_path=nc_file,
            single_dir=single_dir,
            data_path=data_path,
        )

        generated_files.append(output_json)

    combined_json = combine_single_refs(
        single_dir=single_dir,
        multi_dir=multi_dir,
    )

    print("\nKerchunk generation completed.")
    print(f"Single references created: {len(generated_files)}")
    print(f"Combined reference: {combined_json}")

    return combined_json


if __name__ == "__main__":
    input_path = input(
        "Enter the directory containing the NetCDF files: "
    ).strip()

    create_kerchunk_references(input_path)