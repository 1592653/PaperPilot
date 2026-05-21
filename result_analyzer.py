"""Result Analyzer - Analyze experiment results, create visualizations, and compare with SOTA."""

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

from paperpilot.utils.api import ClaudeClient
from paperpilot.utils.tools import COMMON_TOOLS, execute_tool
from paperpilot.utils.token_tracker import TokenTracker

console = Console()

SYSTEM_PROMPT = """You are an expert ML experiment analyst. Your job is to analyze experiment results and provide actionable insights.

When analyzing results:
1. Read experiment logs and metric files from the output directory
2. Use Python to create visualizations (matplotlib/seaborn), saved as PNG files
3. Compare results across experiments and against SOTA baselines
4. Identify patterns: what works, what doesn't, and why

Visualization tasks (always save figures to the output directory):
- Learning curves (loss/accuracy over epochs)
- Metric comparison bar charts (across models/datasets)
- Confusion matrices (per hierarchy level if applicable)
- Radar charts for multi-metric comparison

Analysis output should include:
1. **Executive Summary**: 2-3 sentences of key findings
2. **Detailed Metrics Table**: All metrics in a clear table
3. **SOTA Comparison**: How results compare to published benchmarks
4. **Error Analysis**: Common failure patterns
5. **Recommendations**: Concrete next steps to improve

Be specific with numbers. Don't just say "good performance" - say "F1=0.847 which is 2.3% above the previous SOTA".
"""


class ResultAnalyzer:
    """Analyze experiment results and generate visualizations."""

    def __init__(self, db, tracker: TokenTracker, output_dir: str = "outputs"):
        self.client = ClaudeClient()
        self.db = db
        self.tracker = tracker
        self.output_dir = Path(output_dir)

    def analyze_experiment(self, exp_id: int) -> dict:
        """Analyze a single experiment by its database ID."""
        exps = self.db.get_experiments()
        exp = next((e for e in exps if e["id"] == exp_id), None)
        if not exp:
            return {"error": f"Experiment {exp_id} not found"}

        return self._run_analysis(exp, f"Analyze experiment '{exp['name']}' in detail.")

    def compare_experiments(self, exp_ids: list[int] | None = None) -> dict:
        """Compare multiple experiments side by side."""
        if exp_ids:
            exps = [e for e in self.db.get_experiments() if e["id"] in exp_ids]
        else:
            exps = self.db.get_experiments(limit=10)

        if not exps:
            return {"error": "No experiments found"}

        # Build comparison table
        table = Table(title="Experiment Comparison", show_lines=True)
        table.add_column("ID", style="dim")
        table.add_column("Name", style="bold")
        table.add_column("Dataset")
        table.add_column("Status")
        table.add_column("Key Metrics")

        for exp in exps:
            metrics_str = exp.get("metrics", "{}")
            if isinstance(metrics_str, str):
                import json
                try:
                    metrics = json.loads(metrics_str)
                    metrics_display = ", ".join(f"{k}={v:.4f}" if isinstance(v, float) else f"{k}={v}"
                                                for k, v in list(metrics.items())[:3])
                except:
                    metrics_display = metrics_str[:50]
            else:
                metrics_display = str(metrics_str)[:50]

            table.add_row(str(exp["id"]), exp["name"], exp.get("dataset", ""),
                          exp.get("status", ""), metrics_display)

        console.print(table)

        # Ask Claude to analyze the comparison
        exp_summaries = "\n".join(
            f"Exp {e['id']} ({e['name']}): metrics={e.get('metrics', '{}')}, "
            f"arch={e.get('model_arch', 'N/A')}"
            for e in exps
        )

        messages = [{
            "role": "user",
            "content": (
                f"Compare these experiments and identify the best approach:\n\n{exp_summaries}\n\n"
                f"Provide: 1) Ranking 2) What distinguishes the best 3) Recommendations"
            ),
        }]

        result = self.client.chat(system=SYSTEM_PROMPT, messages=messages, max_tokens=3000)

        self.tracker.log("result_analyzer", self.client.session_usage.input_tokens,
                         self.client.session_usage.output_tokens, detail="comparison")

        return {"table": str(table), "analysis": result["text"], "experiments": exps}

    def generate_report(self, topic: str = "") -> dict:
        """Generate a comprehensive research progress report."""
        console.print(Panel("Generating research progress report", title="Report Generator"))

        experiments = self.db.get_experiments()
        knowledge = self.db.get_knowledge()
        papers = self.db.get_recent_papers(limit=10)

        context = f"Total experiments: {len(experiments)}\n"
        context += f"Papers analyzed: {len(papers)}\n"
        context += f"Knowledge entries: {len(knowledge)}\n\n"

        if experiments:
            context += "Recent experiments:\n"
            for e in experiments[:5]:
                context += f"  - {e['name']}: {e.get('metrics', '{}')}\n"

        if topic:
            context += f"\nResearch focus: {topic}"

        messages = [{
            "role": "user",
            "content": (
                f"Generate a research progress report based on this data:\n\n{context}\n\n"
                f"Include: 1) Summary of progress 2) Key findings so far 3) "
                f"What's working and what isn't 4) Recommended next steps"
            ),
        }]

        result = self.client.chat(
            system="You are a research advisor. Write a concise, actionable progress report.",
            messages=messages, max_tokens=3000,
        )

        self.tracker.log("result_analyzer", self.client.session_usage.input_tokens,
                         self.client.session_usage.output_tokens, detail="progress_report")

        # Save report
        report_path = self.output_dir / "progress_report.md"
        report_path.write_text(result["text"], encoding="utf-8")

        console.print(Markdown(result["text"][:2000]))
        return {"report": result["text"], "path": str(report_path)}

    def _run_analysis(self, exp: dict, prompt_extra: str) -> dict:
        """Internal: run analysis on a single experiment."""
        exp_dir = exp.get("code_path", "")

        messages = [{
            "role": "user",
            "content": (
                f"Experiment: {exp['name']}\n"
                f"Description: {exp.get('description', '')}\n"
                f"Metrics: {exp.get('metrics', '{}')}\n"
                f"Output dir: {exp_dir}\n\n"
                f"{prompt_extra}"
            ),
        }]

        result = self.client.chat_with_tools(
            system=SYSTEM_PROMPT, messages=messages,
            tools=COMMON_TOOLS, tool_executor=execute_tool, max_tokens=4096,
        )

        self.tracker.log("result_analyzer", self.client.session_usage.input_tokens,
                         self.client.session_usage.output_tokens, detail=exp["name"])

        return {"analysis": result["text"], "rounds": result["rounds"]}
