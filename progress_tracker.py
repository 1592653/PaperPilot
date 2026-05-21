"""Progress Tracker - Track research progress and build a knowledge base."""

import json
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from paperpilot.utils.api import ClaudeClient
from paperpilot.utils.token_tracker import TokenTracker

console = Console()


class ProgressTracker:
    """Track research progress, manage knowledge base, and suggest next steps."""

    def __init__(self, db, tracker: TokenTracker):
        self.client = ClaudeClient()
        self.db = db
        self.tracker = tracker

    def add_insight(self, title: str, content: str, category: str = "general",
                    source: str = "") -> int:
        """Add a research insight to the knowledge base."""
        entry_id = self.db.add_knowledge(
            category=category, title=title, content=content,
            source_experiment=source,
        )
        console.print(f"[green]Knowledge entry #{entry_id} added: {title}[/green]")
        return entry_id

    def log_experiment_insight(self, exp_id: int, insight: str) -> None:
        """Log an insight derived from an experiment."""
        exps = self.db.get_experiments()
        exp = next((e for e in exps if e["id"] == exp_id), None)
        exp_name = exp["name"] if exp else f"exp_{exp_id}"

        self.db.add_knowledge(
            category="experiment_insight",
            title=f"Insight from {exp_name}",
            content=insight,
            source_experiment=exp_name,
        )

    def suggest_next_steps(self, research_goal: str) -> dict:
        """Use Claude to suggest next research steps based on history."""
        console.print(Panel("Analyzing research progress...", title="Progress Tracker"))

        # Gather context
        experiments = self.db.get_experiments(limit=20)
        knowledge = self.db.get_knowledge()
        papers = self.db.get_recent_papers(limit=10)

        context = f"Research goal: {research_goal}\n\n"

        if experiments:
            context += "## Recent Experiments\n"
            for e in experiments[:10]:
                m = e.get("metrics", "{}")
                context += f"- {e['name']} [{e.get('status', '?')}]: {m}\n"

        if knowledge:
            context += "\n## Knowledge Base\n"
            for k in knowledge[:10]:
                context += f"- [{k['category']}] {k['title']}: {k['content'][:150]}\n"

        if papers:
            context += "\n## Analyzed Papers\n"
            for p in papers[:5]:
                context += f"- {p['title']}\n"

        messages = [{
            "role": "user",
            "content": (
                f"Based on this research history, suggest the next 3-5 concrete steps:\n\n"
                f"{context}\n\n"
                f"For each step, provide: 1) What to do 2) Why 3) Expected outcome"
            ),
        }]

        result = self.client.chat(
            system="You are a senior NLP research advisor. Give specific, actionable advice.",
            messages=messages, max_tokens=3000,
        )

        self.tracker.log("progress_tracker", self.client.session_usage.input_tokens,
                         self.client.session_usage.output_tokens, detail="suggest_next")

        return {"suggestions": result["text"]}

    def dashboard(self) -> None:
        """Display a research dashboard with key stats."""
        experiments = self.db.get_experiments()
        papers = self.db.get_recent_papers(limit=100)
        knowledge = self.db.get_knowledge()

        # Stats table
        table = Table(title="Research Dashboard", show_lines=True)
        table.add_column("Category", style="bold cyan")
        table.add_column("Count", justify="right")
        table.add_column("Details")

        completed = [e for e in experiments if e.get("status") == "completed"]
        running = [e for e in experiments if e.get("status") == "running"]
        table.add_row("Experiments", str(len(experiments)),
                       f"{len(completed)} completed, {len(running)} running")
        table.add_row("Papers", str(len(papers)), "")
        table.add_row("Knowledge Entries", str(len(knowledge)), "")

        # Token usage
        today_usage = self.tracker.get_today_usage()
        table.add_row("Tokens Today", f"{today_usage['total_tokens']:,}",
                       f"{today_usage['calls']} API calls")

        console.print(table)

        # Recent experiments
        if completed:
            console.print("\n[bold]Recent Completed Experiments:[/bold]")
            for e in completed[:5]:
                metrics = e.get("metrics", "{}")
                console.print(f"  [{e['id']}] {e['name']}: {metrics}")

        # Knowledge categories
        if knowledge:
            cats = {}
            for k in knowledge:
                cat = k.get("category", "general")
                cats[cat] = cats.get(cat, 0) + 1
            console.print("\n[bold]Knowledge Base:[/bold]")
            for cat, count in sorted(cats.items()):
                console.print(f"  {cat}: {count} entries")

    def export_summary(self) -> dict:
        """Export a summary of all research data."""
        return {
            "experiments": self.db.get_experiments(),
            "papers": self.db.get_recent_papers(limit=50),
            "knowledge": self.db.get_knowledge(),
            "token_usage_today": self.tracker.get_today_usage(),
            "token_usage_month": self.tracker.get_month_usage(),
        }
