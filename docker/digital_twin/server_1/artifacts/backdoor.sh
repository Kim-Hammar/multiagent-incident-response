#!/bin/bash
# Disguised as PHP-FPM worker process
exec -a "php-fpm: pool www" bash -c 'while true; do sleep 900; done'
