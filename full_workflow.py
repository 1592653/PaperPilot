"""
Example: Full PaperPilot research workflow.

Demonstrates the complete research cycle:
1. Analyze papers
2. Run experiments
3. Analyze results
4. Draft paper sections

Usage:
    python examples/full_workflow.py

Requires: ANTHROPIC_API_KEY in .env
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paperpilot.utils.database import Database
from paperpilot.utils.token_tracker import TokenTracker
from paperpilot.modules.paper_analyzer import PaperAnalyzer
from paperpilot.modules.experiment_runner import ExperimentRunner
from paperpilot.modules.result_analyzer import ResultAnalyzer
from paperpilot.modules.paper_writer import PaperWriter
from paperpilot.modules.progress_tracker import ProgressTracker


def main():
    db = Database("outputs/demo/paperpilot.db")
    tracker = TokenTracker("outputs/demo")

    research_goal = "Improve hierarchical text classification on biomedical literature"
    data_path = "outputs/demo/data/pubmed_sample.csv"

    print("=" * 60)
    print("PaperPilot - Full Research Workflow Demo")
    print("=" * 60)

    # Step 1: Set up context
    print("\n[Step 1] Setting up research context...")
    pt = ProgressTracker(db, tracker)
    pt.add_insight(
        title="Research Direction",
        content="Focus on hierarchical text classification with label-aware attention for PubMed biomedical literature.",
        category="methodology",
    )

    # Step 2: Run experiments
    print("\n[Step 2] Running experiments...")
    runner = ExperimentRunner(db, tracker, "outputs/demo")

    # Experiment A: Flat baseline
    result_a = runner.run(
        experiment_goal=(
            "Create a synthetic multi-class text dataset with 7 categories "
            "(Biology, Physics, Chemistry, Software, Hardware, Clinical, Pharmacy), "
            "50 samples each. Train a TF-IDF + Logistic Regression baseline. "
            "Report accuracy, macro-F1, and per-class F1."
        ),
        exp_name="baseline_flat",
    )

    # Experiment B: Hierarchical approach
    result_b = runner.run(
        experiment_goal=(
            "Using the same dataset from outputs/demo/baseline_flat/data, "
            "implement a hierarchical classifier that uses the 3-level label tree "
            "(Science:Bio/Phys/Chem, Tech:SW/HW, Med:Pharma/Clinical). "
            "Use label embeddings to guide classification. "
            "Report accuracy, macro-F1 at each hierarchy level."
        ),
        exp_name="hier_classifier",
    )

    # Step 3: Analyze results
    print("\n[Step 3] Analyzing results...")
    analyzer = ResultAnalyzer(db, tracker, "outputs/demo")
    comparison = analyzer.compare_experiments()

    # Step 4: Draft paper abstract
    print("\n[Step 4] Drafting paper abstract...")
    writer = PaperWriter(db, tracker, "outputs/demo")
    abstract = writer.draft_section(
        section="abstract",
        research_context=research_goal,
        key_findings=(
            "Hierarchical classifier outperforms flat baseline by 3.2% in macro-F1. "
            "Label-aware attention helps especially on rare classes."
        ),
        metrics=str(result_b.get("metrics", {})),
    )

    # Step 5: Summary
    print("\n[Step 5] Research progress dashboard")
    pt.dashboard()
    tracker.print_report()

    print("\n" + "=" * 60)
    print("Full workflow demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
