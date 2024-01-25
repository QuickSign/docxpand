# Build the docker container
* With GPU
If you have a compatible GPU available on your server, build the docker image for Stable Diffusion like this :
```
docker build -t stable_diffusion .
```

Skipping the CUDA test is only done because GPUs are not available during build.

* Without GPU (not recommended)
If you only have CPU available on your server, build it like this :
```
export EXTRA_COMMANDLINE_ARGS="--precision full --no-half"
docker build -t stable_diffusion .
```

# Run the docker container
* With GPU
```
docker run --gpus all --privileged --rm -it --network host stable_diffusion
```

We have tested the inference using a NVidia GTX Titan X (12 GB) card, with NVidia driver version 510.108.03 and CUDA version 11.6. Please refer to https://github.com/AUTOMATIC1111/stable-diffusion-webui documentation in case of difficulty.

* Without GPU (not recommended)
```
docker run --rm -it --network host stable_diffusion
```
