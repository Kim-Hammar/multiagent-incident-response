"""
Configuration dataclasses for IRBench evaluation.

All parameters are set directly in code (no CLI arguments)
so they can be easily edited in an IDE like PyCharm.
"""
from dataclasses import dataclass, field


@dataclass
class SSHConfig:
    """
    SSH connection parameters for a single target machine.

    :param hostname: IP or hostname of the target
    :param port: SSH port (default 22)
    :param username: SSH username (default root)
    :param password: SSH password (empty if using key auth)
    :param key_filename: path to SSH private key file
    """

    hostname: str
    port: int = 22
    username: str = "root"
    password: str = ""
    key_filename: str = ""


@dataclass
class IRBenchConfig:
    """
    Top-level configuration for an IRBench evaluation run.

    The IRBench pipeline uses two agents:

    1. **Investigator** — investigates the target via SSH,
       solves all subtasks (detection + remediation).
    2. **InvestigatorVerifier** — reviews the report for
       correctness, gives feedback on errors.

    They iterate for ``max_iterations`` cycles.

    :param model_name: Gemini model to use for both agents
    :param thinking_budget: token budget for extended thinking
    :param compaction_threshold: context usage fraction that
        triggers compaction (0.0 to disable)
    :param scenario_ids: which IRBench scenarios to evaluate
    :param info_tools_enabled: enable external info tools
        (Tavily, NVD, MITRE, VirusTotal, AbuseIPDB, OTX)
    :param max_iterations: max Investigator-Verifier cycles
    :param max_steps_per_subtask: max LLM tool-calling
        rounds per individual subtask investigation
    :param max_agent_steps: max LLM tool-calling rounds
        for the Verifier agent
    :param ssh_command_timeout: seconds per SSH command
    :param verbose: print thinking traces and tool calls
        to terminal
    :param results_dir: directory for JSON result files
    :param ssh_configs: SSH credentials keyed by scenario id
    :param irbench_dir: path to the IRBench scenario
        markdown files (empty = auto-resolve from project root)
    """

    # LLM
    model_name: str = "gemini-3.1-pro-preview"
    thinking_budget: int = 8192
    compaction_threshold: float = 0.8

    # Scenario selection
    scenario_ids: list[int] = field(
        default_factory=lambda: [4],
    )

    # Agent pipeline
    info_tools_enabled: bool = True
    max_iterations: int = 2
    max_steps_per_subtask: int = 15
    max_agent_steps: int = 15

    # Execution limits
    ssh_command_timeout: int = 120

    # Output
    verbose: bool = True
    print_prompts: bool = False
    results_dir: str = "irbench_results"

    # SSH credentials per scenario
    ssh_configs: dict[int, SSHConfig] = field(
        default_factory=dict,
    )

    # Path to IRBench scenario files.
    # Default: resolved relative to the project root.
    irbench_dir: str = ""
