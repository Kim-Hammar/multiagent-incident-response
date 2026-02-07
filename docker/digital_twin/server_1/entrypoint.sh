#!/bin/bash
set -e

# Initialize the SQLite database
php /var/www/html/init_db.php

# Start PHP-FPM as root (-R allows running as root for CTF scenario)
mkdir -p /run/php
php-fpm7.4 -R

# Wait for PHP-FPM to be listening on port 9000
for i in $(seq 1 10); do
    if ss -tlnp | grep -q ':9000'; then
        break
    fi
    sleep 1
done

# Start dnsmasq
dnsmasq

# Start Nginx in foreground
exec nginx -g 'daemon off;'
