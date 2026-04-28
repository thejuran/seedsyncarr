FROM seedsyncarr/run/python/devenv AS seedsyncarr_test_python

RUN ls -l /app/python

# Install dependencies
# Note: The base image (seedsyncarr_run_python_env) already has non-free repos enabled via DEB822 format
# ARM64: skip `rar` (Debian ships rar for amd64/i386 only; RARLAB has no aarch64 Linux build)
# AMD64: install `rar` normally for test-fixture archive creation
RUN apt-get update && \
    apt-get install -y openssh-server unrar && \
    ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ] || [ "$ARCH" = "i386" ]; then \
        apt-get install -y rar; \
    else \
        echo "Skipping rar install on $ARCH (Debian rar is amd64/i386 only)"; \
    fi

ADD src/docker/test/python/entrypoint.sh /app/

# setup sshd
RUN mkdir -p /var/run/sshd
RUN ssh-keygen -t rsa -N "" -f /root/.ssh/id_rsa && \
    cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys
# DOCKSEC-06: accept-new + /dev/null = no host-key verification (keys never persist). Test-only.
RUN printf "StrictHostKeyChecking accept-new\nUserKnownHostsFile /dev/null\nLogLevel=quiet\n" > /root/.ssh/config
# DOCKSEC-03: Disable password authentication — key-only auth
RUN sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && \
    sed -i 's/^#\?KbdInteractiveAuthentication.*/KbdInteractiveAuthentication no/' /etc/ssh/sshd_config && \
    (grep -qE '^#?UsePAM' /etc/ssh/sshd_config && sed -i 's/^#\?UsePAM.*/UsePAM no/' /etc/ssh/sshd_config || echo "UsePAM no" >> /etc/ssh/sshd_config)

# create the seedsyncarrtest user, add root's public key to seedsyncarrtest
# DOCKSEC-03: no chpasswd — password auth is disabled and account is locked below
RUN useradd --create-home -s /bin/bash seedsyncarrtest
# DOCKSEC-01: Dedicated group instead of root group
RUN groupadd testgroup && \
    usermod -a -G testgroup seedsyncarrtest && \
    usermod -a -G testgroup root
# DOCKSEC-03: Disable password login without locking the account.
# '*' is an invalid hash (no password matches) but unlike '!' it does not
# trigger OpenSSH 10's "account is locked" check that blocks key auth.
RUN usermod -p '*' seedsyncarrtest
RUN cp /root/.ssh/id_rsa.pub /home/seedsyncarrtest/ && \
    chown seedsyncarrtest:seedsyncarrtest /home/seedsyncarrtest/id_rsa.pub
USER seedsyncarrtest
RUN  mkdir -p /home/seedsyncarrtest/.ssh && \
    cat /home/seedsyncarrtest/id_rsa.pub >> /home/seedsyncarrtest/.ssh/authorized_keys && \
    chmod 700 /home/seedsyncarrtest/.ssh && \
    chmod 600 /home/seedsyncarrtest/.ssh/authorized_keys
USER root


EXPOSE 22

# src needs to be mounted on /src/
WORKDIR /src/
ENV PYTHONPATH=/src
ENV PYTHONWARNINGS="ignore::DeprecationWarning:cgi"

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["pytest", "-v", "-p", "no:cacheprovider"]
