"""Executor: runs the planner-generated action plan against shared state."""

from __future__ import annotations

import logging
from typing import Any

from doc_intel_poc.planner import Planner
from doc_intel_poc.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Safety limit to prevent infinite loops when the planner keeps inserting
# new actions.  Increase if workflows legitimately require more steps.
MAX_STEPS = 20


class Executor:
    """Iterates over a dynamic plan, executing registered tools.

    After every action the planner is asked to *revise* the remaining plan,
    which allows mid-execution changes (inserts, removals) driven by
    intermediate results.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        planner: Planner,
        *,
        max_steps: int = MAX_STEPS,
    ) -> None:
        self.registry = registry
        self.planner = planner
        self.max_steps = max_steps

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute the plan stored in *state['plan']* and return final state."""
        plan: list[str] = list(state.get("plan", []))
        state.setdefault("completed_actions", [])
        state.setdefault("execution_log", [])
        state.setdefault("errors", [])

        step = 0
        while step < len(plan) and step < self.max_steps:
            action_name = plan[step]
            tool = self.registry.get(action_name)

            if tool is None:
                msg = f"Unknown action in plan: '{action_name}'"
                logger.error(msg)
                state["errors"].append(msg)
                break

            logger.info("Step %d: executing '%s'", step + 1, action_name)
            state["execution_log"].append(
                {"step": step + 1, "action": action_name, "status": "started"}
            )

            try:
                tool(state)
                state["completed_actions"].append(action_name)
                state["execution_log"][-1]["status"] = "completed"
                logger.info("Step %d: '%s' completed", step + 1, action_name)
            except Exception as exc:
                msg = f"Action '{action_name}' failed: {exc}"
                logger.exception(msg)
                state["errors"].append(msg)
                state["execution_log"][-1]["status"] = "failed"
                break

            # Let the planner revise the remaining plan after each step.
            remaining = plan[step + 1 :]
            revised = self.planner.revise_plan(remaining, state)
            plan[step + 1 :] = revised

            step += 1

        if step >= self.max_steps:
            state["errors"].append(
                "Execution stopped after reaching max steps."
            )

        # Persist the (possibly revised) plan back into state.
        state["plan"] = plan
        return state
