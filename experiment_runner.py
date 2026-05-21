"""Experiment Runner - Generate, execute, and debug ML experiment code."""

from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from paperpilot.utils.api import ClaudeClient
from paperpilot.utils.tools import COMMON_TOOLS, execute_tool
from paperpilot.utils.token_tracker import TokenTracker

console = Console()

SYSTEM_PROMPT = """You are an expert ML/NLP experiment engineer. Your job is to write and execute experiment code.

Capabilities:
- Generate PyTorch, scikit-learn, or HuggingFace training code
- Design model architectures (especially for text classification)
- Handle data loading, preprocessing, training, and evaluation
- Debug errors automatically: if code fails, read the error, fix it, and retry

Workflow when asked to run an experiment:
1. Understand the dataset (read files, check format)
2. Write complete, runnable Python code
3. Save code to a file using write_file
4. Execute it using run_python
5. If it fails, read the error, fix the code, and retry (up to 3 times)
6. Report final metrics

For hierarchical text classification, consider:
- Multi-level label structures (label hierarchy)
- Label-aware attention mechanisms
- Hierarchical loss functions (level-wise + global)
- Contrastive learning between label levels
- Both flat and hierarchical baselines for comparison

Always save experiment code to the output directory so it's reproducible.
Report results in a structured format:
```
## Experiment Results
- Model: [name]
- Dataset: [name]
- Metrics: [key=value pairs]
- Training time: [duration]
- Code saved to: [path]
```
"""


class ExperimentRunner:
    """Generate and execute NLP experiments with automatic error recovery."""

    def __init__(self, db, tracker: TokenTracker, output_dir: str = "outputs"):
        self.client = ClaudeClient()
        self.db = db
        self.tracker = tracker
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(self, experiment_goal: str, data_path: str = "",
            constraints: str = "", exp_name: str = "") -> dict:
        """Generate and run an experiment."""
        if not exp_name:
            exp_name = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        exp_dir = self.output_dir / exp_name
        exp_dir.mkdir(parents=True, exist_ok=True)

        console.print(Panel(
            f"Experiment: {exp_name}\nGoal: {experiment_goal}\nData: {data_path}",
            title="Experiment Runner", border_style="green",
        ))

        # Register experiment in DB
        exp_id = self.db.add_experiment(
            name=exp_name, description=experiment_goal,
            dataset=data_path, status="running",
        )

        # Build user prompt
        user_msg = f"Experiment goal: {experiment_goal}\n"
        if data_path:
            user_msg += f"Dataset path: {data_path}\n"
        if constraints:
            user_msg += f"Constraints: {constraints}\n"
        user_msg += f"Output directory: {exp_dir}\n"
        user_msg += "\nPlease implement and run this experiment."

        messages = [{"role": "user", "content": user_msg}]
        result = self.client.chat_with_tools(
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=COMMON_TOOLS,
            tool_executor=execute_tool,
            max_tokens=8192,
            max_rounds=15,
        )

        # Track tokens
        self.tracker.log("experiment_runner", self.client.session_usage.input_tokens,
                         self.client.session_usage.output_tokens, detail=exp_name)

        # Update DB
        metrics = self._extract_metrics(result["text"])
        self.db.update_experiment(
            exp_id, status="completed", metrics=metrics,
            code_path=str(exp_dir), notes=result["text"][:2000],
        )

        console.print(f"\n[green]Experiment {exp_name} completed.[/green]")
        return {
            "experiment_id": exp_id,
            "name": exp_name,
            "output_dir": str(exp_dir),
            "result_text": result["text"],
            "metrics": metrics,
            "rounds": result["rounds"],
        }

    def compare_baselines(self, data_path: str, task_description: str) -> dict:
        """Run multiple baseline models for comparison."""
        console.print(Panel("Running baseline comparison experiments", title="Baseline Comparison"))

        baselines = [
            ("tfidf_logreg", "TF-IDF + Logistic Regression baseline"),
            ("bert_flat", "BERT-based flat classifier"),
            ("hier_classifier", "Hierarchical-aware classifier"),
        ]

        results = []
        for name, desc in baselines:
            result = self.run(
                experiment_goal=f"{desc}: {task_description}",
                data_path=data_path,
                exp_name=f"baseline_{name}",
            )
            results.append(result)

        return {"baselines": results}

    def _extract_metrics(self, text: str) -> dict:
        """Extract metric key-value pairs from experiment output."""
        metrics = {}
        for line in text.split("\n"):
            line = line.strip()
            # Look for patterns like "Accuracy: 0.85" or "F1 = 0.72"
            for sep in [":", "="]:
                if sep in line:
                    parts = line.split(sep, 1)
                    key = parts[0].strip().lower().replace(" ", "_")
                    val = parts[1].strip().split()[0] if len(parts) > 1 else ""
                    try:
                        metrics[key] = float(val)
                    except (ValueError, IndexError):
                        pass
        return metrics
