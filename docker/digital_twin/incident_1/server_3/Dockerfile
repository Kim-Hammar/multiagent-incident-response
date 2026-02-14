FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    sshpass \
    cron \
    sudo \
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
    python-is-python3 \
    git \
    postgresql-client \
    smbclient \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Create vulnerable user with weak password and sudo access
RUN useradd -m -s /bin/bash admin && \
    echo "admin:admin" | chpasswd && \
    usermod -aG sudo admin && \
    echo "admin ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Configure SSH for password authentication
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    echo "PermitRootLogin yes" >> /etc/ssh/sshd_config && \
    echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config

# Add CI/CD cron job (simulated build/deploy pipeline)
RUN echo "*/30 * * * * root echo \"[CI/CD] Build \$(date +\\%s) deployed\" >> /var/log/cicd.log" \
    > /etc/cron.d/cicd-pipeline && \
    chmod 0644 /etc/cron.d/cicd-pipeline

RUN mkdir /var/run/sshd

COPY artifacts/ /opt/artifacts/
RUN chmod +x /opt/artifacts/plant_artifacts.sh /opt/artifacts/backdoor.sh \
    /opt/artifacts/plant_static.sh && \
    bash /opt/artifacts/plant_static.sh

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22

ENTRYPOINT ["/entrypoint.sh"]
