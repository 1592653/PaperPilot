"""Persistent token usage tracking with daily/weekly/monthly aggregation."""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path


class TokenTracker:
    """Persist token usage to a JSONL file for reporting."""

    def __init__(self, log_dir: str = ".paperpilot"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / "token_usage.jsonl"

    def log(self, module: str, input_tokens: int, output_tokens: int,
            cache_read: int = 0, detail: str = "") -> None:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "module": module,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read": cache_read,
            "total_tokens": input_tokens + output_tokens,
            "detail": detail,
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_today_usage(self) -> dict:
        return self._aggregate(days=1)

    def get_week_usage(self) -> dict:
        return self._aggregate(days=7)

    def get_month_usage(self) -> dict:
        return self._aggregate(days=30)

    def _aggregate(self, days: int) -> dict:
        cutoff = datetime.now() - timedelta(days=days)
        stats = {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0,
                 "cache_read": 0, "calls": 0, "by_module": {}}

        if not self.log_file.exists():
            return stats

        for line in self.log_file.read_text(encoding="utf-8").strip().split("\n"):
            if not line.strip():
                continue
            entry = json.loads(line)
            ts = datetime.fromisoformat(entry["timestamp"])
            if ts < cutoff:
                continue

            stats["total_tokens"] += entry["total_tokens"]
            stats["input_tokens"] += entry["input_tokens"]
            stats["output_tokens"] += entry["output_tokens"]
            stats["cache_read"] += entry.get("cache_read", 0)
            stats["calls"] += 1

            mod = entry["module"]
            if mod not in stats["by_module"]:
                stats["by_module"][mod] = {"tokens": 0, "calls": 0}
            stats["by_module"][mod]["tokens"] += entry["total_tokens"]
            stats["by_module"][mod]["calls"] += 1

        return stats

    def print_report(self) -> str:
        today = self.get_today_usage()
        week = self.get_week_usage()
        month = self.get_month_usage()

        lines = [
            "=== PaperPilot Token Usage Report ===",
            "",
            f"{'Period':<12} {'Calls':>8} {'Input':>12} {'Output':>12} {'Cache':>12} {'Total':>12}",
            "-" * 70,
        ]
        for label, data in [("Today", today), ("This Week", week), ("This Month", month)]:
            lines.append(
                f"{label:<12} {data['calls']:>8} {data['input_tokens']:>12,} "
                f"{data['output_tokens']:>12,} {data['cache_read']:>12,} "
                f"{data['total_tokens']:>12,}"
            )

        if today["by_module"]:
            lines.extend(["", "--- Today by Module ---"])
            for mod, s in sorted(today["by_module"].items(), key=lambda x: -x[1]["tokens"]):
                lines.append(f"  {mod:<20} {s['calls']:>5} calls  {s['tokens']:>10,} tokens")

        report = "\n".join(lines)
        print(report)
        return report
