FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    ncat \
    hydra \
    smbclient \
    sshpass \
    openssh-client \
    curl \
    wget \
    python3 \
    python3-pip \
    python3-venv \
    gcc \
    libc6-dev \
    postgresql-client \
    ftp \
    dnsutils \
    tcpdump \
    iptables \
    iproute2 \
    iputils-ping \
    net-tools \
    netcat-openbsd \
    telnet \
    traceroute \
    procps \
    git \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir impacket
ENV PATH="/opt/venv/bin:$PATH"

# Metasploit Framework — provides ready-made exploits for known CVEs
RUN mkdir -p /opt/metasploit && \
    curl -fsSL https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb \
      -o /tmp/msfinstall && \
    chmod +x /tmp/msfinstall && \
    /tmp/msfinstall && \
    rm -f /tmp/msfinstall

CMD ["sleep", "infinity"]
