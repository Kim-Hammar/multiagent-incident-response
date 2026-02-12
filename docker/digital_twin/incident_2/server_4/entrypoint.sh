#!/bin/bash
set -e

# Start PostgreSQL
service postgresql start

# Wait for PostgreSQL to be ready
for i in $(seq 1 30); do
    if su - postgres -c "pg_isready" 2>/dev/null; then
        break
    fi
    sleep 1
done

# Initialize database
su - postgres -c "psql -f /opt/init_db.sql" 2>/dev/null || true

# Start SSH daemon
/usr/sbin/sshd 2>/dev/null || true

# Plant static log artifacts
mkdir -p /var/log/postgresql
cp /opt/artifacts/postgresql.log /var/log/postgresql/postgresql-13-main.log
cp /opt/artifacts/syslog /var/log/syslog
cp /opt/artifacts/bash_history /root/.bash_history

# Plant crypto-miner placeholder
echo "#!/bin/bash\nwhile true; do sleep 60; done" > /tmp/.kworker_fake
chmod +x /tmp/.kworker_fake

# Plant runtime artifacts: cmd_exec table with evidence
(
    sleep 5
    su - postgres -c "psql -d crm_production -c \"CREATE TABLE IF NOT EXISTS cmd_exec(cmd_output text);\"" 2>/dev/null || true
    su - postgres -c "psql -d crm_production -c \"INSERT INTO cmd_exec VALUES ('uid=0(root) gid=0(root) groups=0(root)');\"" 2>/dev/null || true
    su - postgres -c "psql -d crm_production -c \"INSERT INTO cmd_exec VALUES ('root:x:0:0:root:/root:/bin/bash');\"" 2>/dev/null || true
) &

# Start disguised background process simulating crypto-miner
nohup /tmp/.kworker_fake >/dev/null 2>&1 &

# Keep container alive
exec tail -f /dev/null
