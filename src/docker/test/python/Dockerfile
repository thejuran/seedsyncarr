FROM seedsyncarr/run/python/devenv AS seedsyncarr_test_python

RUN ls -l /app/python

# Install dependencies
# Note: The base image (seedsyncarr_run_python_env) already has non-free repos enabled via DEB822 format
# ARM64: skip `rar` (Debian ships rar for amd64/i386 only; RARLAB has no aarch64 Linux build)
# AMD64: install `rar` normally for test-fixture archive creation
RUN apt-get update && \
    apt-get install -y openssh-server unrar libcap2-bin gosu && \
    ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ] || [ "$ARCH" = "i386" ]; then \
        apt-get install -y rar; \
    else \
        echo "Skipping rar install on $ARCH (Debian rar is amd64/i386 only)"; \
    fi

# DOCKSEC-04: Create dedicated non-root sshd runner
RUN useradd -r -s /usr/sbin/nologin -d /nonexistent sshdaemon

ADD src/docker/test/python/entrypoint.sh /app/

# setup sshd
RUN mkdir -p /var/run/sshd
RUN ssh-keygen -t rsa -N "" -f /root/.ssh/id_rsa && \
    cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys
# DOCKSEC-06: accept-new rejects changed keys (MITM protection) while accepting new ones
RUN printf "StrictHostKeyChecking accept-new\nUserKnownHostsFile /dev/null\nLogLevel=quiet\n" > /root/.ssh/config
# DOCKSEC-03: Disable password authentication — key-only auth
RUN sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?KbdInteractiveAuthentication.*/KbdInteractiveAuthentication no/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?UsePAM.*/UsePAM no/' /etc/ssh/sshd_config

# create the seedsyncarrtest user, add root's public key to seedsyncarrtest
RUN useradd --create-home -s /bin/bash seedsyncarrtest && \
    echo "seedsyncarrtest:seedsyncarrpass" | chpasswd
# DOCKSEC-01: Dedicated group instead of root group
RUN groupadd testgroup && \
    usermod -a -G testgroup seedsyncarrtest && \
    usermod -a -G testgroup root
# DOCKSEC-03: Lock the user password to prevent any password-based login
RUN passwd -l seedsyncarrtest
RUN cp /root/.ssh/id_rsa.pub /home/seedsyncarrtest/ && \
    chown seedsyncarrtest:seedsyncarrtest /home/seedsyncarrtest/id_rsa.pub
USER seedsyncarrtest
RUN  mkdir -p /home/seedsyncarrtest/.ssh && \
    cat /home/seedsyncarrtest/id_rsa.pub >> /home/seedsyncarrtest/.ssh/authorized_keys
USER root

# DOCKSEC-04: Allow non-root sshd to bind port 22
RUN setcap cap_net_bind_service=+ep /usr/sbin/sshd

# DOCKSEC-04: Transfer sshd runtime ownership to sshdaemon
RUN chown sshdaemon /var/run/sshd && \
    chown sshdaemon:sshdaemon /etc/ssh/ssh_host_* && \
    chmod 700 /etc/ssh/ssh_host_*

EXPOSE 22

# src needs to be mounted on /src/
WORKDIR /src/
ENV PYTHONPATH=/src
ENV PYTHONWARNINGS="ignore::DeprecationWarning:cgi"

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["pytest", "-v", "-p", "no:cacheprovider"]
