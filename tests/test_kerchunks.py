import unittest
from pathlib import Path

import numpy as np
import xarray as xr

from cube_example.kerchunks import combine_single_refs, make_single_ref

class KerchunkWorkflowTests(unittest.TestCase):
    def test_single_to_multi_refs_work(self) -> None:
        data_dir = Path("/tmp/kerchunk_test_data")
        if data_dir.exists():
            for path in sorted(data_dir.rglob("*"), reverse=True):
                if path.is_file() or path.is_symlink():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
        data_dir.mkdir(parents=True, exist_ok=True)

        ds = xr.Dataset(
            {"foo": (("time", "lat", "lon"), np.arange(6).reshape(2, 1, 3))},
            coords={"time": [0, 1], "lat": [1.0], "lon": [2.0, 3.0, 4.0]},
        )
        ds.isel(time=slice(0, 1)).to_netcdf(data_dir / "a.nc")
        ds.isel(time=slice(1, 2)).to_netcdf(data_dir / "b.nc")

        single_dir = data_dir / "single"
        single_dir.mkdir(parents=True, exist_ok=True)

        json_a = make_single_ref(data_dir / "a.nc", single_dir, data_dir)
        json_b = make_single_ref(data_dir / "b.nc", single_dir, data_dir)

        self.assertTrue(json_a.exists())
        self.assertTrue(json_b.exists())

        multi_dir = data_dir / "multi"
        multi_dir.mkdir(parents=True, exist_ok=True)
        combine_single_refs(single_dir, multi_dir)

        combined_json = multi_dir / "combined_refs.json"
        self.assertTrue(combined_json.exists())


if __name__ == "__main__":
    unittest.main()
