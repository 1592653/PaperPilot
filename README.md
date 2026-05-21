# PaperPilot

**Claude-Powered NLP Research Assistant** | Claude 驱动的 NLP 研究助手

PaperPilot 是一个深度整合 Claude API 的 NLP 研究工作流工具。它不是通用 Agent 框架，而是为 NLP 研究者日常使用设计的专用工具——从论文阅读、实验执行、结果分析到论文写作，覆盖完整研究周期。

## Why PaperPilot?

在 NLP 研究中，一个典型的工作日：
- 📖 读 3-5 篇论文，每篇需要反复精读、对比、做笔记
- 🧪 写/调试实验代码，反复"改→跑→看→改"
- 📊 分析实验结果，对比 SOTA，生成可视化
- ✍️ 写论文段落，从实验数据到学术语言的转换

**这些工作每天消耗 300-800 万 Token**，PaperPilot 让这个过程更高效、更系统化。

## Features

| Module | Function | Token/Day |
|--------|----------|-----------|
| **PaperAnalyzer** | 论文结构化分析、批量对比、研究空白识别 | 50-150万 |
| **ExperimentRunner** | 自动生成训练代码、执行实验、自动排错重试 | 100-300万 |
| **ResultAnalyzer** | 实验结果对比、可视化、SOTA 对比报告 | 30-80万 |
| **PaperWriter** | 论文章节草稿生成、润色、一致性检查 | 50-150万 |
| **ProgressTracker** | 研究进度追踪、知识图谱积累、下一步建议 | 20-50万 |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI (click)                          │
│  paperpilot paper | experiment | compare | write | status   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │PaperAnalyzer │ │Experiment    │ │ResultAnalyzer│        │
│  │              │ │Runner        │ │              │        │
│  │ • 论文分析   │ │ • 代码生成   │ │ • 指标对比   │        │
│  │ • 批量对比   │ │ • 自动执行   │ │ • 可视化     │        │
│  │ • 研究空白   │ │ • 错误恢复   │ │ • SOTA对比   │        │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘        │
│         │                │                │                 │
│  ┌──────┴───────┐ ┌──────┴───────┐                        │
│  │PaperWriter   │ │Progress      │                        │
│  │              │ │Tracker       │                        │
│  │ • 章节草稿   │ │ • 知识图谱   │                        │
│  │ • 润色修订   │ │ • 进度看板   │                        │
│  │ • 全文一致   │ │ • 智能建议   │                        │
│  └──────────────┘ └──────────────┘                        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  ClaudeClient (Anthropic API + prompt caching)              │
│  TokenTracker (persistent JSONL logging)                    │
│  Database (SQLite: papers / experiments / knowledge)         │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# 1. Install
git clone https://github.com/your-username/paperpilot.git
cd paperpilot
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Add your ANTHROPIC_API_KEY

# 3. Use CLI
python main.py paper path/to/paper.pdf          # Analyze a paper
python main.py experiment "train classifier" -d data.csv  # Run experiment
python main.py compare --ids 1,2,3              # Compare experiments
python main.py write abstract "our research..."  # Draft abstract
python main.py status                            # Dashboard + token usage

# 4. Full workflow demo
python examples/full_workflow.py
```

## Usage Examples

### Daily Research Workflow

```python
from paperpilot.utils.database import Database
from paperpilot.utils.token_tracker import TokenTracker
from paperpilot.modules.experiment_runner import ExperimentRunner
from paperpilot.modules.result_analyzer import ResultAnalyzer

db = Database()
tracker = TokenTracker()

# Morning: run experiments
runner = ExperimentRunner(db, tracker)
runner.run("Hierarchical classifier on PubMed data", data_path="data/pubmed.csv")

# Afternoon: analyze results
analyzer = ResultAnalyzer(db, tracker)
analyzer.compare_experiments()  # auto-compare all recent experiments

# End of day: check usage
tracker.print_report()
# === Token Usage Report ===
# Today       47   3,200,000   1,800,000   500,000   5,500,000
```

### Programmatic API

```python
from paperpilot.modules.paper_writer import PaperWriter

writer = PaperWriter(db, tracker)
writer.draft_section("methodology", "hierarchical text classification with label attention")
writer.refine(draft_text, "Make the loss function description more precise")
```

## Key Design Decisions

1. **Not a generic framework**: PaperPilot is purpose-built for NLP research, not a reusable "multi-agent platform"
2. **Persistent state**: SQLite database tracks experiments, papers, and knowledge across sessions
3. **Token transparency**: Every API call is logged with module attribution
4. **Error recovery**: ExperimentRunner automatically retries failed code (up to 3 attempts)
5. **Prompt caching**: System prompts use Anthropic's ephemeral cache to reduce costs

## Daily Token Consumption

A typical research day with PaperPilot:

| Activity | Calls | Tokens |
|----------|-------|--------|
| Read 3 papers | ~15 | ~1.5M |
| Run 2 experiments | ~20 | ~3M |
| Analyze results | ~8 | ~800K |
| Write paper sections | ~10 | ~1M |
| Progress tracking | ~3 | ~300K |
| **Daily Total** | **~56** | **~6.6M** |

## Project Structure

```
paperpilot/
├── modules/
│   ├── paper_analyzer.py    # 论文分析
│   ├── experiment_runner.py # 实验执行
│   ├── result_analyzer.py   # 结果分析
│   ├── paper_writer.py      # 论文写作
│   └── progress_tracker.py  # 进度追踪
├── utils/
│   ├── api.py               # Claude API 客户端
│   ├── token_tracker.py     # Token 使用追踪
│   ├── database.py          # SQLite 持久化
│   └── tools.py             # Agent 工具定义
main.py                       # CLI 入口
```

## License

MIT
