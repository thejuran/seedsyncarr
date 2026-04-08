# ============================================================================
# Angular Build Stages
# ============================================================================

# Creates environment for angular
# Note: Using Node 20 LTS with Angular 13.x and Dart Sass
# --legacy-peer-deps required for peer dependency conflicts
FROM node:22-slim AS seedsyncarr_build_angular_env
COPY src/angular/package*.json /app/
WORKDIR /app
# Ensure NODE_ENV is not production so devDependencies (including @angular/cli) are installed
ENV NODE_ENV=development
# Install all dependencies including devDependencies
# Note: Angular 13+ CLI binary is ng.js, not ng
RUN npm install --include=dev --legacy-peer-deps && \
    test -f node_modules/@angular/cli/bin/ng.js || (echo "ERROR: @angular/cli not installed" && exit 1)

# Builds angular app into html
# Output is in /build/dist/browser/
FROM seedsyncarr_build_angular_env AS seedsyncarr_build_angular
COPY src/angular /app
WORKDIR /app
RUN mkdir -p /build
# Verify node_modules exists, reinstall if missing (handles Docker cache issues)
RUN if [ ! -f node_modules/@angular/cli/bin/ng.js ]; then npm install --legacy-peer-deps; fi
# Use --configuration=production with the application builder (esbuild)
# Note: Angular 21 application builder outputs to browser/ subdirectory
RUN node node_modules/@angular/cli/bin/ng.js build --configuration=production --output-path /build/dist/

# ============================================================================
# Scanfs Build Stages
# ============================================================================

# Creates environment to build python binaries
# Using Debian 11 (bullseye) with GLIBC 2.31 for compatibility with older systems
# Ubuntu 22.04 uses GLIBC 2.35 which causes runtime errors on older distros
FROM python:3.11-slim-bullseye AS seedsyncarr_build_pyinstaller_env
# Install build dependencies
RUN apt-get update && apt-get install -y \
    binutils \
    build-essential \
    libffi-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*
# Install Poetry
RUN pip3 install poetry && \
    poetry config virtualenvs.create false
COPY src/python/pyproject.toml /app/python/
COPY src/python/poetry.lock /app/python/
WORKDIR /python
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
RUN cd /app/python && poetry install

# Builds scanfs with pyinstaller
# Output is in /build/dist/
FROM seedsyncarr_build_pyinstaller_env AS seedsyncarr_build_scanfs
COPY src/python /python
RUN mkdir -p /build
RUN	pyinstaller /python/scan_fs.py \
    -y \
    --onefile \
    -p /python \
    --distpath /build/dist \
    --workpath /build/work \
    --specpath /build \
    --name scanfs

# ============================================================================
# Python Runtime Environment
# ============================================================================

# Creates environment to run Seedsync python code
# Installs all python dependencies
FROM python:3.11-slim AS seedsyncarr_run_python_env

# Install dependencies
# Debian 12 (Bookworm) uses DEB822 format in /etc/apt/sources.list.d/debian.sources
RUN sed -i 's/Components: main/Components: main contrib non-free non-free-firmware/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y \
        build-essential \
        libssl-dev \
        lftp \
        openssh-client \
        p7zip \
        p7zip-full \
        unrar \
        bzip2 \
        curl \
        libnss-wrapper \
        libxml2-dev libxslt-dev libffi-dev \
    && apt-get clean

# Install Poetry using pip (more reliable than installer script in CI)
RUN pip3 install poetry && \
    poetry config virtualenvs.create false

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Install Python dependencies
RUN mkdir -p /app
COPY src/python/pyproject.toml /app/python/
COPY src/python/poetry.lock /app/python/
RUN cd /app/python && poetry install --only main


# Creates environment for Python dev
FROM seedsyncarr_run_python_env AS seedsyncarr_run_python_devenv
RUN cd /app/python && poetry install


# Installs Seedsync python code
FROM seedsyncarr_run_python_env AS seedsyncarr_run_python
RUN mkdir -p /app
COPY src/python /app/python


# Full Seedsync docker image
FROM seedsyncarr_run_python AS seedsyncarr_run
LABEL org.opencontainers.image.source="https://github.com/thejuran/seedsyncarr"
COPY --from=seedsyncarr_build_angular /build/dist/browser /app/html
COPY --from=seedsyncarr_build_scanfs /build/dist/scanfs /app/scanfs
COPY src/docker/build/docker-image/setup_default_config.sh /scripts/

# Accept new host keys on first connection; reject changed keys to prevent MITM
RUN mkdir -p /root/.ssh && echo "StrictHostKeyChecking accept-new" > /root/.ssh/config

# SSH as any user fix
# https://stackoverflow.com/a/57531352
COPY src/docker/build/docker-image/run_as_user /usr/local/bin/
RUN chmod a+x /usr/local/bin/run_as_user
COPY src/docker/build/docker-image/ssh /usr/local/sbin
RUN chmod a+x /usr/local/sbin/ssh
COPY src/docker/build/docker-image/scp /usr/local/sbin
RUN chmod a+x /usr/local/sbin/scp


# Create non-root user and directories under that user
RUN groupadd -g 1000 seedsyncarr && \
    useradd -r -u 1000 -g seedsyncarr seedsyncarr
RUN mkdir /config && \
    mkdir /downloads && \
    chown seedsyncarr:seedsyncarr /config && \
    chown seedsyncarr:seedsyncarr /downloads

# Switch to non-root user
USER seedsyncarr

# First time config setup and replacement
RUN /scripts/setup_default_config.sh

# Must run app inside shell
# Otherwise the container crashes as soon as a child process exits
CMD [ \
    "python", \
    "/app/python/seedsyncarr.py", \
    "-c", "/config", \
    "--html", "/app/html", \
    "--scanfs", "/app/scanfs" \
]

EXPOSE 8800
