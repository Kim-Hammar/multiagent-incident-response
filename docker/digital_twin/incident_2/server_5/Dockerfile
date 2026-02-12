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
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /run/sshd

COPY dnsmasq.conf /etc/dnsmasq.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 53 22

ENTRYPOINT ["/entrypoint.sh"]
