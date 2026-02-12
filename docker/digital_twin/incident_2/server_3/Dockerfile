FROM debian:bullseye-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    iptables \
    iproute2 \
    iputils-ping \
    net-tools \
    procps \
    curl \
    openssh-client \
    netcat-openbsd \
    nmap \
    telnet \
    wget \
    ftp \
    dnsutils \
    tcpdump \
    traceroute \
    python3 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/bin/python

# Configure SSH: key-based only, no password auth
RUN mkdir -p /run/sshd && \
    sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config && \
    sed -i 's/^#*PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/^#*PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config

# Create jump user with SSH key pair
RUN useradd -m -s /bin/bash jump && \
    mkdir -p /home/jump/.ssh && \
    ssh-keygen -t ed25519 -f /home/jump/.ssh/id_ed25519 -N "" -q && \
    cp /home/jump/.ssh/id_ed25519.pub /home/jump/.ssh/authorized_keys && \
    chown -R jump:jump /home/jump/.ssh && \
    chmod 700 /home/jump/.ssh && \
    chmod 600 /home/jump/.ssh/authorized_keys

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22

ENTRYPOINT ["/entrypoint.sh"]
