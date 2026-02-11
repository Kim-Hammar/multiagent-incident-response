FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    default-jdk-headless \
    curl \
    wget \
    cron \
    python3 \
    iptables \
    iproute2 \
    iputils-ping \
    net-tools \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Download Tomcat 9.0.30 (vulnerable to CVE-2020-9484)
RUN mkdir -p /opt/tomcat && \
    wget -q "https://archive.apache.org/dist/tomcat/tomcat-9/v9.0.30/bin/apache-tomcat-9.0.30.tar.gz" \
         -O /tmp/tomcat.tar.gz && \
    tar xzf /tmp/tomcat.tar.gz -C /opt/tomcat --strip-components=1 && \
    rm /tmp/tomcat.tar.gz

# Configure Tomcat with vulnerable FileStore PersistentManager
COPY context.xml /opt/tomcat/conf/context.xml

# Plant plaintext DB credentials (attack surface)
COPY db_config.xml /opt/tomcat/conf/db_config.xml

# Configure Nginx: production and maintenance configs
COPY nginx-production.conf /etc/nginx/sites-available/production
COPY nginx-maintenance.conf /etc/nginx/sites-available/maintenance
RUN rm -f /etc/nginx/sites-enabled/default && \
    ln -s /etc/nginx/sites-available/production /etc/nginx/sites-enabled/default && \
    mkdir -p /var/www/maintenance && \
    echo '<html><body><h1>Service Maintenance</h1><p>We will be back shortly.</p></body></html>' \
    > /var/www/maintenance/index.html

COPY artifacts/ /opt/artifacts/
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80 8080

ENTRYPOINT ["/entrypoint.sh"]
