FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    suricata \
    iptables \
    iproute2 \
    iputils-ping \
    net-tools \
    curl \
    procps \
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
    python-is-python3 \
    && rm -rf /var/lib/apt/lists/*

COPY iptables-rules.sh /iptables-rules.sh
COPY artifacts/ /opt/artifacts/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /iptables-rules.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
