from pathlib import Path
import shutil


def flatten_nested_folders(
    root_dir: str | Path,
    *,
    keep_levels: int = 2,
    pattern: str = "*.nc",
    dry_run: bool = True,
    collision: str = "path_prefix",
    remove_empty_dirs: bool = True,
) -> list[tuple[str, str]]:
    """
    Move files from deeply nested directories while preserving a fixed
    number of directory levels below the root.

    Example with keep_levels=2
    --------------------------
    root/YYYY/MM/DD/file.nc
        -> root/YYYY/MM/file.nc

    root/dir/subdir/subsubdir/file.nc
        -> root/dir/subdir/file.nc

    root/dir/subdir/a/b/c/file.nc
        -> root/dir/subdir/file.nc

    Parameters
    ----------
    root_dir
        Root directory to process.

    keep_levels
        Number of directory levels below `root_dir` to preserve.

        keep_levels=0:
            root/a/b/file.nc -> root/file.nc

        keep_levels=1:
            root/a/b/file.nc -> root/a/file.nc

        keep_levels=2:
            root/a/b/c/file.nc -> root/a/b/file.nc

    pattern
        File pattern to move, such as "*.nc", "*.json", or "*".

    dry_run
        If True, print planned moves without changing files.

    collision
        Action when the destination file already exists:

        - "raise": raise FileExistsError
        - "skip": do not move the source file
        - "overwrite": overwrite the existing destination
        - "path_prefix": prefix the filename with removed folder names
        - "increment": add _1, _2, and so on

    remove_empty_dirs
        Remove empty directories after moving files.

    Returns
    -------
    list[tuple[str, str]]
        Old and new file URLs.
    """
    root_dir = Path(root_dir).expanduser().resolve()

    if not root_dir.is_dir():
        raise NotADirectoryError(
            f"Root directory does not exist: {root_dir}"
        )

    if keep_levels < 0:
        raise ValueError("`keep_levels` cannot be negative.")

    valid_collisions = {
        "raise",
        "skip",
        "overwrite",
        "path_prefix",
        "increment",
    }

    if collision not in valid_collisions:
        raise ValueError(
            f"`collision` must be one of {sorted(valid_collisions)}."
        )

    # Collect the files before moving anything. This prevents newly moved
    # files from being discovered again during the same operation.
    all_files = sorted(
        path
        for path in root_dir.rglob(pattern)
        if path.is_file()
    )

    moved_urls: list[tuple[str, str]] = []

    for source in all_files:
        relative_path = source.relative_to(root_dir)
        directory_parts = relative_path.parent.parts

        # The file is already at or above the requested depth.
        if len(directory_parts) <= keep_levels:
            continue

        kept_parts = directory_parts[:keep_levels]
        removed_parts = directory_parts[keep_levels:]

        destination_dir = root_dir.joinpath(*kept_parts)
        destination = destination_dir / source.name

        if destination == source:
            continue

        # Resolve duplicate filenames.
        if destination.exists():
            if collision == "raise":
                raise FileExistsError(
                    f"Destination already exists: {destination}"
                )

            if collision == "skip":
                print(
                    f"SKIP: {source.relative_to(root_dir)} "
                    f"because {destination.relative_to(root_dir)} exists"
                )
                continue

            if collision == "overwrite":
                if not dry_run:
                    destination.unlink()

            elif collision == "path_prefix":
                # Example:
                # root/2010/01/15/file.nc
                # -> root/2010/01/15_file.nc
                prefix = "_".join(removed_parts)

                destination = destination_dir / (
                    f"{prefix}_{source.name}"
                )

                destination = _make_unique_path(destination)

            elif collision == "increment":
                destination = _make_unique_path(destination)

        old_url = source.as_uri()
        new_url = destination.as_uri()

        print(
            f"{'PLAN' if dry_run else 'MOVE'}: "
            f"{source.relative_to(root_dir)} "
            f"-> {destination.relative_to(root_dir)}"
        )

        if not dry_run:
            destination_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.move(
                str(source),
                str(destination),
            )

        moved_urls.append(
            (old_url, new_url)
        )

    if remove_empty_dirs and not dry_run:
        _remove_empty_directories(root_dir)

    print(
        f"\n{'Planned' if dry_run else 'Completed'} "
        f"{len(moved_urls)} file moves."
    )

    return moved_urls


def _make_unique_path(path: Path) -> Path:
    """
    Return a non-existing path by adding an incrementing suffix.

    Example
    -------
    file.nc
    file_1.nc
    file_2.nc
    """
    if not path.exists():
        return path

    counter = 1

    while True:
        candidate = path.with_name(
            f"{path.stem}_{counter}{path.suffix}"
        )

        if not candidate.exists():
            return candidate

        counter += 1


def _remove_empty_directories(root_dir: Path) -> None:
    """
    Remove empty directories from deepest to shallowest.
    """
    directories = sorted(
        (
            path
            for path in root_dir.rglob("*")
            if path.is_dir()
        ),
        key=lambda path: len(path.parts),
        reverse=True,
    )

    for directory in directories:
        try:
            directory.rmdir()
            print(
                f"REMOVED EMPTY DIRECTORY: "
                f"{directory.relative_to(root_dir)}"
            )
        except OSError:
            # Directory is not empty.
            pass


from pathlib import Path

import numpy as np
import xarray as xr
############################################################################
## This is to expert an Xvec vector cube to Zarr using WKB geometry encoding.
#############################################################################

def export_xvec_wkb_zarr(
    vector_cube: xr.Dataset | xr.DataArray,
    output_path: str | Path,
    *,
    time_chunk: int = 30,
    zone_chunk: int | None = None,
    consolidated: bool = True,
    overwrite: bool = True,
) -> Path:
    """
    Export an Xvec vector cube to Zarr using WKB geometry encoding.

    Parameters
    ----------
    vector_cube
        Xarray Dataset or DataArray containing one or more
        Shapely geometry coordinates or variables.

    output_path
        Destination Zarr directory.

    time_chunk
        Number of time steps per Zarr chunk.

    zone_chunk
        Number of geometries per chunk. If None, all zones are
        placed in one chunk.

    consolidated
        Write consolidated Zarr metadata.

    overwrite
        Replace an existing Zarr store.

    Returns
    -------
    Path
        Path to the created Zarr store.
    """
    output_path = Path(
        output_path
    ).expanduser().resolve()

    if isinstance(vector_cube, xr.DataArray):
        cube = vector_cube.to_dataset(
            name=vector_cube.name or "value"
        )

    elif isinstance(vector_cube, xr.Dataset):
        cube = vector_cube.copy()

    else:
        raise TypeError(
            "`vector_cube` must be an Xarray Dataset or DataArray."
        )

    # Convert descriptive object coordinates to strings
    for coordinate_name in [
        "city_name",
        "zone_cat",
    ]:
        if coordinate_name in cube.coords:
            coordinate = cube[coordinate_name]

            cube = cube.assign_coords(
                {
                    coordinate_name: (
                        coordinate.dims,
                        np.asarray(
                            coordinate.values,
                            dtype=str,
                        ),
                    )
                }
            )

    # Encode all Shapely geometry arrays as WKB
    encoded = cube.xvec.encode_wkb()

    chunks = {}

    if "time" in encoded.dims:
        chunks["time"] = min(
            time_chunk,
            encoded.sizes["time"],
        )

    if "zone" in encoded.dims:
        if zone_chunk is None:
            chunks["zone"] = encoded.sizes["zone"]
        else:
            chunks["zone"] = min(
                zone_chunk,
                encoded.sizes["zone"],
            )

    if chunks:
        encoded = encoded.chunk(chunks)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    mode = "w" if overwrite else "w-"

    encoded.to_zarr(
        output_path,
        mode=mode,
        consolidated=consolidated,
    )

    print(f"Zarr store: {output_path}")
    print(f"Dimensions: {dict(encoded.sizes)}")
    print(f"Chunks: {chunks}")

    return output_path

############################################################################
## This is to read an Xvec vector cube from Zarr using WKB geometry decoding.
#############################################################################

def open_xvec_wkb_zarr(
    zarr_path: str | Path,
    *,
    consolidated: bool = True,
    chunks="auto",
) -> xr.Dataset:
    """
    Open a WKB-encoded Xvec Zarr store and restore geometries.
    """
    zarr_path = Path(
        zarr_path
    ).expanduser().resolve()

    if not zarr_path.exists():
        raise FileNotFoundError(
            f"Zarr store not found: {zarr_path}"
        )

    encoded = xr.open_zarr(
        zarr_path,
        consolidated=consolidated,
        chunks=chunks,
    )

    decoded = encoded.xvec.decode_wkb()

    return decoded