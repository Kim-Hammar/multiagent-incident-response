FROM debian:bullseye-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    python3 \
    redis-server \
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
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/bin/python

RUN mkdir /var/run/sshd

# Configure Redis to listen on all interfaces
RUN sed -i 's/^bind .*/bind 0.0.0.0/' /etc/redis/redis.conf

COPY app.py /opt/app.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22 8080 6379

ENTRYPOINT ["/entrypoint.sh"]
