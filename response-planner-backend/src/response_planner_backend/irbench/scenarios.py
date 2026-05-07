"""
Scenario and subtask data structures, plus a markdown parser
that loads IRBench scenario files.
"""
import os
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Subtask:
    """
    A single IRBench subtask within a scenario.

    :param number: task number (1-based)
    :param description: the task description / question
    :param task_type: IRBench task type classification
        (e.g. "System Log Analysis")
    """

    number: int
    description: str
    task_type: str


@dataclass
class Scenario:
    """
    A complete IRBench scenario parsed from a markdown file.

    :param id: scenario number (1-12)
    :param name: scenario name
    :param source_url: URL of the hosting platform
    :param scenario_type: attack / investigation type
    :param keywords: list of relevant keywords
    :param description: narrative scenario description
    :param subtasks: ordered list of subtasks
    :param difficulty: Easy, Medium, or Hard
    :param platform: TryHackMe, ZGSF, or XuanJi
    :param os_type: Windows or Linux
    """

    id: int
    name: str
    source_url: str
    scenario_type: str
    keywords: list[str] = field(default_factory=list)
    description: str = ""
    subtasks: list[Subtask] = field(default_factory=list)
    difficulty: str = ""
    platform: str = ""
    os_type: str = ""


# Maps scenario IDs to (name, difficulty, platform, os)
# extracted from IRBench/0_Benchmark.md.
_SCENARIO_META: dict[
    int, tuple[str, str, str, str]
] = {
    1: (
        "Investigating Windows", "Easy",
        "TryHackMe", "Windows",
    ),
    2: ("Linux1", "Easy", "ZGSF", "Linux"),
    3: ("Web1", "Easy", "ZGSF", "Windows"),
    4: (
        "Tardigrade", "Medium",
        "TryHackMe", "Linux",
    ),
    5: (
        "VulnTarget-n-Ransomware", "Medium",
        "XuanJi", "Linux",
    ),
    6: ("Web2", "Medium", "ZGSF", "Windows"),
    7: ("Web3", "Medium", "ZGSF", "Windows"),
    8: (
        "Windows Black Pages & Tampering",
        "Medium", "XuanJi", "Windows",
    ),
    9: (
        "WindowsMiner", "Medium",
        "ZGSF", "Windows",
    ),
    10: ("Linux2", "Hard", "ZGSF", "Linux"),
    11: (
        "Memory Trojan Analysis - Nacos",
        "Hard", "XuanJi", "Linux",
    ),
    12: (
        "Where 1S tHe Hacker", "Hard",
        "XuanJi", "Windows",
    ),
}


def _find_scenario_file(
    irbench_dir: str, scenario_id: int,
) -> str:
    """
    Find the markdown file for a given scenario ID.

    Files are named ``{id}_*.md`` with varying suffixes.

    :param irbench_dir: directory containing the md files
    :param scenario_id: scenario number (1-12)
    :return: absolute path to the markdown file
    :raises FileNotFoundError: if no matching file exists
    """
    for entry in os.listdir(irbench_dir):
        if not entry.endswith(".md"):
            continue
        match = re.match(r"^(\d+)_", entry)
        if match and int(match.group(1)) == scenario_id:
            return os.path.join(irbench_dir, entry)
    raise FileNotFoundError(
        f"No IRBench markdown file found for "
        f"scenario {scenario_id} in {irbench_dir}"
    )


def _parse_subtask_table(
    lines: list[str],
) -> list[Subtask]:
    """
    Parse the markdown table of subtasks.

    Expects rows like:
    ``| 1 | Task description | Task type |``

    :param lines: raw lines from the markdown file
        starting after the table header
    :return: list of Subtask objects
    """
    subtasks: list[Subtask] = []
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [
            c.strip() for c in line.split("|")
        ]
        # Filter empty cells from leading/trailing |
        cells = [c for c in cells if c]
        if len(cells) < 3:
            continue
        # Skip header row and separator row
        if cells[0] in ("", "---") or cells[0].startswith("---"):
            continue
        try:
            num = int(cells[0])
        except ValueError:
            continue
        subtasks.append(Subtask(
            number=num,
            description=cells[1].strip(),
            task_type=cells[2].strip(),
        ))
    return subtasks


def load_scenario(
    scenario_id: int,
    irbench_dir: str | None = None,
) -> Scenario:
    """
    Parse an IRBench scenario markdown file.

    :param scenario_id: scenario number (1-12)
    :param irbench_dir: path to the IRBench directory;
        defaults to ``irbench/IRCopilot/IRBench`` relative
        to the project root
    :return: a populated Scenario object
    :raises FileNotFoundError: if the scenario file is
        not found
    """
    if irbench_dir is None:
        project_root = Path(__file__).resolve().parents[4]
        irbench_dir = str(
            project_root / "irbench" / "IRCopilot" / "IRBench"
        )

    filepath = _find_scenario_file(
        irbench_dir, scenario_id,
    )
    with open(filepath, encoding="utf-8") as f:
        text = f.read()

    lines = text.splitlines()

    # Parse Source
    source_url = ""
    for line in lines:
        m = re.match(
            r"\*\*Source\*\*:\s*(.*)", line,
        )
        if m:
            # Strip markdown link syntax if present
            url = m.group(1).strip()
            link_m = re.search(r"\((https?://[^)]+)\)", url)
            if link_m:
                url = link_m.group(1)
            source_url = url
            break

    # Parse Type
    scenario_type = ""
    for line in lines:
        m = re.match(
            r"\*\*Type\*\*:\s*(.*)", line,
        )
        if m:
            scenario_type = m.group(1).strip()
            break

    # Parse Keywords
    keywords: list[str] = []
    in_keywords = False
    for line in lines:
        if "#### Keywords" in line:
            in_keywords = True
            continue
        if in_keywords:
            if line.startswith("####") or (
                line.startswith("**")
            ):
                break
            stripped = line.strip().lstrip("- ").strip()
            if stripped:
                keywords.append(stripped)

    # Parse Scenario description
    description = ""
    in_scenario = False
    desc_lines: list[str] = []
    for line in lines:
        if "#### Scenario" in line:
            in_scenario = True
            continue
        if in_scenario:
            if line.startswith("####"):
                break
            desc_lines.append(line)
    description = "\n".join(desc_lines).strip()

    # Parse Subtask table
    subtask_start = -1
    for i, line in enumerate(lines):
        if re.match(
            r"####\s+Sub-task\s+Li", line, re.IGNORECASE,
        ):
            subtask_start = i + 1
            break
    subtasks: list[Subtask] = []
    if subtask_start >= 0:
        subtasks = _parse_subtask_table(
            lines[subtask_start:],
        )

    # Look up metadata
    meta = _SCENARIO_META.get(scenario_id)
    name = meta[0] if meta else ""
    difficulty = meta[1] if meta else ""
    platform = meta[2] if meta else ""
    os_type = meta[3] if meta else ""

    return Scenario(
        id=scenario_id,
        name=name,
        source_url=source_url,
        scenario_type=scenario_type,
        keywords=keywords,
        description=description,
        subtasks=subtasks,
        difficulty=difficulty,
        platform=platform,
        os_type=os_type,
    )


def load_all_scenarios(
    irbench_dir: str | None = None,
) -> list[Scenario]:
    """
    Load all 12 IRBench scenarios.

    :param irbench_dir: path to the IRBench directory
    :return: list of Scenario objects sorted by ID
    """
    scenarios: list[Scenario] = []
    for sid in range(1, 13):
        try:
            scenarios.append(
                load_scenario(sid, irbench_dir),
            )
        except FileNotFoundError:
            pass
    return scenarios
