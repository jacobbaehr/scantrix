ARG CUDA_ARCHITECTURES=native

# -------------------------------------
# Stage 1: Build COLMAP from source
# -------------------------------------
FROM nvidia/cuda:12.6.1-devel-ubuntu22.04 as colmap-builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    git cmake ninja-build build-essential \
    libboost-program-options-dev libboost-graph-dev libboost-system-dev \
    libeigen3-dev libflann-dev libfreeimage-dev libmetis-dev \
    libgoogle-glog-dev libgtest-dev libgmock-dev libsqlite3-dev \
    libglew-dev qtbase5-dev libqt5opengl5-dev libcgal-dev \
    libceres-dev libcurl4-openssl-dev

RUN git clone https://github.com/colmap/colmap.git
RUN cd colmap && \
    git fetch https://github.com/colmap/colmap.git ${COLMAP_GIT_COMMIT} && \
    git checkout FETCH_HEAD && \
    mkdir build && \
    cd build && \
    cmake .. -GNinja -DCMAKE_CUDA_ARCHITECTURES=${CUDA_ARCHITECTURES} \
        -DCMAKE_INSTALL_PREFIX=/colmap-install && \
    ninja install

# -------------------------------------
# Stage 2: Build Brush with Rust
# -------------------------------------
FROM rust:1.86 as brush-builder

RUN git clone https://github.com/ArthurBrussee/brush
RUN cargo build --release --manifest-path ./brush/Cargo.toml

# -------------------------------------
# Stage 3: Final Runtime Image
# -------------------------------------
FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH=/opt/conda/bin:$PATH

# Allow the host to bind-mount a directory here (default: /data/outside)
ENV SPLAT_STORAGE_DIR=/data/outside

# Create the directory and declare it as a volume
RUN mkdir -p ${SPLAT_STORAGE_DIR}
VOLUME ["${SPLAT_STORAGE_DIR}"]

# System & Python + ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget git curl ffmpeg \
    build-essential gcc-11 g++-11 \
    libgl1-mesa-dev libglib2.0-0 \
    libboost-program-options1.74.0 libc6 libceres2 libfreeimage3 \
    libgcc-s1 libgl1 libglew2.2 libgoogle-glog0v5 libqt5core5a \
    libqt5gui5 libqt5widgets5 libcurl4 \
    libvulkan1 vulkan-tools mesa-vulkan-drivers \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy COLMAP
COPY --from=colmap-builder /colmap-install/ /usr/local/

# Copy Brush binary
RUN mkdir /opt/brush
COPY --from=brush-builder /brush/target/release/brush_app /opt/brush/
ENV PATH=/opt/brush:$PATH

# Install Conda
RUN curl -o ~/miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-py311_25.1.1-2-Linux-x86_64.sh && \
    bash ~/miniconda.sh -b -p /opt/conda && rm ~/miniconda.sh

# Set up environment
COPY environment-dev.yml /tmp/environment-dev.yml
COPY entrypoint.sh /entrypoint.sh
RUN /opt/conda/bin/conda env create -f /tmp/environment-dev.yml && /opt/conda/bin/conda clean -a -y
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

WORKDIR /workspace
COPY . .

EXPOSE 8000

# Default: Start FastAPI app
CMD ["uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", "8000"]
