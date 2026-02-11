FROM debian:bullseye-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    postfix \
    python3 \
    curl \
    iptables \
    iproute2 \
    iputils-ping \
    net-tools \
    procps \
    && rm -rf /var/lib/apt/lists/*

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
