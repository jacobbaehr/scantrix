How to run the splats api on the server:

1. ssh into the server
2. clone the latest from the repo
3. build the docker container by running: `sudo docker build -t splats --build-arg CUDA_ARCHITECTURES=89 .`
4. run the docker container by running: `sudo docker run --gpus all --network host -it --rm --runtime=nvidia --env NVIDIA_VISIBLE_DEVICES=all --env NVIDIA_DRIVER_CAPABILITIES=all -v /etc/OpenCL/vendors:/etc/OpenCL/vendors:ro -p 8000:8000 -e SPLAT_STORAGE_DIR=/data/outside -v ~/splat_storage:/data/outside splats`

How to follow on-going logs from a running container:

1. ssh into the server
2. Run `sudo docker ps` to see running containers. There should only be one for now. Grab the container id.
3. Run `sudo docker logs <container id> -f` to follow on-going logs.