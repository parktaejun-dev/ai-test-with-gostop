#!/usr/bin/env python3
"""Build the Korean-first public PDF for the Go-Stop LLM evaluation paper.

The repository does not assume a local TeX installation. This script creates a
stable bilingual PDF from the public paper text and result tables with
reportlab.
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
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
PAPER_TITLE_KO = "4인 고스톱에서의 위험 민감 LLM 평가"
PAPER_TITLE_EN = "Risk-Sensitive LLM Evaluation in Four-Player Go-Stop"
PDF_TITLE = f"{PAPER_TITLE_KO} / {PAPER_TITLE_EN}"
KOREAN_FONT = "PublicKorean"
KOREAN_SERIF = "PublicKorean"


def register_korean_font() -> None:
    font_candidates = [
        Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
        Path("/System/Library/Fonts/Supplemental/NotoSansGothic-Regular.ttf"),
    ]
    for font_path in font_candidates:
        if font_path.exists():
            pdfmetrics.registerFont(TTFont(KOREAN_FONT, str(font_path)))
            return
    pdfmetrics.registerFont(UnicodeCIDFont("HYGothic-Medium"))
    pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))
    globals()["KOREAN_FONT"] = "HYGothic-Medium"
    globals()["KOREAN_SERIF"] = "HYSMyeongJo-Medium"


register_korean_font()


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
        append_body_item(story, item)
    story.append(Spacer(1, 0.08 * inch))


def append_body_item(story: list, text: str) -> None:
    if " / " in text:
        ko_text, en_text = text.split(" / ", 1)
        story.append(paragraph(ko_text, STYLES["body"]))
        story.append(Spacer(1, 0.03 * inch))
        story.append(paragraph(en_text, STYLES["body_en"]))
    else:
        style = STYLES["body_en"] if is_english_line(text) else STYLES["body"]
        story.append(paragraph(text, style))
    story.append(Spacer(1, 0.05 * inch))


def is_english_line(text: str) -> bool:
    stripped = text.lstrip()
    english_prefixes = (
        "English:",
        "Answer:",
        "Go-Stop ",
        "The ",
        "In ",
        "Repository:",
        "Web paper",
        "Public PDF:",
        "English manuscript",
        "Bilingual summary:",
        "Qwen result",
        "NVIDIA result",
        "NVIDIA small-model",
        "Policy screens:",
        "References ",
    )
    return stripped.startswith(english_prefixes)


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
        title=PDF_TITLE,
        author="Go-Stop AI Evaluation Harness",
    )

    story: list = []
    story.append(paragraph(PAPER_TITLE_KO, STYLES["title"]))
    story.append(paragraph(PAPER_TITLE_EN, STYLES["subtitle_title"]))
    story.append(paragraph("Go-Stop AI Evaluation Harness", STYLES["subtitle_en"]))
    story.append(paragraph("공개 GitHub판", STYLES["subtitle"]))
    story.append(paragraph("Public GitHub edition - April 2026", STYLES["subtitle_en"]))
    story.append(Spacer(1, 0.18 * inch))

    add_section(
        story,
        "초록 / Abstract",
        [
            "한국어: 이 원고는 재현 가능한 4인 고스톱 하네스에서 고정 원격 LLM 정책을 평가한다. 고스톱은 숨은 정보, 확률적 드로우, 조합적 점수 계산, 다중 에이전트 상호작용, 고/스톱 위험 결정을 짧은 에피소드 안에 압축한다. 주 실험인 Qwen 패널과 NVIDIA 패널은 관측 성능이 파라미터 규모만으로 설명되지 않음을 보인다. 보조 실험은 제한된 조건에서 소형 모델도 양의 평균 수익을 낼 수 있고, 정책 framing 효과가 모델별로 다르게 나타남을 보여준다. 모든 결과는 기술통계이며 보편적 모델 순위가 아니다.",
            "English: We evaluate fixed-policy LLM play in a reproducible four-player Go-Stop harness. The main Qwen and NVIDIA panels show that observed performance is not explained by parameter scale alone. Supplementary screens show positive small-model results under restricted settings and model-specific policy-framing effects. The results are descriptive, not universal model rankings.",
        ],
    )

    add_section(
        story,
        "1. 연구문제 / Research Questions",
        [
            "RQ1: 고스톱은 LLM 에이전트의 위험 민감적 순차 의사결정을 평가하기에 타당한 환경인가? / Is Go-Stop a plausible environment for evaluating risk-sensitive sequential decision making by LLM agents?",
            "RQ2: Qwen/DashScope 패널에서 관측 성능은 명목 파라미터 규모에 대해 단조적인가? / Is observed performance monotone in nominal parameter scale in the Qwen-labeled DashScope panel?",
            "RQ3: 비슷한 규모의 NVIDIA Build 패널에서 모델 family별 기술통계 차이가 보이는가? / Are cross-family differences visible in a rate-limited, roughly same-scale NVIDIA Build panel?",
            "RQ4: 보조 실험에서 소형 모델과 prompt-policy 변형은 측정 가능한 모델별 차이를 보이는가? / Do small models and prompt-policy variants show measurable but model-specific differences?",
            "답: RQ1은 방법론적으로 긍정이다. RQ2는 Qwen 패널에서 기술적으로 부정이다. RQ3는 제한된 NVIDIA 패널에서 family별 차이가 관찰된다. RQ4는 탐색적이다.",
            "Answer: RQ1 is methodologically positive. RQ2 is descriptively negative in the Qwen panel. RQ3 shows visible cross-family differences under the constrained NVIDIA panel. RQ4 remains exploratory.",
        ],
    )

    add_section(
        story,
        "2. 왜 고스톱인가 / Why Go-Stop",
        [
            "고스톱은 작은 확률적 의사결정 환경이다. 각 행동은 숨은 패, 불확실한 미래 드로우, 상대 행동, 큰 하방 손실을 만들 수 있는 정산 규칙 아래에서 선택된다. 고/스톱 결정은 위험 민감적 stopping problem이다.",
            "Go-Stop is a compact stochastic decision environment with hidden information, uncertain draws, opponent interaction, and risk-sensitive stop-or-continue choices.",
            "따라서 이 평가는 평균 수익과 함께 CVaR 5%, 승률, 파산 확률, 표본 수를 같이 본다. 이 구조는 실시간 광고 입찰과 캠페인 예산 pacing처럼 불확실한 수익과 하방 위험 아래에서 지출, 대기, 입찰 조정을 반복 결정하는 산업적 의사결정에도 방법론적으로 연결된다.",
            "The evaluation reports mean profit together with CVaR 5%, win rate, ruin probability, and sample count. This is methodologically relevant to industrial decision systems such as real-time advertising bidding and campaign budget pacing.",
        ],
    )

    add_section(
        story,
        "3. 방법 / Methods",
        [
            "하네스는 고정 정책만 평가한다. 온라인 학습, self-play training, 로그 기반 정책 업데이트는 없다. 각 에이전트는 공개 game-state serialization을 받고 하나의 legal action index를 반환해야 한다.",
            "The harness evaluates fixed policies only. There is no online learning, self-play training, or log-based policy update. Each agent receives a public game-state serialization and must return one legal action index.",
            "Qwen 주 실험은 Alibaba DashScope를 사용하며 24개 seat permutation을 2회 반복한다. 각 모델은 48 표본이고 세션 horizon은 2 hands다.",
            "The Qwen study uses Alibaba DashScope with all 24 seat permutations repeated twice, producing 48 samples per model with a two-hand horizon.",
            "NVIDIA 주 실험은 NVIDIA Build NIM을 사용하며 같은 seat enumeration과 repetition을 유지하지만 rate limit 때문에 one-hand horizon과 max_remote_calls_per_agent=1을 사용한다.",
            "The NVIDIA study uses NVIDIA Build NIM with the same seat enumeration and repetition, but a one-hand horizon and max_remote_calls_per_agent=1 because rate limits were binding.",
        ],
    )

    story.append(paragraph("4. 결과 / Results", STYLES["section"]))
    append_body_item(
        story,
        "Qwen 패널은 명목 파라미터 규모에 대해 단조적이지 않다. 397B 모델이 가장 높고, 더 큰 480B Coder 모델은 낮다. / The Qwen panel is not monotone in nominal parameter scale. The 397B model ranks first, while the larger 480B Coder model ranks lower.",
    )
    story.append(Spacer(1, 0.08 * inch))
    story.append(
        result_table(
            ["Model", "Params", "Mean profit", "CVaR 5%", "Win rate", "Samples"],
            [
                ["qwen3.5-397b-a17b", "397B/A17B", "996.25", "-1850.08", "0.3021", "48"],
                ["qwen3.5-122b-a10b", "122B/A10B", "-51.75", "-4145.33", "0.3542", "48"],
                ["qwen3-coder-480b-a35b-instruct", "480B/A35B", "-198.92", "-5084.75", "0.2396", "48"],
                ["qwen3-coder-30b-a3b-instruct", "30B/A3B", "-745.58", "-5269.25", "0.1042", "48"],
            ],
            [2.45 * inch, 0.8 * inch, 0.82 * inch, 0.82 * inch, 0.7 * inch, 0.55 * inch],
        )
    )
    story.append(Spacer(1, 0.18 * inch))

    append_body_item(
        story,
        "NVIDIA 패널에서는 Nemotron이 평균 수익과 empirical CVaR 기준으로 가장 높다. / In the constrained NVIDIA panel, Nemotron has the highest mean profit and least severe empirical CVaR.",
    )
    story.append(Spacer(1, 0.08 * inch))
    story.append(
        result_table(
            ["Model", "Scale", "Mean profit", "CVaR 5%", "Win rate", "Samples"],
            [
                ["nvidia/nemotron-3-super-120b-a12b", "~120B", "500.65", "-1384.17", "0.2708", "48"],
                ["mistralai/mistral-small-4-119b-2603", "~119B", "-73.19", "-4150.00", "0.2917", "48"],
                ["qwen/qwen3.5-122b-a10b", "122B", "-172.85", "-3350.42", "0.1875", "48"],
                ["stockmark/stockmark-2-100b-instruct", "~100B", "-254.60", "-4267.08", "0.2500", "48"],
            ],
            [2.55 * inch, 0.62 * inch, 0.82 * inch, 0.82 * inch, 0.7 * inch, 0.55 * inch],
        )
    )
    story.append(Spacer(1, 0.18 * inch))

    append_body_item(
        story,
        "NVIDIA 소형 모델 보조 실험에서는 Granite 3B가 양의 평균 수익을 보였다. / In the NVIDIA small-model screen, Granite 3B produced positive mean profit.",
    )
    story.append(Spacer(1, 0.08 * inch))
    story.append(
        result_table(
            ["Small NVIDIA model", "Scale", "Mean profit", "CVaR 5%", "Win rate", "Samples"],
            [
                ["ibm/granite-3.0-3b-a800m-instruct", "3B/A800M", "381.25", "-1966.67", "0.3125", "48"],
                ["meta/llama-3.2-1b-instruct", "1B", "-20.83", "-2083.33", "0.2708", "48"],
                ["google/gemma-2-2b-it", "2B", "-68.75", "-3833.33", "0.2500", "48"],
                ["microsoft/phi-4-mini-instruct", "mini", "-291.67", "-3916.67", "0.1667", "48"],
            ],
            [2.55 * inch, 0.7 * inch, 0.82 * inch, 0.82 * inch, 0.7 * inch, 0.55 * inch],
        )
    )
    story.append(Spacer(1, 0.18 * inch))

    append_body_item(
        story,
        "정책 스크린은 모델별 prompt-policy 민감도를 보인다. Qwen 소형 패널은 framing에 따라 1위가 바뀌고, NVIDIA 정책 스크린은 Nemotron이 네 framing 모두에서 1위를 유지한다. / Policy screens show model-specific prompt-policy sensitivity.",
    )
    story.append(Spacer(1, 0.08 * inch))
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
    story.append(Spacer(1, 0.12 * inch))
    story.append(
        result_table(
            ["NVIDIA policy", "Top model", "Top mean", "Top CVaR 5%"],
            [
                ["Balanced", "nvidia/nemotron-3-super-120b-a12b", "645.17", "-2067.00"],
                ["Analytic", "nvidia/nemotron-3-super-120b-a12b", "598.92", "-2067.00"],
                ["Conservative", "nvidia/nemotron-3-super-120b-a12b", "416.67", "-1850.00"],
                ["Aggressive", "nvidia/nemotron-3-super-120b-a12b", "598.83", "-3701.67"],
            ],
            [1.0 * inch, 2.65 * inch, 0.95 * inch, 0.95 * inch],
        )
    )
    story.append(Spacer(1, 0.16 * inch))

    add_section(
        story,
        "5. 해석 / Discussion",
        [
            "핵심 발견은 제한적이지만 분명하다. 이 하네스에서 고정 정책의 고스톱 성능은 명목 파라미터 수 하나로 요약되지 않는다. 모델 family, 정책 framing, serving 제약, fallback behavior, tail-risk behavior를 함께 보고해야 한다.",
            "The central finding is bounded but clear: fixed-policy Go-Stop performance in this harness is not summarized by nominal parameter count alone. Model family, policy framing, serving constraints, fallback behavior, and tail-risk behavior should be reported together.",
        ],
    )

    add_section(
        story,
        "6. 한계 / Limitations",
        [
            "모델 패널은 사용 가능한 원격 API에서 구성한 convenience sample이다. Qwen 비교는 Coder와 Qwen3.5 변형을 함께 포함하므로 파라미터 규모와 특화 목적이 부분적으로 얽혀 있다.",
            "The model panels are convenience samples from available remote APIs. The Qwen comparison mixes Coder and Qwen3.5 variants, so parameter scale is partly confounded with specialization.",
            "NVIDIA 실행은 rate limit 때문에 max_remote_calls_per_agent=1을 사용했다. 이는 full-game autonomous play보다 제한된 first-decision behavior에 가깝다.",
            "The NVIDIA run used max_remote_calls_per_agent=1 because of rate limits. It measures constrained first-decision-policy behavior more than full-game autonomous play.",
            "주 패널은 모델당 48 표본, 정책 스크린은 model-policy cell당 24 표본이다. CVaR은 안정적 추론이 아니라 하방 위험의 기술통계다.",
            "Main panels have 48 samples per model; policy screens have 24 samples per model-policy cell. CVaR is a descriptive lower-tail summary, not a stable inferential statistic.",
        ],
    )

    add_section(
        story,
        "7. 결론 / Conclusion",
        [
            "재현 가능한 4인 고스톱 하네스에서 Qwen 패널은 명목 파라미터 규모에 대해 단조적이지 않았고, 제한된 NVIDIA Build 패널은 family별 기술통계 차이를 보였다. 보조 실험은 제한된 조건에서 소형 모델의 양의 평균 수익과 모델별 정책 민감도를 보여준다.",
            "In a reproducible four-player Go-Stop harness, the Qwen panel is not monotone in nominal parameter scale, and the constrained NVIDIA Build panel shows visible cross-family differences. Supplementary screens show positive small-model performance under restricted settings and model-specific policy sensitivity.",
        ],
    )

    add_section(
        story,
        "코드와 산출물 / Code and Artifact Availability",
        [
            f"Repository: {REPO_URL}",
            f"Web paper page: {WEB_URL}",
            "Public PDF: paper/gostop_ai_evaluation_paper.pdf",
            "English manuscript source: paper/arxiv_main.tex",
            "Bilingual summary: paper/bilingual_summary.md",
            "Qwen result bundle: results/paper_qwen_4model_param_2h_2rep",
            "NVIDIA result bundle: results/paper_nvidia_120b_4model_family_1h_2rep_budget1",
            "NVIDIA small-model bundle: results/tiny_nvidia_4model_1h_2rep_budget1_20260425_075542",
            "Policy screens: results/policy_screen_qwen_tiny_*_20260425_102731 and results/policy_screen_nvidia_*_20260425_075542",
        ],
    )

    story.append(paragraph("재현 명령 / Reproducibility Commands", STYLES["section"]))
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
    append_body_item(story, "참고문헌은 paper/refs.bib에서 유지한다. / References are maintained in paper/refs.bib.")

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return OUTPUT_PATH


BASE_STYLES = getSampleStyleSheet()
STYLES = {
    "title": ParagraphStyle(
        "PublicPaperTitle",
        parent=BASE_STYLES["Title"],
        fontName=KOREAN_SERIF,
        fontSize=18,
        leading=23,
        alignment=TA_CENTER,
        spaceAfter=8,
    ),
    "subtitle_title": ParagraphStyle(
        "PublicPaperEnglishTitle",
        parent=BASE_STYLES["Title"],
        fontName="Helvetica",
        fontSize=12,
        leading=15,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#333333"),
        spaceAfter=5,
    ),
    "subtitle": ParagraphStyle(
        "PublicPaperSubtitle",
        parent=BASE_STYLES["Normal"],
        fontName=KOREAN_FONT,
        fontSize=9.6,
        leading=12.5,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#333333"),
    ),
    "subtitle_en": ParagraphStyle(
        "PublicPaperSubtitleEnglish",
        parent=BASE_STYLES["Normal"],
        fontName="Helvetica",
        fontSize=9.6,
        leading=12.5,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#333333"),
    ),
    "section": ParagraphStyle(
        "PublicPaperSection",
        parent=BASE_STYLES["Heading1"],
        fontName=KOREAN_FONT,
        fontSize=12.5,
        leading=16,
        alignment=TA_LEFT,
        spaceBefore=8,
        spaceAfter=5,
    ),
    "body": ParagraphStyle(
        "PublicPaperBody",
        parent=BASE_STYLES["BodyText"],
        fontName=KOREAN_FONT,
        fontSize=8.9,
        leading=12.4,
        alignment=TA_LEFT,
        spaceAfter=2,
    ),
    "body_en": ParagraphStyle(
        "PublicPaperBodyEnglish",
        parent=BASE_STYLES["BodyText"],
        fontName="Helvetica",
        fontSize=8.9,
        leading=12.4,
        alignment=TA_LEFT,
        spaceAfter=2,
        textColor=colors.HexColor("#333333"),
    ),
    "table_header": ParagraphStyle(
        "PublicPaperTableHeader",
        parent=BASE_STYLES["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=7.2,
        leading=9,
    ),
    "table_cell": ParagraphStyle(
        "PublicPaperTableCell",
        parent=BASE_STYLES["BodyText"],
        fontName="Helvetica",
        fontSize=6.9,
        leading=8.5,
    ),
    "code": ParagraphStyle(
        "PublicPaperCode",
        parent=BASE_STYLES["Code"],
        fontName="Courier",
        fontSize=7.2,
        leading=9,
        leftIndent=8,
        borderPadding=5,
        backColor=colors.HexColor("#f4f4f4"),
    ),
}


if __name__ == "__main__":
    output = build_pdf()
    print(output)
