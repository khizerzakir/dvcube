## VirtualiZarr - Kerchunks

Kerchunk does not convert `nc` files to zarr but actually writes a lightweight reference file to let xarray read `nc` files as if they were zarr files. 

We have the test dataset here that we will use to build the pipeline and then scale it. 

We first create the kerchunk reference file from the nc files and then open them using xarray -> subset -> xvec


## Kerchunks

- We made single and then MultiZarr kerchunk reference jsons.
- Loaded multizarr jsons to load all the nc files

- Corrected or `sortby` `lat` `lon` to help us find the corrected coords for our `ds`.

- Then we created our vector data cube using `xvec` and then plot it. 


## Next Steps 

- Create Monthly plots
- Apply this pipeline on all the other data - ECVs.