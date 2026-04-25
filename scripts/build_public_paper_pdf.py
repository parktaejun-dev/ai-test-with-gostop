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
    PageBreak,
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
        title="Parameter Scale and Model-Family Effects in Fixed-Policy LLM Play for Four-Player Go-Stop",
        author="Go-Stop AI Evaluation Harness",
    )

    story: list = []
    story.append(
        paragraph(
            "Parameter Scale and Model-Family Effects in Fixed-Policy LLM Play for Four-Player Go-Stop",
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
            "We evaluate fixed-policy large language model play in four-player Go-Stop, a Korean card game with stochastic deals, seat-order nuisance effects, multi-agent interaction, and risk-sensitive payoffs. The study asks whether performance within a Qwen model family increases monotonically with parameter scale, and whether model family still matters when models are compared at roughly similar parameter scale.",
            "The Qwen panel compares four DashScope models spanning 30B, 122B, 397B, and 480B total parameters. The NVIDIA Build panel compares four roughly 100B-122B models from Qwen, Mistral, Nemotron, and Stockmark. Each panel yields 48 session samples per model and 192 model-session observations. The results suggest that Go-Stop policy quality is not explained by parameter count alone.",
        ],
    )

    add_section(
        story,
        "1. Introduction",
        [
            "This paper is about evaluation, not training. We study fixed language-model policies in four-player Go-Stop, where agents choose among legal game actions under partial information, stochastic deals, seat-order effects, and heavy-tailed settlements.",
            "The motivating claim is simple: model scale is an incomplete proxy for game-playing policy quality. A multi-agent, risk-sensitive game can expose differences in action selection, risk tolerance, and instruction following that are not captured by parameter count alone.",
            "RQ1: Within a Qwen panel, does Go-Stop performance improve monotonically with parameter scale? RQ2: Among roughly same-scale models served through NVIDIA Build, does model family affect Go-Stop performance?",
        ],
    )

    add_section(
        story,
        "2. Methods",
        [
            "The harness evaluates fixed policies only. There is no online learning, self-play training, or log-based policy update. Each agent receives a public game-state serialization and must return one legal action index.",
            "Remote models are called through OpenAI-compatible chat-completion APIs. The fixed policy prompt asks the model to choose one legal action index only, optimize long-run profit with risk control, and avoid explanation. Invalid, unparsable, or out-of-range responses fall back to the first legal action.",
            "The Qwen study uses Alibaba DashScope with all 24 seat permutations repeated twice. Each session has a two-hand horizon. The NVIDIA study uses NVIDIA Build NIM with the same seat enumeration and repetition, but a one-hand horizon and max_remote_calls_per_agent=1 because rate limits were binding.",
            "The primary metric is terminal session profit relative to initial bankroll. We also report empirical CVaR_0.05, win rate, ruin probability, and sample count.",
        ],
    )

    story.append(PageBreak())
    story.append(paragraph("3. Results", STYLES["section"]))
    story.append(
        paragraph(
            "RQ1 is answered negatively in this panel. The best Qwen result is the 397B model, not the largest 480B model.",
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
            "RQ2 is answered positively under the constrained NVIDIA panel. Nemotron has the strongest mean-profit and tail-risk profile among the roughly same-scale models.",
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

    add_section(
        story,
        "4. Discussion",
        [
            "The two panels agree on the central point: fixed-policy Go-Stop performance is not a simple function of parameter count. In the Qwen panel, the best result comes from the 397B model rather than the 480B model. In the NVIDIA panel, models of roughly similar scale separate by family, with Nemotron producing the strongest profit and tail-risk profile.",
            "These outcomes fit the game domain. Go-Stop requires local tactical choices, risk control, settlement awareness, and disciplined JSON action selection. General language-model scale can help, but the observed policy is also shaped by model specialization, instruction following, decoding behavior, and provider-level serving constraints.",
        ],
    )

    add_section(
        story,
        "5. Limitations",
        [
            "The model panels are convenience samples from currently callable remote APIs. The Qwen scale panel mixes Qwen3.5 and Qwen Coder variants, so parameter scale is confounded with model specialization.",
            "The NVIDIA panel is constrained by rate limits and uses max_remote_calls_per_agent=1. It measures constrained first-decision-policy behavior more than full-game autonomous play. The horizons are short: two hands for Qwen and one hand for NVIDIA.",
            "The sample count supports the reported empirical summaries, but not universal model ranking claims.",
        ],
    )

    add_section(
        story,
        "6. Conclusion",
        [
            "In a reproducible four-player Go-Stop evaluation harness, Qwen parameter scale does not produce monotonic performance gains, and same-scale NVIDIA Build models differ substantially by family. The strongest Qwen result comes from qwen3.5-397b-a17b; the strongest NVIDIA result comes from nvidia/nemotron-3-super-120b-a12b.",
            "The main implication is methodological: multi-agent, risk-sensitive card-game evaluation should report model identity, parameter scale, family, serving constraints, and tail-risk metrics together rather than reducing model quality to size alone.",
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
