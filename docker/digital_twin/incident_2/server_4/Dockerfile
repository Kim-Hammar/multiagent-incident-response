FROM debian:bullseye-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql \
    postgresql-client \
    openssh-server \
    iptables \
    iproute2 \
    iputils-ping \
    net-tools \
    curl \
    procps \
    dnsutils \
    openssh-client \
    netcat-openbsd \
    nmap \
    telnet \
    wget \
    ftp \
    tcpdump \
    traceroute \
    python3 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/bin/python

# Configure PostgreSQL to listen on all interfaces
RUN echo "listen_addresses = '*'" >> /etc/postgresql/13/main/postgresql.conf && \
    echo "host all all 10.0.0.0/8 md5" >> /etc/postgresql/13/main/pg_hba.conf

# Configure SSH
RUN mkdir -p /run/sshd

COPY init_db.sql /opt/init_db.sql
COPY artifacts/ /opt/artifacts/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5432 22

ENTRYPOINT ["/entrypoint.sh"]
