#!/usr/bin/env python3
"""Build a public PDF copy of the Go-Stop LLM evaluation paper.

The repository does not assume a local TeX installation. This script creates a
stable PDF from the paper text and result tables with reportlab.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


REPO_URL = "https://github.com/parktaejun-dev/ai-test-with-gostop"
WEB_URL = "https://godori.dahanda.dev/dashboard/paper.html"
OUTPUT_PATH = Path("paper/gostop_ai_evaluation_paper.pdf")
PAPER_TITLE = "Risk-Sensitive LLM Evaluation in Four-Player Go-Stop: Remote-Model Panels, Scale Effects, and Policy Sensitivity"


def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text), style)


def code_block(text: str, style: ParagraphStyle) -> Preformatted:
    return Preformatted(text.rstrip(), style)


def result_table(headers: list[str], rows: list[list[str]], col_widths: list[float]) -> Table:
    table_data = [[paragraph(cell, STYLES["table_header"]) for cell in headers]]
    for row in rows:
        table_data.append([paragraph(cell, STYLES["table_cell"]) for cell in row])

    table = Table(table_data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#bdbdbd")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def add_section(story: list, title: str, body: list[str]) -> None:
    story.append(paragraph(title, STYLES["section"]))
    for item in body:
        story.append(paragraph(item, STYLES["body"]))
        story.append(Spacer(1, 0.06 * inch))
    story.append(Spacer(1, 0.08 * inch))


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(doc.leftMargin, 0.45 * inch, "Go-Stop AI Evaluation Paper")
    canvas.drawRightString(letter[0] - doc.rightMargin, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf() -> Path:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=letter,
        rightMargin=0.72 * inch,
        leftMargin=0.72 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.72 * inch,
        title=PAPER_TITLE,
        author="Go-Stop AI Evaluation Harness",
    )

    story: list = []
    story.append(
        paragraph(
            PAPER_TITLE,
            STYLES["title"],
        )
    )
    story.append(paragraph("Go-Stop AI Evaluation Harness", STYLES["subtitle"]))
    story.append(paragraph("Public GitHub edition - April 2026", STYLES["subtitle"]))
    story.append(Spacer(1, 0.18 * inch))

    add_section(
        story,
        "Abstract",
        [
            "We evaluate fixed-policy large language model play in four-player Go-Stop, a Korean card game that compresses hidden information, stochastic card draws, combinatorial scoring, multi-agent interaction, and risk-sensitive stop-or-continue decisions into short episodes. The study asks whether observed performance across a Qwen-labeled remote-model panel is monotone in nominal parameter scale, and whether cross-family differences are visible in a rate-limited, roughly same-scale NVIDIA Build panel.",
            "The Qwen panel compares four DashScope models spanning 30B, 122B, 397B, and 480B total parameters. The NVIDIA Build panel compares four roughly 100B-122B models from Qwen, Mistral, Nemotron, and Stockmark. Each main panel yields 48 session samples per model and 192 model-session observations. Supplementary screens show that small models can achieve positive mean profit under restricted settings and that policy framing changes performance in model-specific ways.",
        ],
    )

    add_section(
        story,
        "1. Introduction",
        [
            "This paper is about evaluation, not training. We study fixed language-model policies in four-player Go-Stop, where agents choose among legal game actions under partial information, stochastic deals, seat-order effects, and heavy-tailed settlements.",
            "Go-Stop is useful for this purpose because it is a compact stochastic decision problem. A player must infer value from visible cards while reasoning over hidden hands and the draw pile; choose local tactical actions that change future card availability; decide whether to continue after scoring; and manage the downside risk created by multipliers and opponent responses.",
            "RQ1: Why is Go-Stop a plausible environment for evaluating risk-sensitive sequential decision making by LLM agents? RQ2: In a Qwen-labeled DashScope panel, is observed Go-Stop performance monotone in nominal parameter scale? RQ3: In a rate-limited NVIDIA Build panel of roughly same-scale models, are cross-family differences visible in descriptive profit and risk summaries? RQ4: In supplementary screens, do small models and prompt-policy variants show measurable but model-specific differences?",
            "Beyond game AI, this evaluation logic is relevant to industrial decision systems that repeatedly act under uncertainty. Real-time advertising bidding and campaign budget pacing, for example, require agents to decide whether to spend, wait, or adjust bids under uncertain conversion probabilities and competitive market conditions.",
        ],
    )

    add_section(
        story,
        "2. Go-Stop as a Stochastic Decision Environment",
        [
            "Go-Stop is a Korean fishing-style card game played with Hanafuda cards. In each turn, a player chooses from legal actions based on a public table state, a private hand, and uncertain future draws. Scoring depends on card categories and combinations, and the Go/Stop decision creates a risk-sensitive stopping problem.",
            "A risk-neutral action can be represented as argmax over legal actions of expected terminal utility conditional on public state, hidden cards, and opponent policies. The practical policy problem is harder because hidden card distributions, future draws, and opponent responses are only partially observed.",
            "The evaluation therefore reports mean profit together with CVaR_0.05, ruin probability, win rate, and sample count. CVaR is used as a descriptive lower-tail measure because a policy that wins often can still be weak if its losses concentrate in rare but severe outcomes.",
        ],
    )

    add_section(
        story,
        "3. Methods",
        [
            "The harness evaluates fixed policies only. There is no online learning, self-play training, or log-based policy update. Each agent receives a public game-state serialization and must return one legal action index.",
            "Remote models are called through OpenAI-compatible chat-completion APIs. The fixed policy prompt asks the model to choose one legal action index only, optimize long-run profit with risk control, and avoid explanation. Invalid, unparsable, or out-of-range responses fall back to the first legal action.",
            "The Qwen study uses Alibaba DashScope with all 24 seat permutations repeated twice. Each session has a two-hand horizon. The NVIDIA study uses NVIDIA Build NIM with the same seat enumeration and repetition, but a one-hand horizon and max_remote_calls_per_agent=1 because rate limits were binding.",
            "Supplementary screens add a small-model NVIDIA panel and four policy framings - balanced, analytic, conservative, and aggressive - for Qwen small models and NVIDIA roughly same-scale models. These screens have 24 samples per model-policy cell and are exploratory.",
        ],
    )

    story.append(paragraph("4. Results", STYLES["section"]))
    story.append(
        paragraph(
            "RQ2 is descriptively negative in this panel. The highest Qwen result is the 397B model, not the largest 480B model. Because the panel mixes Qwen3.5 and Qwen Coder variants, it does not isolate a pure scale effect.",
            STYLES["body"],
        )
    )
    story.append(Spacer(1, 0.08 * inch))
    story.append(
        result_table(
            ["Model", "Total params", "Active params", "Mean profit", "CVaR 5%", "Win rate"],
            [
                ["qwen3.5-397b-a17b", "397B", "17B", "996.25", "-1850.08", "0.3021"],
                ["qwen3.5-122b-a10b", "122B", "10B", "-51.75", "-4145.33", "0.3542"],
                ["qwen3-coder-480b-a35b-instruct", "480B", "35B", "-198.92", "-5084.75", "0.2396"],
                ["qwen3-coder-30b-a3b-instruct", "30B", "3B", "-745.58", "-5269.25", "0.1042"],
            ],
            [2.25 * inch, 0.85 * inch, 0.85 * inch, 0.9 * inch, 0.9 * inch, 0.75 * inch],
        )
    )
    story.append(Spacer(1, 0.18 * inch))
    story.append(
        paragraph(
            "RQ3 shows visible descriptive differences under the constrained NVIDIA panel. Nemotron has the highest mean profit and least severe empirical CVaR among the roughly same-scale models.",
            STYLES["body"],
        )
    )
    story.append(Spacer(1, 0.08 * inch))
    story.append(
        result_table(
            ["Model", "Scale", "Mean profit", "CVaR 5%", "Win rate"],
            [
                ["nvidia/nemotron-3-super-120b-a12b", "~120B", "500.65", "-1384.17", "0.2708"],
                ["mistralai/mistral-small-4-119b-2603", "~119B", "-73.19", "-4150.00", "0.2917"],
                ["qwen/qwen3.5-122b-a10b", "122B", "-172.85", "-3350.42", "0.1875"],
                ["stockmark/stockmark-2-100b-instruct", "~100B", "-254.60", "-4267.08", "0.2500"],
            ],
            [2.9 * inch, 0.75 * inch, 0.95 * inch, 0.95 * inch, 0.75 * inch],
        )
    )
    story.append(Spacer(1, 0.18 * inch))

    story.append(
        paragraph(
            "RQ4 is supported as exploratory evidence. In the NVIDIA small-model screen, Granite 3B is the only model with clearly positive mean profit. In the Qwen small-model policy screen, the leading model changes with policy framing: qwen3-4b leads under balanced and analytic framings, qwen3-8b under conservative framing, and qwen3-14b under aggressive framing.",
            STYLES["body"],
        )
    )
    story.append(Spacer(1, 0.08 * inch))
    story.append(
        result_table(
            ["Small NVIDIA model", "Scale", "Mean profit", "CVaR 5%", "Win rate"],
            [
                ["ibm/granite-3.0-3b-a800m-instruct", "3B/A800M", "381.25", "-1966.67", "0.3125"],
                ["meta/llama-3.2-1b-instruct", "1B", "-20.83", "-2083.33", "0.2708"],
                ["google/gemma-2-2b-it", "2B", "-68.75", "-3833.33", "0.2500"],
                ["microsoft/phi-4-mini-instruct", "mini", "-291.67", "-3916.67", "0.1667"],
            ],
            [2.85 * inch, 0.7 * inch, 0.95 * inch, 0.95 * inch, 0.75 * inch],
        )
    )
    story.append(Spacer(1, 0.16 * inch))
    story.append(
        result_table(
            ["Qwen policy", "Top model", "Top mean", "Top CVaR 5%"],
            [
                ["Balanced", "qwen3-4b", "224.88", "-1166.67"],
                ["Analytic", "qwen3-4b", "412.33", "-2566.83"],
                ["Conservative", "qwen3-8b", "238.08", "-1301.67"],
                ["Aggressive", "qwen3-14b", "254.08", "-1284.33"],
            ],
            [1.0 * inch, 2.1 * inch, 0.95 * inch, 0.95 * inch],
        )
    )
    story.append(Spacer(1, 0.18 * inch))

    add_section(
        story,
        "5. Discussion",
        [
            "The main panels and supplementary screens agree on a bounded point: fixed-policy Go-Stop performance in this harness is not fully summarized by nominal parameter count. Model family, prompt-policy framing, serving constraints, and tail-risk behavior jointly shape the observed results.",
            "These outcomes fit the game domain. Go-Stop requires local tactical choices, risk control, settlement awareness, and disciplined JSON action selection. General language-model scale can help, but the observed policy is also shaped by model specialization, instruction following, decoding behavior, provider-level serving constraints, fallback behavior, and policy framing.",
        ],
    )

    add_section(
        story,
        "6. Limitations",
        [
            "The model panels are convenience samples from currently callable remote APIs. The Qwen scale panel mixes Qwen3.5 and Qwen Coder variants, so parameter scale is confounded with model specialization.",
            "The NVIDIA panel is constrained by rate limits and uses max_remote_calls_per_agent=1. It measures constrained first-decision-policy behavior more than full-game autonomous play. The horizons are short: two hands for Qwen and one hand for NVIDIA.",
            "Each main-panel model has 48 session samples, below the repository's 100-session threshold for stable CVaR inference. Supplementary policy screens have 24 samples per model-policy cell and one layout repetition. These runs are enough for descriptive summaries, but not for universal model ranking claims.",
        ],
    )

    add_section(
        story,
        "7. Conclusion",
        [
            "In a reproducible four-player Go-Stop evaluation harness, the observed Qwen panel is not monotone in nominal parameter scale, and the constrained NVIDIA Build panel shows visible cross-family differences in descriptive profit and empirical tail summaries. Supplementary screens show that selected small models can achieve positive mean profit under restricted settings and that prompt-policy effects are model-specific.",
            "The main implication is methodological: multi-agent, risk-sensitive card-game evaluation should report model identity, parameter scale, family, policy framing, serving constraints, fallback policy, and tail-risk metrics together rather than reducing model quality to size alone.",
        ],
    )

    add_section(
        story,
        "Code and Artifact Availability",
        [
            f"Repository: {REPO_URL}",
            f"Web paper page: {WEB_URL}",
            "Manuscript source: paper/arxiv_main.tex",
            "Qwen result bundle: results/paper_qwen_4model_param_2h_2rep",
            "NVIDIA result bundle: results/paper_nvidia_120b_4model_family_1h_2rep_budget1",
            "NVIDIA small-model bundle: results/tiny_nvidia_4model_1h_2rep_budget1_20260425_075542",
            "Policy screens: results/policy_screen_qwen_tiny_*_20260425_102731 and results/policy_screen_nvidia_*_20260425_075542",
            "Compact result summary: paper/remote_model_results.md",
        ],
    )

    story.append(paragraph("Reproducibility Commands", STYLES["section"]))
    story.append(
        code_block(
            """
python3 scripts/run_dashscope_qwen_parameter_sweep.py \\
  --session-hands 2 \\
  --layout-repetitions 2 \\
  --remote-eval-hands 2 \\
  --decoding max_tokens=64 \\
  --decoding temperature=0 \\
  --decoding enable_thinking=false \\
  --output-dir results/paper_qwen_4model_param_2h_2rep

python3 scripts/run_nvidia_same_size_family_eval.py \\
  --session-hands 1 \\
  --layout-repetitions 2 \\
  --remote-eval-hands 1 \\
  --max-remote-calls-per-agent 1 \\
  --decoding max_tokens=64 \\
  --decoding temperature=0 \\
  --output-dir results/paper_nvidia_120b_4model_family_1h_2rep_budget1
""",
            STYLES["code"],
        )
    )
    story.append(Spacer(1, 0.12 * inch))
    story.append(
        paragraph(
            "References are maintained in paper/refs.bib. The TeX manuscript remains the canonical source for citation keys and bibliography style.",
            STYLES["body"],
        )
    )

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return OUTPUT_PATH


BASE_STYLES = getSampleStyleSheet()
STYLES = {
    "title": ParagraphStyle(
        "PublicPaperTitle",
        parent=BASE_STYLES["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=8,
    ),
    "subtitle": ParagraphStyle(
        "PublicPaperSubtitle",
        parent=BASE_STYLES["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#333333"),
    ),
    "section": ParagraphStyle(
        "PublicPaperSection",
        parent=BASE_STYLES["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=TA_LEFT,
        spaceBefore=9,
        spaceAfter=5,
    ),
    "body": ParagraphStyle(
        "PublicPaperBody",
        parent=BASE_STYLES["BodyText"],
        fontName="Helvetica",
        fontSize=9.3,
        leading=12.3,
        alignment=TA_LEFT,
        spaceAfter=2,
    ),
    "table_header": ParagraphStyle(
        "PublicPaperTableHeader",
        parent=BASE_STYLES["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=7.6,
        leading=9.2,
    ),
    "table_cell": ParagraphStyle(
        "PublicPaperTableCell",
        parent=BASE_STYLES["BodyText"],
        fontName="Helvetica",
        fontSize=7.3,
        leading=8.7,
    ),
    "code": ParagraphStyle(
        "PublicPaperCode",
        parent=BASE_STYLES["Code"],
        fontName="Courier",
        fontSize=7.4,
        leading=9.2,
        leftIndent=8,
        borderPadding=5,
        backColor=colors.HexColor("#f4f4f4"),
    ),
}


if __name__ == "__main__":
    output = build_pdf()
    print(output)
