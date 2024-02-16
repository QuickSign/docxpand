FROM python:3.10-bullseye
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6
RUN mkdir /work
WORKDIR /work
RUN git clone -b v1.5.0 https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
WORKDIR /work/stable-diffusion-webui 
ARG EXTRA_COMMANDLINE_ARGS
ENV COMMANDLINE_ARGS="--skip-torch-cuda-test ${EXTRA_COMMANDLINE_ARGS}"
RUN pip install httpx==0.24.1
RUN python -c 'import launch; launch.prepare_environment()'
RUN python -c 'import webui; webui.initialize();'
CMD ["python", "/work/stable-diffusion-webui/launch.py", "--api", "--listen"]
