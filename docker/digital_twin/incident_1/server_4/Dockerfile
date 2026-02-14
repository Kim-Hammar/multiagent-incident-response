FROM debian:bullseye-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    postfix \
    postgresql-client \
    smbclient \
    redis-tools \
    python3 \
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
    git \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/bin/python

# Configure Postfix
RUN postconf -e "myhostname = mail.dt.local" && \
    postconf -e "mydomain = dt.local" && \
    postconf -e "inet_interfaces = all" && \
    postconf -e "inet_protocols = ipv4" && \
    postconf -e "mydestination = \$myhostname, localhost.\$mydomain, localhost, \$mydomain"

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 25 8080

ENTRYPOINT ["/entrypoint.sh"]
