FROM debian:bullseye-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    vsftpd \
    cron \
    rsyslog \
    curl \
    iptables \
    iproute2 \
    iputils-ping \
    net-tools \
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
    git \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/bin/python

# Create FTP user
RUN useradd -m -s /bin/bash ftpuser && \
    echo "ftpuser:ftppass" | chpasswd

# Create backup directory
RUN mkdir -p /srv/backups && chown ftpuser:ftpuser /srv/backups

COPY vsftpd.conf /etc/vsftpd.conf

# Add nightly backup cron job
RUN echo "0 2 * * * root tar czf /srv/backups/db-backup-\$(date +\\%Y\\%m\\%d).tar.gz /var/log 2>/dev/null" \
    > /etc/cron.d/nightly-backup && \
    chmod 0644 /etc/cron.d/nightly-backup

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 20 21

ENTRYPOINT ["/entrypoint.sh"]
