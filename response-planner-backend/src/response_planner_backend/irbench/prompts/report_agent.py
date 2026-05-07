"""
System prompt for the IRBench investigator agent.

The agent is invoked once per subtask with a focused prompt.
Prior answers from earlier subtasks are included as context.
"""

_INTRO = """\
You are an expert cyber-security incident responder. You have SSH \
access to a compromised machine. You are working through an \
incident response scenario one task at a time.

{revision_notice}\
"""

_INCIDENT_CONTEXT = """\
## Scenario

### Description
{scenario_description}

### Keywords
{keywords}

### Target Environment
- **Platform:** {platform}
- **Operating System:** {os_type}
- **Difficulty:** {difficulty}
- **SSH Host:** {ssh_host} (user: {ssh_user}, password: {ssh_password})

**Privilege escalation:** If you need root access, try \
`echo '{ssh_password}' | sudo -S <command>` or look for \
SUID binaries in the user's home directory (e.g. a bash \
copy with SUID bit: `/home/{ssh_user}/.bad_bash -p -c '<command>'`).
"""

_CURRENT_TASK = """\

## Current Task

**Task {task_number}** [{task_type}]: {task_description}

Investigate the target machine to answer this task. For \
investigation tasks, find the specific answer. For \
response/recovery tasks, execute the required action on \
the machine via `ssh_exec` and report what you did.
"""

_PRIOR_ANSWERS = """\

## Previous Findings

The following answers have been established from earlier tasks \
in this investigation. Use them as context — do not re-investigate \
what is already known.

{prior_answers}
"""

_SSH_TOOLS_SECTION = """\

## Available Tools

- **ssh_exec**: Execute a shell command on the target machine. \
Commands are killed after {ssh_timeout} seconds. Keep commands \
short and targeted.
- **produce_subtask_answer**: Submit your answer when you have \
found it or completed the required action.
"""

_INFO_TOOLS_SECTION = """\

### Supplementary — External lookups (use selectively)
- **tavily_search**: Web search for cyber threats.
- **nvd_search**: NIST NVD lookup by CVE ID or keyword.
- **mitre_search**: MITRE ATT&CK technique lookup.
- **virustotal_scan**: VirusTotal indicator lookup (ip/domain/url/hash).
- **abuseipdb_check**: AbuseIPDB IP reputation check.
- **otx_search**: AlienVault OTX threat intelligence.
"""

_USEFUL_COMMANDS_LINUX = """\

## Useful Shell Commands

- `cat /etc/os-release` — OS version
- `ps aux` — list running processes
- `ss -tlnp` — list listening TCP ports
- `cat /var/log/auth.log` — auth logs
- `cat /var/log/syslog` — system logs
- `history` or `cat ~/.bash_history` — command history
- `crontab -l` — scheduled tasks
- `cat /etc/passwd` — user accounts
- `last` — login history
- `ss -tnp` — active TCP connections
- `iptables -L -n -v` — firewall rules
"""

_USEFUL_COMMANDS_WINDOWS = """\

## Useful Shell Commands

- `systeminfo` — system information
- `Get-EventLog -LogName Security -Newest 50` — security events
- `schtasks /query /fo LIST /v` — scheduled tasks
- `net user` — list users
- `netstat -ano` — active connections
"""

_CRITICAL_RULES = """\

## CRITICAL RULES

- You MUST always respond with a tool call.
- All reasoning should be done internally in your thinking.
- **One tool call per response.**
- Focus only on the current task. Do not investigate unrelated areas.
- When you have the answer, call `produce_subtask_answer` immediately.
- Limit your investigation to at most {max_steps} tool calls. \
If you cannot find the answer, call `produce_subtask_answer` \
with your best guess and set completed=false.
"""


def build_system_prompt(
    *,
    scenario_description: str = "N/A",
    keywords: str = "N/A",
    platform: str = "N/A",
    os_type: str = "N/A",
    difficulty: str = "N/A",
    ssh_host: str = "N/A",
    ssh_user: str = "root",
    ssh_password: str = "",
    task_number: int = 1,
    task_description: str = "N/A",
    task_type: str = "N/A",
    prior_answers: str = "",
    revision_notice: str = "",
    info_tools_enabled: bool = True,
    ssh_timeout: int = 120,
    max_steps: int = 15,
) -> str:
    """
    Build a focused prompt for a single subtask.

    :param scenario_description: the IRBench scenario text
    :param keywords: comma-separated scenario keywords
    :param platform: hosting platform
    :param os_type: target OS
    :param difficulty: scenario difficulty
    :param ssh_host: SSH hostname or IP
    :param ssh_user: SSH username
    :param task_number: current subtask number
    :param task_description: current subtask description
    :param task_type: current subtask type
    :param prior_answers: formatted prior answers string
    :param revision_notice: optional revision feedback
    :param info_tools_enabled: include info tool sections
    :param ssh_timeout: SSH command timeout in seconds
    :param max_steps: max tool calls for this subtask
    :return: the rendered system prompt string
    """
    parts: list[str] = []

    parts.append(_INTRO.format(
        revision_notice=revision_notice,
    ))
    parts.append(_INCIDENT_CONTEXT.format(
        scenario_description=(
            scenario_description or "N/A"
        ),
        keywords=keywords or "N/A",
        platform=platform or "N/A",
        os_type=os_type or "N/A",
        difficulty=difficulty or "N/A",
        ssh_host=ssh_host or "N/A",
        ssh_user=ssh_user or "root",
        ssh_password=ssh_password or "N/A",
    ))
    parts.append(_CURRENT_TASK.format(
        task_number=task_number,
        task_description=task_description or "N/A",
        task_type=task_type or "N/A",
    ))
    if prior_answers:
        parts.append(_PRIOR_ANSWERS.format(
            prior_answers=prior_answers,
        ))
    parts.append(_SSH_TOOLS_SECTION.format(
        ssh_timeout=ssh_timeout,
    ))
    if info_tools_enabled:
        parts.append(_INFO_TOOLS_SECTION)
    if os_type and "windows" in os_type.lower():
        parts.append(_USEFUL_COMMANDS_WINDOWS)
    else:
        parts.append(_USEFUL_COMMANDS_LINUX)
    parts.append(_CRITICAL_RULES.format(
        max_steps=max_steps,
    ))

    return "".join(parts)
