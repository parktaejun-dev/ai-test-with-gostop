#!/usr/bin/env python3
"""Build the public Korean/English sectioned PDF report for Go-Stop evaluation."""

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
PAPER_TITLE_KO = "4인 고스톱 LLM 평가 실험 결과"
PAPER_TITLE_EN = "Go-Stop LLM Evaluation Result Report"
KOREAN_FONT = "PublicKorean"


def register_fonts() -> None:
    candidates = [
        Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
        Path("/System/Library/Fonts/Supplemental/NotoSansGothic-Regular.ttf"),
    ]
    for path in candidates:
        if path.exists():
            pdfmetrics.registerFont(TTFont(KOREAN_FONT, str(path)))
            return
    pdfmetrics.registerFont(UnicodeCIDFont("HYGothic-Medium"))
    globals()["KOREAN_FONT"] = "HYGothic-Medium"


register_fonts()


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text), style)


def code(text: str) -> Preformatted:
    return Preformatted(text.rstrip(), STYLES["code"])


def add_section(story: list, title: str, body: list[str], lang: str) -> None:
    story.append(p(title, STYLES[f"section_{lang}"]))
    for item in body:
        story.append(p(item, STYLES[f"body_{lang}"]))
        story.append(Spacer(1, 0.05 * inch))
    story.append(Spacer(1, 0.08 * inch))


def result_table(headers: list[str], rows: list[list[str]], widths: list[float]) -> Table:
    table_data = [[p(cell, STYLES["table_header"]) for cell in headers]]
    for row in rows:
        table_data.append([p(cell, STYLES["table_cell"]) for cell in row])
    table = Table(table_data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
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


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.drawString(doc.leftMargin, 0.45 * inch, "Go-Stop AI Evaluation Report")
    canvas.drawRightString(letter[0] - doc.rightMargin, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


QWEN_ROWS = [
    ["qwen3.5-397b-a17b", "397B/A17B", "996.25", "-1850.08", "0.3021", "48"],
    ["qwen3.5-122b-a10b", "122B/A10B", "-51.75", "-4145.33", "0.3542", "48"],
    ["qwen3-coder-480b-a35b-instruct", "480B/A35B", "-198.92", "-5084.75", "0.2396", "48"],
    ["qwen3-coder-30b-a3b-instruct", "30B/A3B", "-745.58", "-5269.25", "0.1042", "48"],
]

NVIDIA_ROWS = [
    ["nvidia/nemotron-3-super-120b-a12b", "~120B", "500.65", "-1384.17", "0.2708", "48"],
    ["mistralai/mistral-small-4-119b-2603", "~119B", "-73.19", "-4150.00", "0.2917", "48"],
    ["qwen/qwen3.5-122b-a10b", "122B", "-172.85", "-3350.42", "0.1875", "48"],
    ["stockmark/stockmark-2-100b-instruct", "~100B", "-254.60", "-4267.08", "0.2500", "48"],
]

TINY_ROWS = [
    ["ibm/granite-3.0-3b-a800m-instruct", "3B/A800M", "381.25", "-1966.67", "0.3125", "48"],
    ["meta/llama-3.2-1b-instruct", "1B", "-20.83", "-2083.33", "0.2708", "48"],
    ["google/gemma-2-2b-it", "2B", "-68.75", "-3833.33", "0.2500", "48"],
    ["microsoft/phi-4-mini-instruct", "mini", "-291.67", "-3916.67", "0.1667", "48"],
]

QWEN_POLICY_KO = [
    ["균형", "qwen3-4b", "224.88", "-1166.67"],
    ["분석", "qwen3-4b", "412.33", "-2566.83"],
    ["보수", "qwen3-8b", "238.08", "-1301.67"],
    ["공격", "qwen3-14b", "254.08", "-1284.33"],
]

QWEN_POLICY_EN = [
    ["Balanced", "qwen3-4b", "224.88", "-1166.67"],
    ["Analytic", "qwen3-4b", "412.33", "-2566.83"],
    ["Conservative", "qwen3-8b", "238.08", "-1301.67"],
    ["Aggressive", "qwen3-14b", "254.08", "-1284.33"],
]

NVIDIA_POLICY_KO = [
    ["균형", "nvidia/nemotron-3-super-120b-a12b", "645.17", "-2067.00"],
    ["분석", "nvidia/nemotron-3-super-120b-a12b", "598.92", "-2067.00"],
    ["보수", "nvidia/nemotron-3-super-120b-a12b", "416.67", "-1850.00"],
    ["공격", "nvidia/nemotron-3-super-120b-a12b", "598.83", "-3701.67"],
]

NVIDIA_POLICY_EN = [
    ["Balanced", "nvidia/nemotron-3-super-120b-a12b", "645.17", "-2067.00"],
    ["Analytic", "nvidia/nemotron-3-super-120b-a12b", "598.92", "-2067.00"],
    ["Conservative", "nvidia/nemotron-3-super-120b-a12b", "416.67", "-1850.00"],
    ["Aggressive", "nvidia/nemotron-3-super-120b-a12b", "598.83", "-3701.67"],
]


def add_korean(story: list) -> None:
    story.append(p("한국어", STYLES["language_ko"]))
    add_section(
        story,
        "초록",
        [
            "고정된 원격 LLM 정책을 같은 4인 고스톱 환경에서 비교했다. 고스톱은 숨은 패, 다음 패의 운, 조합 점수, 상대 행동, 고/스톱 위험이 짧은 판 안에 들어 있다. Qwen과 NVIDIA 실험에서는 성능이 모델 크기만으로 정해지지 않았다. 보조 실험에서는 제한된 조건에서 작은 모델도 플러스 수익을 냈고, 지시 성향에 따라 결과가 달라졌다. 이 결과는 실험 조건 안에서만 읽어야 한다.",
        ],
        "ko",
    )
    add_section(
        story,
        "왜 고스톱인가?",
        [
            "고스톱은 작은 확률 게임이지만 판단은 가볍지 않다. 각 행동은 숨은 패, 불확실한 다음 패, 상대 행동, 큰 손실을 만들 수 있는 정산 규칙 아래에서 선택된다. 고/스톱은 멈출지 더 갈지의 위험 판단이다.",
            "평균 수익만 보면 위험하다. 이 평가는 CVaR 5%, 승률, 파산 확률, 표본 수를 함께 본다. 광고 입찰도 매 노출마다 돈을 쓸지, 아낄지, 입찰가를 조정할지 정해야 하므로 같은 관점에서 볼 수 있다.",
        ],
        "ko",
    )
    add_section(
        story,
        "산업적 연결: 광고 입찰",
        [
            "광고 입찰은 고스톱과 같은 게임이 아니지만, 평가해야 하는 의사결정 구조가 닮아 있다. 광고 시스템은 제한된 예산 안에서 매 노출마다 입찰할지, 낮출지, 기다릴지를 결정한다. 전환 확률, 경쟁 입찰가, 빈도 피로, 잔여 예산, 캠페인 pacing은 모두 불확실하다.",
            "어떤 정책은 평균 ROAS가 좋아 보여도 특정 구간에서 예산을 너무 빨리 태우거나, 낮은 품질 inventory에 과도하게 노출되거나, 드문 큰 손실을 만들 수 있다. 이 고스톱 평가는 광고 시스템을 직접 모사하지 않는다. 대신 순차 행동 선택, 불확실성, 예산/위험 trade-off, 하방 위험 관리가 함께 나타나는 정책 평가 프레임으로 연결된다.",
        ],
        "ko",
    )
    add_section(
        story,
        "확인 질문과 답",
        [
            "RQ1: 고스톱은 LLM 에이전트의 위험 판단 평가에 쓸 수 있는가? 쓸 수 있다.",
            "RQ2: Qwen/DashScope 패널에서 모델이 클수록 성능이 좋아졌는가? 그렇지 않았다.",
            "RQ3: 비슷한 규모의 NVIDIA Build 패널에서 모델 계열별 차이가 보이는가? 제한된 조건 안에서 차이가 보였다.",
            "RQ4: 소형 모델과 prompt-policy 변형은 모델별 차이를 보이는가? 참고 결과로 차이가 보였다.",
        ],
        "ko",
    )
    add_section(
        story,
        "용어 정의",
        [
            "Mean profit: 세션 종료 후 모델이 얻은 평균 수익이다. 평균만으로는 큰 손실 위험을 설명하지 못한다.",
            "CVaR 5%: 가장 나쁜 하위 5% 결과의 평균 손실을 요약하는 지표다. 표본 수가 작으므로 참고 지표로만 사용한다.",
            "Win rate: 세션에서 양의 수익을 낸 비율이다. 승률이 높아도 큰 손실이 있으면 좋은 정책이라고 보기 어렵다.",
            "Ruin probability: 자본이 소진되거나 사실상 파산 상태에 도달할 확률이다.",
            "Parameter scale: 모델의 명목 파라미터 규모다. MoE 모델에서는 전체 파라미터와 active parameter가 다를 수 있다.",
            "Policy framing: 같은 게임 상태에서 모델에 제시하는 의사결정 지침의 성향이다.",
            "ROAS: 광고비 대비 매출이다. 평균 ROAS가 좋아도 예산 소진 속도나 하방 손실을 따로 봐야 한다.",
            "Budget pacing: 캠페인 예산을 기간 전체에 맞게 쓰도록 지출 속도를 조절하는 과정이다.",
        ],
        "ko",
    )
    add_section(
        story,
        "네 가지 정책 framing 쉽게 설명",
        [
            "Balanced: 수익과 위험을 같이 보라는 기본형이다. 너무 무리하지도, 너무 겁먹지도 않는 정책이다.",
            "Analytic: 패의 조합, 기대값, 상대 위험을 더 따져 보라는 분석형이다. 감보다 근거를 더 요구한다.",
            "Conservative: 큰 손실을 피하는 것을 우선하는 보수형이다. 애매하면 멈추고, 자본을 지키는 쪽으로 기운다.",
            "Aggressive: 수익 기회를 더 강하게 잡는 공격형이다. 이길 가능성이 보이면 더 밀어붙이는 쪽으로 기운다.",
        ],
        "ko",
    )
    story.append(p("결과", STYLES["section_ko"]))
    story.append(result_table(["모델", "규모", "평균 수익", "CVaR 5%", "승률", "표본"], QWEN_ROWS, TABLE6))
    story.append(Spacer(1, 0.14 * inch))
    story.append(result_table(["모델", "규모", "평균 수익", "CVaR 5%", "승률", "표본"], NVIDIA_ROWS, TABLE6))
    story.append(Spacer(1, 0.14 * inch))
    story.append(result_table(["소형 모델", "규모", "평균 수익", "CVaR 5%", "승률", "표본"], TINY_ROWS, TABLE6))
    story.append(Spacer(1, 0.14 * inch))
    story.append(result_table(["정책", "Qwen 1위 모델", "1위 평균", "1위 CVaR"], QWEN_POLICY_KO, TABLE4))
    story.append(Spacer(1, 0.14 * inch))
    story.append(result_table(["정책", "NVIDIA 1위 모델", "1위 평균", "1위 CVaR"], NVIDIA_POLICY_KO, TABLE4))
    story.append(Spacer(1, 0.16 * inch))
    add_section(
        story,
        "해석 범위",
        [
            "이 결과 보고서는 모델 순위를 확정하려는 작업이 아니다. 고스톱을 짧은 위험 판단 환경으로 두고, 원격 LLM이 규모, 계열, 지시 성향에 따라 어떻게 달라지는지 비교한다.",
            "핵심 결과는 세 가지다. 첫째, 고스톱은 숨은 정보와 큰 손실 위험을 함께 가진 짧은 평가 환경이다. 둘째, Qwen 패널에서는 파라미터가 클수록 성능이 좋아지는 흐름이 나오지 않았다. 셋째, 같은 규모대 NVIDIA 패널과 정책 실험에서는 모델별 차이가 보였다.",
            "한계도 있다. 표본 수가 작고, NVIDIA 실험은 호출 1회 제약이 있으며, Qwen 비교에는 Coder와 Qwen3.5 변형이 섞여 있다. 결론은 확정 순위가 아니라 재현 가능한 비교 결과로 읽어야 한다.",
        ],
        "ko",
    )
    add_section(
        story,
        "한계",
        [
            "모델 패널은 사용 가능한 원격 API에서 구성한 convenience sample이다. Qwen 비교는 Coder와 Qwen3.5 변형을 함께 포함하므로 파라미터 규모와 특화 목적이 부분적으로 얽혀 있다. NVIDIA 실행은 에이전트별 원격 호출 1회 제약 때문에 full-game autonomous play보다 제한된 first-decision behavior에 가깝다. 정책 스크린은 model-policy cell당 24 표본이므로 보조 결과다.",
        ],
        "ko",
    )


def add_english(story: list) -> None:
    story.append(PageBreak())
    story.append(p("English", STYLES["language_en"]))
    add_section(
        story,
        "Abstract",
        [
            "We compare fixed remote LLM policies in the same four-player Go-Stop environment. Go-Stop puts hidden cards, uncertain draws, scoring combinations, opponent interaction, and Go/Stop risk into short games. The Qwen and NVIDIA runs show that performance is not explained by model size alone. Supplementary runs show that a small model can make positive mean profit under restricted settings, and that prompt framing changes results by model. The results apply only to these run conditions.",
        ],
        "en",
    )
    add_section(
        story,
        "Why Go-Stop?",
        [
            "Go-Stop is a compact stochastic decision environment. Each action is chosen under hidden cards, uncertain future draws, opponent interaction, and settlement rules that can create heavy lower-tail losses. The Go/Stop decision is a risk-sensitive stopping problem.",
            "Mean profit alone is not sufficient. The evaluation reports CVaR 5%, win rate, ruin probability, and sample count together.",
        ],
        "en",
    )
    add_section(
        story,
        "Industrial Link: Advertising Bidding",
        [
            "Advertising bidding is not the same domain as Go-Stop, but the decision structure is similar enough to motivate the evaluation frame. An ad system repeatedly decides whether to bid, lower a bid, or wait under a finite budget. Conversion probability, competing bids, frequency fatigue, remaining budget, and campaign pacing are all uncertain.",
            "A policy may show attractive average ROAS while spending too fast in specific segments, over-exposing low-quality inventory, or creating rare but severe losses. The Go-Stop harness does not simulate advertising directly; it supplies a compact stress test for sequential action selection, uncertainty, budget-risk trade-offs, and lower-tail risk control.",
        ],
        "en",
    )
    add_section(
        story,
        "Questions and Answers",
        [
            "RQ1: Can Go-Stop be used to evaluate risk-sensitive decisions by LLM agents? Yes.",
            "RQ2: Does observed performance increase monotonically with nominal parameter scale in the Qwen-labeled DashScope panel? No.",
            "RQ3: Are cross-family differences visible in a rate-limited, roughly same-scale NVIDIA Build panel? They are visible under the constrained panel.",
            "RQ4: Do small models and prompt-policy variants show measurable but model-specific differences? They do in the supporting runs.",
        ],
        "en",
    )
    add_section(
        story,
        "Glossary",
        [
            "Mean profit: the average session-ending profit for a model. The mean alone does not capture severe downside risk.",
            "CVaR 5%: the average of the worst 5% outcomes. In this report it is a support metric because sample counts are small.",
            "Win rate: the share of sessions with positive profit. A high win rate can still hide rare but severe losses.",
            "Ruin probability: the probability that a player exhausts capital or reaches an effectively bankrupt state.",
            "Parameter scale: the nominal parameter size of a model. For MoE models, total parameters and active parameters can differ.",
            "Policy framing: the decision-making instruction style given to the model.",
            "ROAS: Return on Ad Spend. A strong average ROAS can still hide budget burn or lower-tail loss risk.",
            "Budget pacing: controlling campaign spend rate so the budget lasts across the intended time window.",
        ],
        "en",
    )
    add_section(
        story,
        "Four Policy Framings in Plain Language",
        [
            "Balanced: the default frame. Consider profit and risk together. It is neither strongly cautious nor strongly risk-seeking.",
            "Analytic: the evidence-focused frame. Reason more about combinations, expected value, and opponent risk.",
            "Conservative: the loss-avoidance frame. Avoid large downside outcomes, stop earlier when uncertain, and preserve capital.",
            "Aggressive: the upside-seeking frame. Push harder when a profitable chance appears and accept more risk for higher payoff.",
        ],
        "en",
    )
    story.append(p("Results", STYLES["section_en"]))
    story.append(result_table(["Model", "Scale", "Mean profit", "CVaR 5%", "Win rate", "Samples"], QWEN_ROWS, TABLE6))
    story.append(Spacer(1, 0.14 * inch))
    story.append(result_table(["Model", "Scale", "Mean profit", "CVaR 5%", "Win rate", "Samples"], NVIDIA_ROWS, TABLE6))
    story.append(Spacer(1, 0.14 * inch))
    story.append(result_table(["Small model", "Scale", "Mean profit", "CVaR 5%", "Win rate", "Samples"], TINY_ROWS, TABLE6))
    story.append(Spacer(1, 0.14 * inch))
    story.append(result_table(["Policy", "Qwen top model", "Top mean", "Top CVaR"], QWEN_POLICY_EN, TABLE4))
    story.append(Spacer(1, 0.14 * inch))
    story.append(result_table(["Policy", "NVIDIA top model", "Top mean", "Top CVaR"], NVIDIA_POLICY_EN, TABLE4))
    story.append(Spacer(1, 0.16 * inch))
    add_section(
        story,
        "Interpretation Scope",
        [
            "This report does not rank Go-Stop players globally. It uses Go-Stop as a short risk-heavy decision setting to compare remote LLM policies across scale, model family, and prompt framing.",
            "The main results are simple. Go-Stop provides hidden information and large-loss risk in short runs. The Qwen panel does not improve monotonically with parameter count. The NVIDIA same-scale panel and policy screens show model-specific differences.",
            "The limits are also clear. Sample counts are modest, the NVIDIA run uses a one-call constraint, and the Qwen scale comparison mixes Coder and Qwen3.5 variants. Read the results as reproducible comparisons, not definitive rankings.",
        ],
        "en",
    )
    add_section(
        story,
        "Limitations",
        [
            "The model panels are convenience samples from available remote APIs. The Qwen comparison mixes Coder and Qwen3.5 variants, so parameter scale is partly confounded with specialization. The NVIDIA run is constrained by one remote call per agent per session, so it measures constrained first-decision behavior more than full-game autonomous play. Policy screens have 24 samples per model-policy cell and are supplementary.",
        ],
        "en",
    )


def build_pdf() -> Path:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=letter,
        rightMargin=0.72 * inch,
        leftMargin=0.72 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.72 * inch,
        title=f"{PAPER_TITLE_KO} / {PAPER_TITLE_EN}",
        author="Go-Stop AI Evaluation Harness",
    )
    story: list = [
        p(PAPER_TITLE_KO, STYLES["title_ko"]),
        p(PAPER_TITLE_EN, STYLES["title_en"]),
        p("Go-Stop AI Evaluation Harness", STYLES["subtitle"]),
        p(f"Repository: {REPO_URL}", STYLES["subtitle"]),
        p(f"Web: {WEB_URL}", STYLES["subtitle"]),
        Spacer(1, 0.18 * inch),
    ]
    add_korean(story)
    add_english(story)
    story.append(PageBreak())
    story.append(p("Reproducibility Commands", STYLES["section_en"]))
    story.append(
        code(
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
"""
        )
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return OUTPUT_PATH


TABLE6 = [2.45 * inch, 0.72 * inch, 0.82 * inch, 0.82 * inch, 0.7 * inch, 0.55 * inch]
TABLE4 = [1.0 * inch, 2.65 * inch, 0.95 * inch, 0.95 * inch]

BASE = getSampleStyleSheet()
STYLES = {
    "title_ko": ParagraphStyle("TitleKo", parent=BASE["Title"], fontName=KOREAN_FONT, fontSize=18, leading=23, alignment=TA_CENTER, spaceAfter=8),
    "title_en": ParagraphStyle("TitleEn", parent=BASE["Title"], fontName="Helvetica", fontSize=12, leading=15, alignment=TA_CENTER, textColor=colors.HexColor("#333333"), spaceAfter=6),
    "subtitle": ParagraphStyle("Subtitle", parent=BASE["Normal"], fontName="Helvetica", fontSize=9, leading=12, alignment=TA_CENTER, textColor=colors.HexColor("#333333")),
    "language_ko": ParagraphStyle("LanguageKo", parent=BASE["Heading1"], fontName=KOREAN_FONT, fontSize=16, leading=21, spaceBefore=12, spaceAfter=10),
    "language_en": ParagraphStyle("LanguageEn", parent=BASE["Heading1"], fontName="Helvetica-Bold", fontSize=16, leading=21, spaceBefore=12, spaceAfter=10),
    "section_ko": ParagraphStyle("SectionKo", parent=BASE["Heading2"], fontName=KOREAN_FONT, fontSize=12.5, leading=16, alignment=TA_LEFT, spaceBefore=8, spaceAfter=5),
    "section_en": ParagraphStyle("SectionEn", parent=BASE["Heading2"], fontName="Helvetica-Bold", fontSize=12.5, leading=16, alignment=TA_LEFT, spaceBefore=8, spaceAfter=5),
    "body_ko": ParagraphStyle("BodyKo", parent=BASE["BodyText"], fontName=KOREAN_FONT, fontSize=8.9, leading=12.4, alignment=TA_LEFT),
    "body_en": ParagraphStyle("BodyEn", parent=BASE["BodyText"], fontName="Helvetica", fontSize=8.9, leading=12.4, alignment=TA_LEFT, textColor=colors.HexColor("#333333")),
    "table_header": ParagraphStyle("TableHeader", parent=BASE["BodyText"], fontName=KOREAN_FONT, fontSize=7.1, leading=8.8),
    "table_cell": ParagraphStyle("TableCell", parent=BASE["BodyText"], fontName=KOREAN_FONT, fontSize=6.8, leading=8.3),
    "code": ParagraphStyle("Code", parent=BASE["Code"], fontName="Courier", fontSize=7.2, leading=9, leftIndent=8, borderPadding=5, backColor=colors.HexColor("#f4f4f4")),
}


if __name__ == "__main__":
    print(build_pdf())
