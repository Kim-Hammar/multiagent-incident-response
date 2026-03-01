"""
Execution statistics collector for the orchestrator pipeline.

Accumulates per-agent token usage, function call counts,
wall-clock time, and step counts across multiple HTTP
requests.  Stats are persisted to the ``planning_sessions``
table between requests and compiled into a final report.
"""
import time
from typing import Any


class ExecutionStatsCollector:
    """
    Accumulates execution metrics for every agent in the
    orchestrator pipeline.

    Call ``to_dict()`` to serialise the current snapshot
    (suitable for JSONB storage) and ``merge()`` to restore
    a previously-saved snapshot.
    """

    def __init__(self) -> None:
        """
        Initialise an empty stats collector.
        """
        self._agents: dict[str, dict[str, Any]] = {}
        self._pipeline_start: float = time.time()
        self._pending_tokens: dict[
            str, dict[str, int]
        ] = {}

    # --------------------------------------------------
    # recording helpers
    # --------------------------------------------------

    def _ensure_agent(
        self, agent_name: str,
    ) -> dict[str, Any]:
        """
        Return the stats bucket for *agent_name*, creating
        it if it does not exist yet.

        :param agent_name: canonical agent name
        :return: mutable stats dict for the agent
        """
        if agent_name not in self._agents:
            self._agents[agent_name] = {
                "prompt_tokens": 0,
                "candidates_tokens": 0,
                "total_tokens": 0,
                "function_calls": 0,
                "wall_time_seconds": 0.0,
                "steps": 0,
                "tools": {},
            }
        return self._agents[agent_name]

    def record_tokens(
        self,
        agent_name: str,
        prompt_tokens: int,
        candidates_tokens: int,
        total_tokens: int,
    ) -> None:
        """
        Record token usage for a single LLM step.

        :param agent_name: canonical agent name
        :param prompt_tokens: input tokens consumed
        :param candidates_tokens: output tokens produced
        :param total_tokens: total tokens (prompt + output)
        """
        bucket = self._ensure_agent(agent_name)
        bucket["prompt_tokens"] += prompt_tokens
        bucket["candidates_tokens"] += candidates_tokens
        bucket["total_tokens"] += total_tokens
        bucket["steps"] += 1
        self._pending_tokens[agent_name] = {
            "prompt_tokens": prompt_tokens,
            "candidates_tokens": candidates_tokens,
            "total_tokens": total_tokens,
        }

    def record_function_call(
        self,
        agent_name: str,
        tool_name: str = "",
    ) -> None:
        """
        Increment the function-call counter for an agent.

        When *tool_name* is provided the call and any
        buffered token usage are also attributed to
        that specific tool.

        :param agent_name: canonical agent name
        :param tool_name: optional tool/function name
        """
        bucket = self._ensure_agent(agent_name)
        bucket["function_calls"] += 1
        if tool_name:
            tools = bucket["tools"]
            if tool_name not in tools:
                tools[tool_name] = {
                    "calls": 0,
                    "prompt_tokens": 0,
                    "candidates_tokens": 0,
                    "total_tokens": 0,
                }
            entry = tools[tool_name]
            entry["calls"] += 1
            pending = self._pending_tokens.pop(
                agent_name, None,
            )
            if pending:
                entry["prompt_tokens"] += (
                    pending["prompt_tokens"]
                )
                entry["candidates_tokens"] += (
                    pending["candidates_tokens"]
                )
                entry["total_tokens"] += (
                    pending["total_tokens"]
                )

    def record_wall_time(
        self, agent_name: str, seconds: float,
    ) -> None:
        """
        Add wall-clock time for an agent.

        :param agent_name: canonical agent name
        :param seconds: elapsed seconds to add
        """
        bucket = self._ensure_agent(agent_name)
        bucket["wall_time_seconds"] += seconds

    # --------------------------------------------------
    # serialisation / restoration
    # --------------------------------------------------

    def merge(
        self, stats_dict: dict[str, Any] | None,
    ) -> None:
        """
        Restore previously-saved stats (from the session DB).

        Adds the values from *stats_dict* into the current
        collector so that stats accumulate across HTTP
        requests.

        :param stats_dict: output of a prior ``to_dict()``
        """
        if not stats_dict:
            return
        if "pipeline_start_time" in stats_dict:
            self._pipeline_start = stats_dict[
                "pipeline_start_time"
            ]
        for name, agent_stats in stats_dict.get(
            "agents", {},
        ).items():
            bucket = self._ensure_agent(name)
            for key in (
                "prompt_tokens",
                "candidates_tokens",
                "total_tokens",
                "function_calls",
                "steps",
            ):
                bucket[key] += agent_stats.get(key, 0)
            bucket["wall_time_seconds"] += (
                agent_stats.get("wall_time_seconds", 0.0)
            )
            for tname, tstats in agent_stats.get(
                "tools", {},
            ).items():
                tools = bucket["tools"]
                if tname not in tools:
                    tools[tname] = {
                        "calls": 0,
                        "prompt_tokens": 0,
                        "candidates_tokens": 0,
                        "total_tokens": 0,
                    }
                entry = tools[tname]
                for tkey in (
                    "calls",
                    "prompt_tokens",
                    "candidates_tokens",
                    "total_tokens",
                ):
                    entry[tkey] += tstats.get(tkey, 0)

    def to_dict(self) -> dict[str, Any]:
        """
        Produce the final stats dict with per-agent data
        and computed totals.

        :return: serialisable stats dictionary
        """
        totals = {
            "prompt_tokens": 0,
            "candidates_tokens": 0,
            "total_tokens": 0,
            "function_calls": 0,
            "steps": 0,
        }
        for agent_stats in self._agents.values():
            for key in (
                "prompt_tokens",
                "candidates_tokens",
                "total_tokens",
                "function_calls",
                "steps",
            ):
                totals[key] += agent_stats.get(key, 0)

        return {
            "pipeline_start_time": self._pipeline_start,
            "total_wall_time_seconds": (
                time.time() - self._pipeline_start
            ),
            "agents": {
                name: {
                    **{
                        k: v
                        for k, v in stats.items()
                        if k != "tools"
                    },
                    "tools": {
                        tn: dict(ts)
                        for tn, ts in stats.get(
                            "tools", {},
                        ).items()
                    },
                }
                for name, stats in self._agents.items()
            },
            "totals": totals,
        }
