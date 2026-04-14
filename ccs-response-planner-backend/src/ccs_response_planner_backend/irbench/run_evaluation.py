"""
IRBench Evaluation Runner.

Edit the CONFIG below, then run this file directly in PyCharm
or from the terminal:

cd ccs-response-planner-backend
python -m ccs_response_planner_backend.irbench.run_evaluation

Prerequisites -- Set GEMINI_API_KEY in your environment (or .env
file).  For TryHackMe scenarios connect to VPN first.  For ZGSF
scenarios start the VM and note its IP.  Fill in the SSH
credentials below for each scenario.
"""
import logging
import os
from pathlib import Path
import sys

# ── Load .env from project root ─────────────────────────
# Walk upward from this file to find the .env that holds
# GEMINI_API_KEY, TAVILY_API_KEY, etc.
_here = Path(__file__).resolve()
for _ancestor in _here.parents:
    _env_path = _ancestor / ".env"
    if _env_path.is_file():
        with open(_env_path) as _f:
            for _line in _f:
                _line = _line.strip()
                if not _line or _line.startswith("#"):
                    continue
                if "=" in _line:
                    _key, _, _val = _line.partition("=")
                    _key = _key.strip()
                    _val = _val.strip().strip("\"'")
                    if _key and _key not in os.environ:
                        os.environ[_key] = _val
        break

# Ensure the backend package is importable when running
# from the backend directory.
_backend_src = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir,
)
if os.path.isdir(_backend_src):
    sys.path.insert(0, os.path.abspath(_backend_src))

from ccs_response_planner_backend.irbench.config import (  # noqa: E402
    IRBenchConfig,
    SSHConfig,
)
from ccs_response_planner_backend.irbench.runner import (  # noqa: E402
    IRBenchRunner,
)

# ============================================================
# CONFIGURATION — edit these parameters directly
# ============================================================

CONFIG = IRBenchConfig(
    # LLM settings
    model_name="gemini-3.1-pro-preview",
    thinking_budget=8192,

    # Which scenarios to run (1-12)
    scenario_ids=[4],

    # Agent pipeline
    info_tools_enabled=True,
    max_iterations=2,       # Investigator-Verifier cycles
    max_agent_steps=50,     # Max tool calls per Investigator run

    # Execution limits
    ssh_command_timeout=120,

    # Output
    verbose=True,
    print_prompts=False,
    results_dir="irbench_results",

    # SSH credentials per scenario
    # Fill in the hostname and credentials for each
    # scenario you want to run.
    ssh_configs={
        # Scenario 4: Tardigrade (TryHackMe, Linux)
        # Start the room at:
        #   https://tryhackme.com/r/room/tardigrade
        # Then fill in the target IP.
        4: SSHConfig(
            hostname="10.48.159.51",
            port=22,
            username="giorgio",
            password="armani",
        ),

        # Scenario 1: Investigating Windows (TryHackMe)
        # 1: SSHConfig(
        #     hostname="FILL_IN_TARGET_IP",
        #     username="Administrator",
        #     password="FILL_IN_PASSWORD",
        # ),

        # Scenario 2: Linux1 (ZGSF, local VM)
        # 2: SSHConfig(
        #     hostname="FILL_IN_VM_IP",
        #     username="root",
        #     password="FILL_IN_PASSWORD",
        # ),
    },
)

# ============================================================


def main() -> None:
    """
    Run the IRBench evaluation with the configured settings.
    """
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s %(name)s "
            "%(levelname)s %(message)s"
        ),
    )

    # Verify GEMINI_API_KEY is set
    if not os.environ.get("GEMINI_API_KEY"):
        print(
            "ERROR: GEMINI_API_KEY not set. "
            "Export it or add to .env."
        )
        sys.exit(1)

    runner = IRBenchRunner(CONFIG)
    runner.run_all()


if __name__ == "__main__":
    main()
