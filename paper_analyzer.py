"""Paper Analyzer - Read, summarize, and extract insights from research papers."""

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from paperpilot.utils.api import ClaudeClient
from paperpilot.utils.tools import COMMON_TOOLS, execute_tool
from paperpilot.utils.token_tracker import TokenTracker

console = Console()

SYSTEM_PROMPT = """You are an expert NLP research paper analyst. Your job is to thoroughly analyze research papers and extract structured information.

When given a paper (as text, PDF path, or URL), you should:

1. **Read the full paper** using available tools (read_file for local files)
2. **Extract structured information:**
   - Title, Authors, Venue/Source
   - Problem statement and motivation
   - Key contributions (numbered list)
   - Methodology description
   - Key results and metrics
   - Datasets used
   - Limitations mentioned
   - Future work directions
3. **Critical analysis:**
   - Strengths of the approach
   - Weaknesses or gaps
   - How it compares to prior work
   - Potential improvements
4. **Relevance assessment:** How this paper relates to hierarchical text classification or NLP research

Output a structured markdown report. Be thorough but concise.
"""


class PaperAnalyzer:
    """Analyze research papers and extract structured insights."""

    def __init__(self, db, tracker: TokenTracker):
        self.client = ClaudeClient()
        self.db = db
        self.tracker = tracker

    def analyze(self, paper_path: str, context: str = "") -> dict:
        """Analyze a paper from a file path."""
        console.print(Panel(f"Analyzing: {paper_path}", title="Paper Analyzer", border_style="cyan"))

        # First, read the file to provide to Claude
        paper_content = ""
        try:
            from pathlib import Path
            p = Path(paper_path)
            if p.suffix == ".pdf":
                paper_content = f"[PDF file at: {paper_path}]\nPlease read this PDF file."
            else:
                paper_content = p.read_text(encoding="utf-8")[:60000]
        except Exception as e:
            paper_content = f"[Error reading file: {e}]"

        user_msg = f"Please analyze this research paper:\n\n{paper_content}"
        if context:
            user_msg += f"\n\nAdditional context: {context}"

        messages = [{"role": "user", "content": user_msg}]
        result = self.client.chat_with_tools(
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=COMMON_TOOLS,
            tool_executor=execute_tool,
            max_tokens=4096,
        )

        # Track tokens
        self.tracker.log("paper_analyzer", self.client.session_usage.input_tokens,
                         self.client.session_usage.output_tokens, detail=paper_path)

        # Save to database
        self.db.add_paper(
            title=self._extract_field(result["text"], "Title"),
            key_findings=result["text"][:2000],
            source=paper_path,
            tags=["auto-analyzed"],
        )

        console.print(Markdown(result["text"][:3000]))
        return {"analysis": result["text"], "rounds": result["rounds"]}

    def batch_analyze(self, paper_paths: list[str], research_context: str = "") -> dict:
        """Analyze multiple papers and produce a comparative summary."""
        console.print(Panel(
            f"Batch analyzing {len(paper_paths)} papers",
            title="Paper Analyzer", border_style="cyan",
        ))

        analyses = []
        for path in paper_paths:
            result = self.analyze(path, context=research_context)
            analyses.append({"path": path, "analysis": result["analysis"]})

        # Generate comparative summary
        summaries = "\n\n---\n\n".join(
            f"Paper: {a['path']}\n{a['analysis'][:1000]}" for a in analyses
        )
        messages = [{
            "role": "user",
            "content": (
                f"I've analyzed {len(analyses)} papers. Please create a comparative summary:\n\n"
                f"{summaries}\n\n"
                f"Research context: {research_context}\n\n"
                f"Please provide:\n1. Common themes\n2. Key differences\n"
                f"3. Research gaps\n4. Suggested research directions"
            ),
        }]

        summary_result = self.client.chat(
            system="You are an expert NLP researcher. Synthesize findings from multiple papers into actionable insights.",
            messages=messages,
            max_tokens=4096,
        )

        self.tracker.log("paper_analyzer", self.client.session_usage.input_tokens,
                         self.client.session_usage.output_tokens, detail="batch_comparative")

        return {
            "individual_analyses": analyses,
            "comparative_summary": summary_result["text"],
        }

    def _extract_field(self, text: str, field: str) -> str:
        """Best-effort extraction of a field from analysis text."""
        for line in text.split("\n"):
            if field.lower() in line.lower() and ":" in line:
                return line.split(":", 1)[1].strip()[:200]
        return "Untitled"
