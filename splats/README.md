Requirements:
- A computer with an Nvidia 5090 GPU and CUDA 12.
- Docker installed

How to run the `splats` api on your computer:

1. Clone the repo by running: `git clone git@github.com:jacobbaehr/scantrix.git`
2. Create a directory to store splats by running: `mkdir ~/splat_storage`
2. Build the docker container by running: `sudo docker build -t splats --build-arg CUDA_ARCHITECTURES=89 .`
3. Run the docker container by running: `sudo docker run --gpus all --network host -it --rm --runtime=nvidia --env NVIDIA_VISIBLE_DEVICES=all --env NVIDIA_DRIVER_CAPABILITIES=all -v /etc/OpenCL/vendors:/etc/OpenCL/vendors:ro -p 8000:8000 -e SPLAT_STORAGE_DIR=/data/outside -v ~/splat_storage:/data/outside splats`
4. Go to localhost:8000/docs to access the Swagger docs.
5. Upload a video or zip file of images to start processing.
6. Access the generated splat in the specified splat storage directory.
