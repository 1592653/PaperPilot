"""Claude API client with token tracking and prompt caching."""

import json
import os
from dataclasses import dataclass, field

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()


@dataclass
class TokenUsage:
    """Track cumulative token usage across all API calls."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_creation: int = 0
    total_calls: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def add(self, usage) -> None:
        self.input_tokens += getattr(usage, "input_tokens", 0)
        self.output_tokens += getattr(usage, "output_tokens", 0)
        self.cache_read += getattr(usage, "cache_read_input_tokens", 0)
        self.cache_creation += getattr(usage, "cache_creation_input_tokens", 0)
        self.total_calls += 1

    def summary(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_read": self.cache_read,
            "cache_creation": self.cache_creation,
            "total_tokens": self.total_tokens,
        }

    def __str__(self) -> str:
        return (
            f"[{self.total_calls} calls] "
            f"in={self.input_tokens:,} out={self.output_tokens:,} "
            f"cache_read={self.cache_read:,} total={self.total_tokens:,}"
        )


class ClaudeClient:
    """Wrapper around Anthropic Claude API with tool-use loop and caching."""

    def __init__(self, model: str | None = None):
        self.client = Anthropic()
        self.model = model or os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
        self.session_usage = TokenUsage()

    def chat(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
    ) -> dict:
        """Single-turn API call."""
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        resp = self.client.messages.create(**kwargs)
        self.session_usage.add(resp.usage)

        result = {"text": "", "tool_calls": [], "stop_reason": resp.stop_reason}
        for block in resp.content:
            if block.type == "text":
                result["text"] += block.text
            elif block.type == "tool_use":
                result["tool_calls"].append({
                    "id": block.id, "name": block.name, "input": block.input,
                })
        return result

    def chat_with_tools(
        self,
        system: str,
        messages: list[dict],
        tools: list[dict],
        tool_executor,
        max_tokens: int = 4096,
        max_rounds: int = 15,
    ) -> dict:
        """Multi-round conversation with automatic tool execution."""
        full_text = ""
        tool_log = []

        for round_idx in range(max_rounds):
            resp = self.chat(system, messages, tools, max_tokens)
            full_text += resp["text"]

            if not resp["tool_calls"]:
                return {
                    "text": full_text,
                    "tool_log": tool_log,
                    "rounds": round_idx + 1,
                }

            # Append assistant message with tool_use blocks
            assistant_content = []
            if resp["text"]:
                assistant_content.append({"type": "text", "text": resp["text"]})
            for tc in resp["tool_calls"]:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["name"],
                    "input": tc["input"],
                })
            messages.append({"role": "assistant", "content": assistant_content})

            # Execute each tool and collect results
            tool_results = []
            for tc in resp["tool_calls"]:
                try:
                    output = tool_executor(tc["name"], tc["input"])
                except Exception as e:
                    output = {"error": str(e)}
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": json.dumps(output, ensure_ascii=False, default=str)[:20000],
                })
                tool_log.append({"tool": tc["name"], "input_keys": list(tc["input"].keys())})

            messages.append({"role": "user", "content": tool_results})

        return {"text": full_text, "tool_log": tool_log, "rounds": max_rounds}
