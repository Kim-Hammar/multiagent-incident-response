FROM debian:bullseye-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    samba \
    rsync \
    cron \
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
    postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/bin/python

# Create shared and backup directories
RUN mkdir -p /srv/shared /srv/backups

COPY smb.conf /etc/samba/smb.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 445 139

ENTRYPOINT ["/entrypoint.sh"]
