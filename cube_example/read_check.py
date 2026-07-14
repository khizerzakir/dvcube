import sys
from pathlib import Path

import rioxarray
import xarray as xr


def check(data_path: str | Path, file_name: str | None = None) -> Path:
    """Validate a file or directory path and return the NetCDF file to open."""

    path = Path(data_path)

    if not path.exists():
        raise FileNotFoundError(f"The path {path} does not exist.")

    if path.is_file():
        if path.suffix.lower() != ".nc":
            raise ValueError(f"The file {path} is not a NetCDF file.")
        return path

    if not path.is_dir():
        raise ValueError(f"The path {path} is neither a file nor a directory.")

    if file_name:
        selected_file = path / file_name
        if not selected_file.exists():
            raise FileNotFoundError(f"The file {selected_file} does not exist.")
        if selected_file.suffix.lower() != ".nc":
            raise ValueError(f"The file {selected_file} is not a NetCDF file.")
        return selected_file

    netcdf_files = sorted(path.rglob("*.nc"))
    if not netcdf_files:
        raise FileNotFoundError(f"No NetCDF files found in the directory {path}.")

    return netcdf_files[0]


def read(data_path: str | Path, file_name: str | None = None) -> tuple[xr.Dataset, Path]:
    """Open a NetCDF file from a file path or a directory path."""

    netcdf_file = check(data_path, file_name=file_name)
    print(f"Opening NetCDF file: {netcdf_file}")
    dataset = xr.open_dataset(netcdf_file)
    return dataset, netcdf_file


def plot(dataset: xr.Dataset, variable_name: str, crs: str = "EPSG:4326") -> None:
    """Assign a CRS and plot a variable from the dataset."""

    if variable_name not in dataset.data_vars:
        raise KeyError(f"The variable {variable_name} does not exist in the dataset.")

    assigned = dataset.rio.write_crs(crs, inplace=False)
    assigned[variable_name].plot()


def main(data_path: str | Path | None = None, file_name: str | None = None, variable_name: str | None = None) -> None:
    if data_path is None:
        data_path = input("Enter the path to a NetCDF file or data directory: ").strip()
    
    if file_name is None and Path(data_path).is_dir():
        file_name = input(
            "Enter a file name inside that directory, or press Enter to use the first NetCDF file: "
        ).strip()
        file_name = file_name or None

    try:
        dataset, netcdf_file = read(data_path, file_name=file_name)
        print(dataset.dims)
        print(dataset.coords)
        print(dataset.data_vars)
    except Exception as exc:
        print(f"An error occurred while reading the NetCDF file: {exc}")
        sys.exit(1)

    if variable_name is None:
        variable_name = input(
            f"Enter the variable name to plot from the dataset {list(dataset.data_vars)}: "
        ).strip()

    try:
        plot(dataset, variable_name)
    except Exception as exc:
        print(f"An error occurred while plotting {variable_name} from {netcdf_file}: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()