"""Paper Writer - Draft, refine, and polish research paper sections."""

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from paperpilot.utils.api import ClaudeClient
from paperpilot.utils.token_tracker import TokenTracker

console = Console()

SECTION_SYSTEM_PROMPTS = {
    "abstract": """You are an expert NLP researcher writing an abstract for an academic paper.
Write a structured abstract (200-250 words) with: Background, Objective, Method, Results, Conclusion.
Be precise with numbers and metrics. Use academic tone.""",

    "introduction": """You are an expert NLP researcher writing an introduction section.
Structure: 1) Problem motivation 2) Related work gap 3) Our contribution 4) Paper organization.
Cite relevant work naturally. Establish clear research gap.""",

    "methodology": """You are an expert NLP researcher writing a methodology section.
Be precise and reproducible. Include: model architecture, training procedure, loss functions,
hyperparameters, and implementation details. Use mathematical notation where appropriate.""",

    "results": """You are an expert NLP researcher writing a results section.
Present results in a clear narrative. Reference tables and figures. Compare with baselines.
Include ablation studies. Be honest about limitations.""",

    "discussion": """You are an expert NLP researcher writing a discussion section.
Interpret results, compare with hypotheses, discuss implications, acknowledge limitations,
and suggest future work. Be balanced and nuanced.""",

    "related_work": """You are an expert NLP researcher writing a related work section.
Organize by themes, not chronologically. Clearly distinguish prior work from our contributions.
Cover: hierarchical classification methods, text representation, and label-aware approaches.""",
}


class PaperWriter:
    """Draft and refine research paper sections."""

    def __init__(self, db, tracker: TokenTracker, output_dir: str = "outputs"):
        self.client = ClaudeClient()
        self.db = db
        self.tracker = tracker
        self.output_dir = Path(output_dir)

    def draft_section(self, section: str, research_context: str,
                      key_findings: str = "", metrics: str = "",
                      references: str = "") -> dict:
        """Draft a paper section."""
        console.print(Panel(f"Drafting: {section}", title="Paper Writer", border_style="magenta"))

        system = SECTION_SYSTEM_PROMPTS.get(section, SECTION_SYSTEM_PROMPTS["abstract"])

        user_msg = f"Write the {section} section for our paper.\n\n"
        user_msg += f"Research context: {research_context}\n"
        if key_findings:
            user_msg += f"Key findings: {key_findings}\n"
        if metrics:
            user_msg += f"Experimental metrics: {metrics}\n"
        if references:
            user_msg += f"References to cite: {references}\n"

        # Pull knowledge from DB
        knowledge = self.db.get_knowledge(category="methodology")
        if knowledge:
            user_msg += "\nRelevant methodology notes:\n"
            for k in knowledge[:3]:
                user_msg += f"  - {k['title']}: {k['content'][:200]}\n"

        messages = [{"role": "user", "content": user_msg}]
        result = self.client.chat(system=system, messages=messages, max_tokens=4096)

        self.tracker.log("paper_writer", self.client.session_usage.input_tokens,
                         self.client.session_usage.output_tokens, detail=section)

        # Save draft
        draft_path = self.output_dir / f"draft_{section}.md"
        draft_path.write_text(result["text"], encoding="utf-8")

        console.print(Markdown(result["text"][:2000]))
        return {"section": section, "draft": result["text"], "path": str(draft_path)}

    def refine(self, section_text: str, feedback: str,
               style: str = "academic") -> dict:
        """Refine a section based on feedback."""
        console.print(Panel("Refining section", title="Paper Writer", border_style="magenta"))

        messages = [{
            "role": "user",
            "content": (
                f"Please refine this text based on the feedback.\n\n"
                f"Style: {style}\n\n"
                f"Current text:\n{section_text}\n\n"
                f"Feedback:\n{feedback}\n\n"
                f"Please output only the refined text, no explanations."
            ),
        }]

        result = self.client.chat(
            system="You are an expert academic editor. Improve text while maintaining the author's voice and meaning.",
            messages=messages, max_tokens=4096,
        )

        self.tracker.log("paper_writer", self.client.session_usage.input_tokens,
                         self.client.session_usage.output_tokens, detail="refine")

        return {"refined": result["text"]}

    def polish_full_paper(self, sections: dict[str, str]) -> dict:
        """Polish an entire paper for consistency and flow."""
        console.print(Panel("Polishing full paper", title="Paper Writer", border_style="magenta"))

        full_text = "\n\n".join(f"## {title}\n{content}" for title, content in sections.items())

        messages = [{
            "role": "user",
            "content": (
                f"Polish this full paper draft for:\n"
                f"1. Consistency in terminology and notation\n"
                f"2. Smooth transitions between sections\n"
                f"3. Remove redundancy\n"
                f"4. Ensure academic tone throughout\n"
                f"5. Fix any grammatical issues\n\n"
                f"Paper:\n{full_text[:30000]}"
            ),
        }]

        result = self.client.chat(
            system="You are a senior academic editor specializing in NLP/ML papers. Maintain the original structure while improving quality.",
            messages=messages, max_tokens=8192,
        )

        self.tracker.log("paper_writer", self.client.session_usage.input_tokens,
                         self.client.session_usage.output_tokens, detail="polish_full")

        polished_path = self.output_dir / "paper_polished.md"
        polished_path.write_text(result["text"], encoding="utf-8")

        return {"polished": result["text"], "path": str(polished_path)}
