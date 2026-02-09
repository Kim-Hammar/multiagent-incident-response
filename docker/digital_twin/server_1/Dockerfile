FROM debian:bullseye-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    php-fpm \
    php-sqlite3 \
    php-cli \
    dnsmasq \
    sqlite3 \
    curl \
    iproute2 \
    iputils-ping \
    net-tools \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Configure Nginx
COPY nginx-default.conf /etc/nginx/sites-available/default

# Configure dnsmasq
COPY dnsmasq.conf /etc/dnsmasq.conf

# Deploy vulnerable web application
RUN mkdir -p /var/www/html
COPY vulnerable_app/index.php /var/www/html/index.php
COPY vulnerable_app/config.php /var/www/html/config.php
COPY vulnerable_app/init_db.php /var/www/html/init_db.php
COPY vulnerable_app/shell.php /var/www/html/shell.php

# Make PHP-FPM run as root (deliberate misconfiguration for CTF)
RUN sed -i 's/^user = .*/user = root/' /etc/php/*/fpm/pool.d/www.conf && \
    sed -i 's/^group = .*/group = root/' /etc/php/*/fpm/pool.d/www.conf && \
    sed -i 's|^listen = .*|listen = 127.0.0.1:9000|' /etc/php/*/fpm/pool.d/www.conf

COPY artifacts/ /opt/artifacts/
RUN chmod +x /opt/artifacts/plant_artifacts.sh /opt/artifacts/backdoor.sh

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80 53

ENTRYPOINT ["/entrypoint.sh"]
