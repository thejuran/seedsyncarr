# Derived from src/docker/test/e2e/remote/Dockerfile (Phase 78 UAT, disposable).
# D-01: password-only, credentials scoped to localhost container — teardown after UAT.
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    openssh-server \
    coreutils \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home -s /bin/bash seeduser && \
    echo "seeduser:seedpass" | chpasswd && \
    mkdir -p /data && chown seeduser:seeduser /data && chmod 0755 /data

RUN sed -i '/Port 22/c\Port 1234' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    mkdir -p /var/run/sshd

EXPOSE 1234
CMD ["/usr/sbin/sshd", "-D", "-e"]
