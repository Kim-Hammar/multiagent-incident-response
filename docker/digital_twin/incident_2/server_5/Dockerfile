FROM debian:bullseye-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    dnsmasq \
    openssh-server \
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
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/bin/python

RUN mkdir -p /run/sshd

COPY dnsmasq.conf /etc/dnsmasq.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 53 22

ENTRYPOINT ["/entrypoint.sh"]
