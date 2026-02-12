FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    snort \
    hydra \
    smbclient \
    sshpass \
    openssh-client \
    gcc \
    libc6-dev \
    python3 \
    python3-pip \
    python-is-python3 \
    curl \
    iptables \
    iproute2 \
    iputils-ping \
    net-tools \
    tcpdump \
    nmap \
    netcat-openbsd \
    telnet \
    wget \
    ftp \
    dnsutils \
    traceroute \
    procps \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir impacket

COPY snort.conf /etc/snort/snort.conf
COPY local.rules /etc/snort/rules/local.rules
COPY samba_exploit.py /test_fixtures/samba_exploit.py
COPY artifacts/ /opt/artifacts/
RUN chmod +x /opt/artifacts/plant_artifacts.sh /opt/artifacts/plant_static.sh && \
    bash /opt/artifacts/plant_static.sh

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
