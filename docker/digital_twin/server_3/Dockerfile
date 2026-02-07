FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-server \
    cron \
    sudo \
    curl \
    iproute2 \
    iputils-ping \
    net-tools \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Create vulnerable user with weak password and sudo access
RUN useradd -m -s /bin/bash admin && \
    echo "admin:password123" | chpasswd && \
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

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22

ENTRYPOINT ["/entrypoint.sh"]
