"""PaperPilot CLI - Claude-Powered NLP Research Assistant."""

import sys

import click
from rich.console import Console
from rich.panel import Panel

from paperpilot.utils.database import Database
from paperpilot.utils.token_tracker import TokenTracker

console = Console()


@click.group()
@click.option("--db", default="paperpilot.db", help="Database path")
@click.pass_context
def cli(ctx, db):
    """PaperPilot - Claude-Powered NLP Research Assistant."""
    ctx.ensure_object(dict)
    ctx.obj["db"] = Database(db)
    ctx.obj["tracker"] = TokenTracker()


@cli.command()
@click.argument("paper_path")
@click.option("--context", "-c", default="", help="Research context")
@click.pass_context
def paper(ctx, paper_path, context):
    """Analyze a research paper."""
    from paperpilot.modules.paper_analyzer import PaperAnalyzer
    analyzer = PaperAnalyzer(ctx.obj["db"], ctx.obj["tracker"])
    result = analyzer.analyze(paper_path, context)
    console.print(f"\n[green]Analysis complete. Rounds: {result['rounds']}[/green]")


@cli.command()
@click.argument("goal")
@click.option("--data", "-d", default="", help="Dataset path")
@click.option("--name", "-n", default="", help="Experiment name")
@click.option("--output", "-o", default="outputs", help="Output directory")
@click.pass_context
def experiment(ctx, goal, data, name, output):
    """Run an ML experiment."""
    from paperpilot.modules.experiment_runner import ExperimentRunner
    runner = ExperimentRunner(ctx.obj["db"], ctx.obj["tracker"], output)
    result = runner.run(goal, data_path=data, exp_name=name)
    console.print(f"\n[green]Experiment '{result['name']}' done. ID: {result['experiment_id']}[/green]")


@cli.command()
@click.option("--ids", default="", help="Comma-separated experiment IDs to compare")
@click.pass_context
def compare(ctx, ids):
    """Compare experiment results."""
    from paperpilot.modules.result_analyzer import ResultAnalyzer
    analyzer = ResultAnalyzer(ctx.obj["db"], ctx.obj["tracker"])
    exp_ids = [int(x.strip()) for x in ids.split(",") if x.strip()] if ids else None
    result = analyzer.compare_experiments(exp_ids)
    console.print(f"\n[green]Comparison done.[/green]")


@cli.command()
@click.argument("section", type=click.Choice(
    ["abstract", "introduction", "methodology", "results", "discussion", "related_work"]))
@click.argument("context")
@click.option("--findings", "-f", default="", help="Key findings")
@click.option("--metrics", "-m", default="", help="Experimental metrics")
@click.pass_context
def write(ctx, section, context, findings, metrics):
    """Draft a paper section."""
    from paperpilot.modules.paper_writer import PaperWriter
    writer = PaperWriter(ctx.obj["db"], ctx.obj["tracker"])
    result = writer.draft_section(section, context, key_findings=findings, metrics=metrics)
    console.print(f"\n[green]Draft saved to: {result['path']}[/green]")


@cli.command()
@click.pass_context
def status(ctx):
    """Show research dashboard and token usage."""
    from paperpilot.modules.progress_tracker import ProgressTracker
    tracker = ProgressTracker(ctx.obj["db"], ctx.obj["tracker"])
    tracker.dashboard()
    ctx.obj["tracker"].print_report()


@cli.command()
@click.option("--topic", "-t", default="", help="Research topic")
@click.pass_context
def suggest(ctx, topic):
    """Get AI-suggested next research steps."""
    from paperpilot.modules.progress_tracker import ProgressTracker
    tracker = ProgressTracker(ctx.obj["db"], ctx.obj["tracker"])
    if not topic:
        topic = "NLP hierarchical text classification research"
    result = tracker.suggest_next_steps(topic)
    console.print(Panel(result["suggestions"], title="Suggested Next Steps", border_style="green"))


@cli.command()
@click.argument("title")
@click.argument("content")
@click.option("--category", "-c", default="general")
@click.pass_context
def insight(ctx, title, content, category):
    """Add a knowledge base entry."""
    from paperpilot.modules.progress_tracker import ProgressTracker
    tracker = ProgressTracker(ctx.obj["db"], ctx.obj["tracker"])
    tracker.add_insight(title, content, category)


if __name__ == "__main__":
    cli()
