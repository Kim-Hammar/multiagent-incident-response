FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    ncat \
    hydra \
    smbclient \
    sshpass \
    openssh-client \
    curl \
    wget \
    python3 \
    python3-pip \
    python3-venv \
    gcc \
    libc6-dev \
    postgresql-client \
    ftp \
    dnsutils \
    tcpdump \
    iproute2 \
    iputils-ping \
    net-tools \
    netcat-openbsd \
    telnet \
    traceroute \
    procps \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir impacket
ENV PATH="/opt/venv/bin:$PATH"

CMD ["sleep", "infinity"]
