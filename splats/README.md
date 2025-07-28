Requirements:
- A computer with an Nvidia 5090 GPU and CUDA 12.
- Docker installed

How to run the `splats` api on your computer:

1. Clone the repo by running: `git clone git@github.com:conjjure/scantrix-public.git`
2. Create a directory to store splats by running: `mkdir ~/splat_storage`
2. Build the docker container by running: `sudo docker build -t splats --build-arg CUDA_ARCHITECTURES=89 .`
3. Run the docker container by running: `sudo docker run --gpus all --network host -it --rm --runtime=nvidia --env NVIDIA_VISIBLE_DEVICES=all --env NVIDIA_DRIVER_CAPABILITIES=all -v /etc/OpenCL/vendors:/etc/OpenCL/vendors:ro -p 8000:8000 -e SPLAT_STORAGE_DIR=/data/outside -v ~/splat_storage:/data/outside splats`

How to follow on-going logs from a running container:

1. Run `sudo docker ps` to see running containers. Grab the container id.
2. Run `sudo docker logs <container id> -f` to follow on-going logs.