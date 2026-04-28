FROM ubuntu:22.04

# Install dependencies
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    python3 \
    openssh-server

# Switch to Python 3 (3.10 is default in Ubuntu 22.04)
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1
RUN update-alternatives --set python /usr/bin/python3

# Create non-root user (no password set -- DOCKSEC-02)
RUN useradd --create-home -s /bin/bash remoteuser

# DOCKSEC-05: Accept ephemeral SSH public key via build argument.
# This is a test-only public key for an ephemeral container — visible in
# docker history is acceptable (no secret material).
ARG SSH_PUBKEY
RUN test -n "${SSH_PUBKEY}" || { echo "ERROR: SSH_PUBKEY build-arg is required. Build via 'make run-tests-e2e', not 'docker compose build'." >&2; exit 1; }
RUN mkdir -p /home/remoteuser/.ssh && \
    echo "${SSH_PUBKEY}" >> /home/remoteuser/.ssh/authorized_keys && \
    chown -R remoteuser:remoteuser /home/remoteuser/.ssh && \
    chmod 700 /home/remoteuser/.ssh && \
    chmod 600 /home/remoteuser/.ssh/authorized_keys

# Copy over data
ADD --chown=remoteuser:remoteuser src/docker/test/e2e/remote/files /home/remoteuser/files

# Change sshd port to 1234
RUN sed -i '/Port 22/c\Port 1234' /etc/ssh/sshd_config
EXPOSE 1234

# DOCKSEC-02: Disable password authentication
RUN sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?KbdInteractiveAuthentication.*/KbdInteractiveAuthentication no/' /etc/ssh/sshd_config && \
    (grep -qE '^#?UsePAM' /etc/ssh/sshd_config && sed -i 's/^#\?UsePAM.*/UsePAM no/' /etc/ssh/sshd_config || echo "UsePAM no" >> /etc/ssh/sshd_config)
# DOCKSEC-02: Disable password login without locking the account.
# '*' is an invalid hash (no password matches) but unlike '!' it does not
# trigger OpenSSH 10's "account is locked" check that blocks key auth.
RUN usermod -p '*' remoteuser

# DOCKSEC-04: Generate host keys and transfer ownership for non-root sshd
RUN mkdir -p /var/run/sshd && \
    ssh-keygen -A && \
    chown remoteuser:remoteuser /etc/ssh/ssh_host_* && \
    chmod 600 /etc/ssh/ssh_host_*_key && \
    chmod 644 /etc/ssh/ssh_host_*_key.pub && \
    chown remoteuser:remoteuser /var/run/sshd

# Non-root sshd needs writable PidFile location
RUN echo "PidFile /tmp/sshd.pid" >> /etc/ssh/sshd_config

# DOCKSEC-04: Switch to non-root user (port 1234 is non-privileged -- no setcap needed)
USER remoteuser

CMD ["/usr/sbin/sshd", "-D", "-e"]
