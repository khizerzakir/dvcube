from __future__ import annotations
import argparse
import glob
import shutil
from pathlib import Path

import xarray as xr


DEFAULT_CHUNKS = {
    "time": 8,
    "lat": 256,
    "lon": 256,
    "latitude": 256,
    "longitude": 256,
    "x": 256,
    "y": 256,
}


def resolve_nc_files(input_path: str) -> list[str]:
    """
    Accepts:
    - glob pattern: /data/.../2010/*/*.nc
    - directory:    /data/.../2010
    - month dir:    /data/.../2010/01
    - single file:  /data/.../file.nc
    """
    p = Path(input_path)

    if any(ch in input_path for ch in ["*", "?", "["]):
        files = sorted(glob.glob(input_path))
        return [f for f in files if f.endswith(".nc")]

    if p.is_file() and p.suffix == ".nc":
        return [str(p)]

    if p.is_dir():
        return sorted(str(f) for f in p.rglob("*.nc"))

    raise FileNotFoundError(f"No valid input found: {input_path}")


def normalize_chunks(ds: xr.Dataset, chunks: dict[str, int]) -> xr.Dataset:
    chunk_plan: dict[str, int] = {}
    for dim, size in chunks.items():
        if dim in ds.dims:
            chunk_plan[dim] = min(size, ds.sizes[dim])
    return ds.chunk(chunk_plan)


def build_encoding(ds: xr.Dataset, chunks: dict[str, int]) -> dict[str, dict]:
    encoding: dict[str, dict] = {}

    for var in ds.data_vars:
        var_chunks = []
        for dim in ds[var].dims:
            if dim in chunks:
                var_chunks.append(min(chunks[dim], ds.sizes[dim]))
            else:
                var_chunks.append(ds.sizes[dim])
        encoding[var] = {"chunks": tuple(var_chunks)}

    return encoding


def nc_to_zarr(
    input_path: str,
    output_zarr: str,
    *,
    engine: str = "h5netcdf",
    combine: str = "by_coords",
    chunks: dict[str, int] | None = None,
    overwrite: bool = True,
    consolidated: bool = True,
    parallel: bool = True,
) -> Path:
    """
    Read NetCDF files from a custom dir/glob and write one Zarr store.
    """
    if chunks is None:
        chunks = DEFAULT_CHUNKS

    files = resolve_nc_files(input_path)
    if not files:
        raise FileNotFoundError(f"No .nc files found for: {input_path}")

    out = Path(output_zarr)
    if out.exists():
        if overwrite:
            shutil.rmtree(out)
        else:
            raise FileExistsError(f"Output exists: {output_zarr}")

    ds = xr.open_mfdataset(
        files,
        combine=combine,
        parallel=parallel,
        chunks="auto",
        engine=engine,
        coords="minimal",
        data_vars="minimal",
        compat="override",
    )

    ds = normalize_chunks(ds, chunks)
    encoding = build_encoding(ds, chunks)

    ds.to_zarr(
        output_zarr,
        mode="w",
        consolidated=consolidated,
        encoding=encoding,
        align_chunks=True,
    )

    return out


def build_default_output(input_path: str) -> str:
    p = Path(input_path)

    if any(ch in input_path for ch in ["*", "?", "["]):
        base = Path(input_path.split("*", 1)[0]).parent
        name = Path(input_path.split("*", 1)[0]).name or "dataset"
        return str(base / f"{name}.zarr")

    if p.is_dir():
        return str(p / f"{p.name}.zarr")

    if p.is_file():
        return str(p.with_suffix(".zarr"))

    return "output.zarr"


def cli() -> None:
    parser = argparse.ArgumentParser(description="Convert NetCDF files to a Zarr store.")
    parser.add_argument("input_path", help="Glob, directory, or single .nc file")
    parser.add_argument("-o", "--output", help="Output Zarr path")
    parser.add_argument("--engine", default="h5netcdf")
    parser.add_argument("--combine", default="by_coords")
    parser.add_argument("--time-chunk", type=int, default=8)
    parser.add_argument("--spatial-chunk", type=int, default=256)
    parser.add_argument("--no-overwrite", action="store_true")
    parser.add_argument("--no-parallel", action="store_true")
    args = parser.parse_args()

    output = args.output or build_default_output(args.input_path)

    chunks = {
        "time": args.time_chunk,
        "lat": args.spatial_chunk,
        "lon": args.spatial_chunk,
        "latitude": args.spatial_chunk,
        "longitude": args.spatial_chunk,
        "x": args.spatial_chunk,
        "y": args.spatial_chunk,
    }

    out = nc_to_zarr(
        input_path=args.input_path,
        output_zarr=output,
        engine=args.engine,
        combine=args.combine,
        chunks=chunks,
        overwrite=not args.no_overwrite,
        parallel=not args.no_parallel,
    )
    print(f"✓ Wrote {out}")


if __name__ == "__main__":
    cli()