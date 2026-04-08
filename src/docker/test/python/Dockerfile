FROM seedsyncarr/run/python/devenv AS seedsyncarr_test_python

RUN ls -l /app/python

# Install dependencies
# Note: The base image (seedsyncarr_run_python_env) already has non-free repos enabled via DEB822 format
RUN apt-get update && \
    apt-get install -y \
        openssh-server \
        rar \
        unrar

ADD src/docker/test/python/entrypoint.sh /app/

# setup sshd
RUN mkdir -p /var/run/sshd
RUN ssh-keygen -t rsa -N "" -f /root/.ssh/id_rsa && \
    cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys
# Test-only: disable host key checking for ephemeral test container connecting to localhost sshd
RUN echo "StrictHostKeyChecking no\nUserKnownHostsFile /dev/null\nLogLevel=quiet" > /root/.ssh/config
# Enable password authentication in sshd (required for OpenSSH 9.x in Debian Bookworm)
# Also enable keyboard-interactive for compatibility
RUN echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config && \
    echo "KbdInteractiveAuthentication yes" >> /etc/ssh/sshd_config && \
    echo "UsePAM yes" >> /etc/ssh/sshd_config

# create the seedsyncarrtest user, add root's public key to seedsyncarrtest
RUN useradd --create-home -s /bin/bash seedsyncarrtest && \
    echo "seedsyncarrtest:seedsyncarrpass" | chpasswd
RUN usermod -a -G root seedsyncarrtest
RUN cp /root/.ssh/id_rsa.pub /home/seedsyncarrtest/ && \
    chown seedsyncarrtest:seedsyncarrtest /home/seedsyncarrtest/id_rsa.pub
USER seedsyncarrtest
RUN  mkdir -p /home/seedsyncarrtest/.ssh && \
    cat /home/seedsyncarrtest/id_rsa.pub >> /home/seedsyncarrtest/.ssh/authorized_keys
USER root

EXPOSE 22

# src needs to be mounted on /src/
WORKDIR /src/
ENV PYTHONPATH=/src

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["pytest", "-v"]
