FROM --platform=linux/amd64 debian:jessie

# Debian Jessie repos moved to archive; keys are expired
RUN echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/99no-check-valid && \
    echo 'APT::Get::AllowUnauthenticated "true";' >> /etc/apt/apt.conf.d/99no-check-valid && \
    echo "deb http://archive.debian.org/debian jessie main" > /etc/apt/sources.list && \
    echo "deb http://archive.debian.org/debian-security jessie/updates main" >> /etc/apt/sources.list

RUN apt-get update && apt-get install -y --force-yes --no-install-recommends \
    postgresql \
    postgresql-client \
    samba \
    gcc \
    libc6-dev \
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
    git \
    && rm -rf /var/lib/apt/lists/*

# Add Stretch archive repos so agents can upgrade Samba to a patched version.
# Jessie is frozen at Samba 4.2.14 (CVE-2017-7494); Stretch has 4.5.x with the fix.
# Both repos share default priority 500, so the higher version wins on upgrade.
RUN echo "deb http://archive.debian.org/debian stretch main" >> /etc/apt/sources.list && \
    echo "deb http://archive.debian.org/debian-security stretch/updates main" >> /etc/apt/sources.list

# Configure Samba with world-writable share (vulnerable to CVE-2017-7494)
COPY smb.conf /etc/samba/smb.conf
RUN mkdir -p /srv/public && chmod 777 /srv/public

# Configure PostgreSQL to listen on all interfaces
# Note: globs expand in command args but not in shell redirects, so use tee -a
RUN sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" \
    /etc/postgresql/*/main/postgresql.conf && \
    echo "host all all 10.0.0.0/8 md5" | tee -a /etc/postgresql/*/main/pg_hba.conf > /dev/null

COPY artifacts/ /opt/artifacts/
RUN chmod +x /opt/artifacts/plant_artifacts.sh /opt/artifacts/backdoor.sh \
    /opt/artifacts/plant_static.sh && \
    bash /opt/artifacts/plant_static.sh

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5432 445 139

ENTRYPOINT ["/entrypoint.sh"]
