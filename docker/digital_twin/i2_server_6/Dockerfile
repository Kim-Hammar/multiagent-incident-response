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
    && rm -rf /var/lib/apt/lists/*

# Create shared and backup directories
RUN mkdir -p /srv/shared /srv/backups

COPY smb.conf /etc/samba/smb.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 445 139

ENTRYPOINT ["/entrypoint.sh"]
