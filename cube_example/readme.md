## VirtualiZarr - Kerchunks

Kerchunk does not convert `nc` files to zarr but actually writes a lightweight reference file to let xarray read `nc` files as if they were zarr files. 

We have the test dataset here that we will use to build the pipeline and then scale it. 

We first create the kerchunk reference file from the nc files and then open them using xarray -> subset -> xvec


## Kerchunks

- We made single and then MultiZarr kerchunk reference jsons.
- Loaded multizarr jsons to load all the nc files

- Corrected or `sortby` `lat` `lon` to help us find the corrected coords for our `ds`.

- Then we created our vector data cube using `xvec` and then plot it. 

## Read - Check - Plot

using the `read_check.py` we are trying to get an overview of the data before we do further processing. It is a useful tool to get the overview of the data[variables, cordinates. extent, time...]

- `check` function simply checks all the available nc files or a nc file, if exists. 
- `read` function reads and loads the metadata to give the basic overview of the dataset
- `plot` function is key here as it uses the proper cordinate extent of the data to print a visibly nice and readable map.

USAGE:
```
python cube_example/read_check.py /path/to/netcdf_or_directory [optional_file_name] [optional_save_path]
```

within a notebook:

```
%run /home/kzakir/dvcube/test/cube_example/read_check.py
```
CLI:

```
cd - to the dir and then
{dir}/read_check.py
```

## Integrating xvec library

- After the kerchunks data becomes easy to subset and access via xarray. 

- We use xvec library to get the zonal stats for the units that we have. 
## Next Steps 

- Create Monthly plots
- Apply this pipeline on all the other data - ECVs.

