"""Run a task through the autogen agent group chat for testing purposes.

This module creates a *fresh* SelectorGroupChat with the task as the initial
message (bypassing the interactive ``get_user_input`` loop).  All messages —
including tool-call requests and execution results — are collected and streamed
back via a callback so the testing dashboard can display the full chat log.

Uses ``nest_asyncio`` to allow running an asyncio event loop from within
eventlet's greenlet context without needing a separate OS thread.
"""

import asyncio
import json
import logging
import os
from contextlib import aclosing
from typing import Any, Callable, Dict, List, Optional

import nest_asyncio
nest_asyncio.apply()

from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import SelectorGroupChat

from .agent_manager import agent_manager
from .model_client import setup_model_client
from .selector import selector_exp

logger = logging.getLogger(__name__)


def _format_message(message) -> Optional[Dict[str, Any]]:
    """Convert an autogen message into a simple dict for the trace panel."""
    source = getattr(message, "source", "unknown")
    msg_type = getattr(message, "type", "")
    content = getattr(message, "content", "")

    if msg_type == "ToolCallRequestEvent":
        calls = []
        for fc in content:
            calls.append({"name": fc.name, "arguments": fc.arguments, "id": fc.id})
        return {
            "role": "tool_call",
            "source": source,
            "content": json.dumps(calls, indent=2),
            "calls": calls,
        }

    if msg_type == "ToolCallExecutionEvent":
        results = []
        for fr in content:
            results.append({"call_id": fr.call_id, "content": fr.content})
        return {
            "role": "tool_result",
            "source": source,
            "content": json.dumps(results, indent=2),
            "results": results,
        }

    # TaskResult — skip the giant summary object
    if "TaskResult" in str(type(message)):
        return None

    if isinstance(content, str):
        if not content.strip():
            return None
        return {"role": "agent", "source": source, "content": content}

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if hasattr(item, "content"):
                text_parts.append(str(item.content))
            else:
                text_parts.append(str(item))
        return {"role": "agent", "source": source, "content": "\n".join(text_parts)}

    return {"role": "agent", "source": source, "content": str(content)}


async def _run_chat(
    task: str,
    on_message: Callable[[Dict[str, Any]], None],
    max_turns: int = 15,
) -> List[Dict[str, Any]]:
    """Create a group chat, run the task, and collect all messages."""
    if not agent_manager.initialized:
        agent_manager.initialize_agents()
        agent_manager.enable_policy_system()

    model_client = setup_model_client()
    all_agents = agent_manager.get_agents_list()
    # Exclude the User agent — it blocks waiting for interactive input
    # which will never come during automated testing.
    agents = [a for a in all_agents if getattr(a, "name", "") != "User"]

    # Strip any tools that require human interaction (e.g. get_user_input)
    # so tests run fully headless.
    _INTERACTIVE_TOOLS = {"get_user_input"}
    for agent in agents:
        if hasattr(agent, "_tools"):
            agent._tools = [
                t for t in agent._tools
                if getattr(t, "name", "") not in _INTERACTIVE_TOOLS
            ]

    agent_names = {getattr(a, "name", "") for a in agents}
    termination = TextMentionTermination("terminate")

    def _test_selector(messages):
        pick = selector_exp(messages)
        if pick not in agent_names:
            return "Planner"
        return pick

    group_chat = SelectorGroupChat(
        agents,
        max_turns=max_turns,
        termination_condition=termination,
        model_client=model_client,
        selector_func=_test_selector,
    )

    collected: List[Dict[str, Any]] = []
    try:
        async with aclosing(group_chat.run_stream(task=task)) as stream:
            async for message in stream:
                formatted = _format_message(message)
                if formatted is None:
                    continue
                collected.append(formatted)
                try:
                    on_message(formatted)
                except Exception:
                    pass
                if isinstance(getattr(message, "content", ""), str):
                    if "terminate" in getattr(message, "content", "").lower():
                        break
    except Exception as exc:
        err = {"role": "error", "source": "system", "content": f"Agent error: {exc}"}
        collected.append(err)
        on_message(err)
    finally:
        try:
            await group_chat.reset()
        except Exception:
            pass

    return collected


def run_test_task(
    task: str,
    on_message: Callable[[Dict[str, Any]], None],
    max_turns: int = 15,
) -> List[Dict[str, Any]]:
    """Synchronous wrapper: run a task through the group chat.

    Sets ``PERMISSION_MANAGEMENT_MODE=skip`` for the duration so the agent
    doesn't ask the user to approve permissions.

    Uses nest_asyncio so we can run an asyncio event loop directly inside
    the current eventlet greenlet — no separate OS thread needed.
    """
    prev_mode = os.environ.get("PERMISSION_MANAGEMENT_MODE", "ask")
    os.environ["PERMISSION_MANAGEMENT_MODE"] = "skip"
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                _run_chat(task, on_message, max_turns)
            )
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            loop.close()
    finally:
        os.environ["PERMISSION_MANAGEMENT_MODE"] = prev_mode
