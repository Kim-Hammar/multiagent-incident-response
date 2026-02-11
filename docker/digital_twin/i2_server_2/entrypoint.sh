#!/bin/bash
set -e

# Start Nginx in daemon mode
nginx

# Start Tomcat
/opt/tomcat/bin/catalina.sh start

# Wait for Tomcat to be ready on port 8080
for i in $(seq 1 30); do
    if curl -s -o /dev/null http://127.0.0.1:8080/ 2>/dev/null; then
        break
    fi
    sleep 1
done

# Plant attack artifacts
mkdir -p /opt/tomcat/sessions
cp /opt/artifacts/shell.jsp /opt/tomcat/webapps/ROOT/shell.jsp
cp /opt/artifacts/access.log /opt/tomcat/logs/access.log
cp /opt/artifacts/bash_history /root/.bash_history

# Plant cron persistence
mkdir -p /etc/cron.d
cp /opt/artifacts/cleanup.sh /etc/cron.d/.cleanup.sh
chmod +x /etc/cron.d/.cleanup.sh

# Keep container alive
exec tail -f /dev/null
