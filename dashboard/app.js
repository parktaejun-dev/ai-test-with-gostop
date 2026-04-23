const LEGACY_RUN_OPTIONS = [
  { value: "paper_study_baselines", label: "paper_study_baselines" },
  { value: "paper_run_v2", label: "paper_run_v2" },
  { value: "paper_run", label: "paper_run" },
  { value: "paper_baseline", label: "paper_baseline" },
];
let RUN_OPTIONS = [...LEGACY_RUN_OPTIONS];
let resolveRunBasePath = (runName) => `../results/${runName}`;
const PUBLIC_SETTINGS_KEY = "godori-settings-public";
const SECRET_SETTINGS_KEY = "godori-settings-secret";

const BASELINE_METHOD_NOTES = [
  {
    title: "mean_profit",
    description: "평균 세션 수익. 높을수록 좋다. 논문 표의 1차 비교축이다.",
  },
  {
    title: "cvar_5",
    description: "하위 5% 꼬리 구간의 평균 손익. 덜 음수일수록 꼬리위험 방어가 좋다.",
  },
  {
    title: "ruin_probability",
    description: "파산 확률. 낮을수록 좋다. 장기 운용 가능성을 직접 보여준다.",
  },
  {
    title: "variance",
    description: "수익 변동성. 낮을수록 흔들림이 작다. mean_profit과 같이 읽어야 한다.",
  },
  {
    title: "showdown_ev_gain",
    description: "진단용 보조 지표. 쇼당 제안 시 실제 정산과 반사실 정산의 차이 평균이다.",
  },
  {
    title: "showdown_misplay_rate",
    description: "진단용 보조 지표. 쇼당 제안으로 손해를 본 비율이다.",
  },
  {
    title: "early_exit_rate",
    description: "중도 탈락 비율. 낮을수록 방어 안정성이 높다.",
  },
  {
    title: "forced_gwang_sell_rate",
    description: "광팔이 강제 매각 비율. 운영 압박이 얼마나 자주 생기는지 본다.",
  },
];

const FACTORIAL_METHOD_NOTES = [
  {
    title: "dominant_main_effect",
    description: "RQ1의 핵심 지표다. model과 strategy의 partial eta-squared를 직접 비교한다.",
  },
  {
    title: "interaction",
    description: "특정 모델이 특정 프롬프트를 유난히 잘 받는지 본다. 0에 가까우면 전략 효과가 모델 전반에 거의 평행하게 작동한다.",
  },
  {
    title: "mean_profit",
    description: "주효과 비교의 1차 목표치다. factorial report에서는 모델 마진 평균과 전략 마진 평균을 같이 읽는다.",
  },
  {
    title: "cvar_5 / ruin_probability",
    description: "보조 위험지표다. mean-profit 우세가 꼬리위험과 파산 확률에서도 유지되는지 확인한다.",
  },
];

const BASELINE_METRIC_COLUMNS = [
  { key: "mean_profit", label: "Mean", title: "Mean Profit", mode: "value", better: "higher" },
  { key: "cvar_5", label: "CVaR", title: "CVaR 5%", mode: "value", better: "higher" },
  { key: "ruin_probability", label: "Ruin", title: "Ruin Probability", mode: "percent", better: "lower" },
  { key: "variance", label: "Var", title: "Variance", mode: "value", better: "lower" },
];

const FACTORIAL_METRIC_COLUMNS = [
  { key: "mean_profit", label: "Mean", title: "Model-marginal Mean Profit", mode: "value", better: "higher" },
  { key: "cvar_5", label: "CVaR", title: "Model-marginal CVaR 5%", mode: "value", better: "higher" },
  { key: "ruin_probability", label: "Ruin", title: "Model-marginal Ruin Probability", mode: "percent", better: "lower" },
  { key: "sample_count", label: "Samples", title: "Observation count", mode: "count", better: "higher" },
  { key: "block_count", label: "Blocks", title: "Factorial block count", mode: "count", better: "higher" },
];

const dom = {};

document.addEventListener("DOMContentLoaded", async () => {
  bindDom();
  await initRunControls();
  hydrateExecutionPanel();
  initSectionSpy();
  const initialRun = getInitialRun();
  loadRun(initialRun);
});

function bindDom() {
  dom.runForm = document.querySelector("#run-form");
  dom.runSelect = document.querySelector("#run-select");
  dom.runLabel = document.querySelector("#run-label");
  dom.runTitle = document.querySelector("#run-title");
  dom.statusText = document.querySelector("#status-text");
  dom.executionPanel = document.querySelector("#execution-panel");
  dom.executionState = document.querySelector("#execution-state");
  dom.executionSummary = document.querySelector("#execution-summary");
  dom.executionMeta = document.querySelector("#execution-meta");
  dom.executionPrimary = document.querySelector("#execution-primary");
  dom.manifestFacts = document.querySelector("#manifest-facts");
  dom.rawLinks = document.querySelector("#raw-links");
  dom.overviewLede = document.querySelector("#overview-lede");
  dom.signalGrid = document.querySelector("#signal-grid");
  dom.overviewNotes = document.querySelector("#overview-notes");
  dom.riskReturnPlot = document.querySelector("#risk-return-plot");
  dom.agentTableHead = document.querySelector("#agent-table thead");
  dom.agentTableBody = document.querySelector("#agent-table tbody");
  dom.lineupTableHead = document.querySelector("#lineup-table thead");
  dom.lineupTableBody = document.querySelector("#lineup-table tbody");
  dom.crossPlayNotes = document.querySelector("#cross-play-notes");
  dom.eventBars = document.querySelector("#event-bars");
  dom.showdownTableHead = document.querySelector("#showdown-table thead");
  dom.showdownTableBody = document.querySelector("#showdown-table tbody");
  dom.incidentTableHead = document.querySelector("#incident-table thead");
  dom.incidentTableBody = document.querySelector("#incident-table tbody");
  dom.methodGrid = document.querySelector("#method-grid");
  dom.errorPanel = document.querySelector("#error-panel");
  dom.errorText = document.querySelector("#error-text");
}

async function initRunControls() {
  await hydrateRunOptions();
  dom.runSelect.innerHTML = RUN_OPTIONS.map(
    (run) => `<option value="${run.value}">${run.label}</option>`
  ).join("");

  dom.runForm.addEventListener("submit", (event) => {
    event.preventDefault();
    loadRun(dom.runSelect.value);
  });
}

function hydrateExecutionPanel() {
  if (!dom.executionPanel) {
    return;
  }

  const saved = readJsonStorage(PUBLIC_SETTINGS_KEY, {});
  const secrets = readJsonStorage(SECRET_SETTINGS_KEY, {});
  const apiKey = String(secrets.apiKey ?? "").trim();
  const selectedModels = Array.isArray(saved.selectedModels)
    ? saved.selectedModels.map((model) => String(model).trim()).filter(Boolean)
    : [];
  const ready = Boolean(apiKey) && (selectedModels.length === 4 || String(saved.mode ?? "").trim() === "factorial");
  const mode = String(saved.mode ?? "series").trim() || "series";
  const baseUrl = String(saved.baseUrl ?? "https://openrouter.ai/api/v1").trim();
  const family = String(saved.family ?? "").trim();
  const selectorUrl = String(saved.selectorUrl ?? "").trim();

  dom.executionPanel.dataset.ready = ready ? "true" : "false";
  dom.executionState.textContent = ready ? "준비됨" : "설정 필요";
  dom.executionSummary.textContent = ready
    ? `${mode === "factorial" ? "고정 4x4 factorial" : `${selectedModels.length}개 모델`} 설정이 저장돼 있다.`
    : "OpenRouter 설정을 저장하면 실행 명령이 이 자리에서 보인다.";
  dom.executionMeta.textContent = ready
    ? [mode === "factorial" ? "factorial" : family || null, selectorUrl ? "selector 연결됨" : null, baseUrl].filter(Boolean).join(" · ")
    : "API 키와 실행 모드를 먼저 저장해라.";
  dom.executionPrimary.textContent = ready ? "실행 명령 보기" : "설정하러 가기";
  dom.executionPrimary.href = ready ? "settings.html#command" : "settings.html#auth";
}

function readJsonStorage(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) {
      return fallback;
    }
    return JSON.parse(raw);
  } catch (_error) {
    return fallback;
  }
}

async function hydrateRunOptions() {
  const runsIndex = await tryFetchJson("./data/runs/index.json");
  if (runsIndex?.runs?.length) {
    RUN_OPTIONS = runsIndex.runs.map((run) => ({
      value: run.name,
      label: run.label ?? run.name,
    }));
    resolveRunBasePath = (runName) => `./data/runs/${runName}`;
    return;
  }

  const latestIndex = await tryFetchJson("./data/latest/index.json");
  if (latestIndex?.run || latestIndex?.source_results_dir) {
    const runName = latestIndex.run ?? "latest";
    RUN_OPTIONS = [{ value: runName, label: runName }];
    resolveRunBasePath = () => "./data/latest";
    return;
  }

  RUN_OPTIONS = [...LEGACY_RUN_OPTIONS];
  resolveRunBasePath = (runName) => `../results/${runName}`;
}

function getInitialRun() {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("run");
  if (RUN_OPTIONS.some((run) => run.value === requested)) {
    return requested;
  }
  return RUN_OPTIONS[0].value;
}

async function loadRun(runName) {
  setStatus("데이터를 읽는 중");
  dom.runSelect.value = runName;
  hideError();
  const basePath = resolveRunBasePath(runName);
  updateRawLinks(basePath);

  try {
    const [report, manifest, logText] = await Promise.all([
      fetchJson(`${basePath}/report.json`),
      fetchJson(`${basePath}/manifest.json`),
      fetchText(`${basePath}/session_logs.jsonl`),
    ]);

    const logs = parseJsonl(logText);
    const model = buildViewModel(runName, report, manifest, logs, basePath);
    render(model);
    updateQuery(runName);
    setStatus(`로그 ${formatInt(logs.length)}행 파싱 완료`);
  } catch (error) {
    console.error(error);
    if (runName !== "paper_study_baselines" && RUN_OPTIONS.some((run) => run.value === "paper_study_baselines")) {
      setStatus("현재 런을 읽지 못해서 기준 런으로 다시 연다");
      await loadRun("paper_study_baselines");
      return;
    }
    renderError(runName, error);
  }
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${url} returned ${response.status}`);
  }
  return response.json();
}

async function fetchText(url) {
  const response = await fetch(url, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${url} returned ${response.status}`);
  }
  return response.text();
}

async function tryFetchJson(url) {
  try {
    return await fetchJson(url);
  } catch (_error) {
    return null;
  }
}

function parseJsonl(text) {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function buildViewModel(runName, report, manifest, logs, basePath) {
  if (report.study_type === "blocked_factorial_llm") {
    return buildFactorialViewModel(runName, report, manifest, logs, basePath);
  }
  return buildLegacyViewModel(runName, report, manifest, logs, basePath);
}

function buildLegacyViewModel(runName, report, manifest, logs, basePath) {
  const agents = report.agent_performance_table ?? {};
  const rankings = report.ranking ?? [];
  const agentRows = Object.entries(agents).map(([agent, metrics]) => ({
    agent,
    ...metrics,
    rank: rankings.findIndex((entry) => entry.agent === agent) + 1,
  }));
  agentRows.sort((left, right) => left.rank - right.rank);

  const highestMean = pickBy(agentRows, "mean_profit", "max", ["cvar_5"]);
  const safest = pickBy(agentRows, "ruin_probability", "min", ["cvar_5", "mean_profit"]);
  const sharpestTail = pickBy(agentRows, "cvar_5", "max", ["mean_profit"]);
  const lowestVariance = pickBy(agentRows, "variance", "min", ["mean_profit"]);
  const widestVariance = pickBy(agentRows, "variance", "max", ["mean_profit"]);

  const crossPlay = summarizeCrossPlay(report.cross_play_results ?? {}, "baseline");
  const logSummary = summarizeLegacyLogs(logs);

  const headline = composeLegacyHeadline({
    highestMean,
    safest,
    sharpestTail,
    runName,
  });

  const overviewSignals = [
    {
      label: "평균수익 1위",
      value: highestMean?.agent ?? "n/a",
      meta: formatMetric(highestMean?.mean_profit, "value"),
    },
    {
      label: "최저 파산확률",
      value: safest?.agent ?? "n/a",
      meta: formatMetric(safest?.ruin_probability, "percent"),
    },
    {
      label: "최소 변동성",
      value: lowestVariance?.agent ?? "n/a",
      meta: formatMetric(lowestVariance?.variance, "value"),
    },
  ];

  const overviewNotes = [
    `${highestMean?.agent ?? "n/a"}가 평균수익 기준으로 선두다. ${highestMean?.agent === safest?.agent ? "수익 우위와 방어력이 한 에이전트에 같이 모여 있다." : "다만 수익 우위와 방어력은 분리돼 있다."}`,
    `${sharpestTail?.agent ?? "n/a"}의 cvar_5가 가장 높다. 하위 5% 구간 손실 방어를 중요하게 보면 이 축을 따로 봐야 한다.`,
    `${widestVariance?.agent ?? "n/a"}는 분산이 가장 커서 성과 해석에 더 긴 표본이 필요하다. 사건 로그와 쇼당 수치는 마지막 진단 섹션에서 분리해서 읽는 편이 맞다.`,
  ];

  const manifestFacts = [
    { label: "agents", value: formatInt(manifest.agents?.length ?? 0) },
    { label: "lineups", value: formatInt(manifest.lineup_count ?? 0) },
    { label: "base_seed", value: formatInt(manifest.config?.base_seed ?? 0) },
    { label: "session_hands", value: formatInt(manifest.config?.session_hands ?? 0) },
    { label: "remote_eval_hands", value: formatInt(manifest.config?.remote_eval_hands ?? 0) },
    { label: "initial_bankroll", value: formatInt(manifest.config?.initial_bankroll ?? 0) },
  ];

  return {
    runName,
    report,
    manifest,
    logs,
    studyType: "baseline",
    agentRows,
    metricColumns: BASELINE_METRIC_COLUMNS,
    headline,
    overviewSignals,
    overviewNotes,
    manifestFacts,
    rawLinks: buildRawLinks(basePath, manifest),
    crossPlay,
    logSummary,
    methodNotes: BASELINE_METHOD_NOTES,
  };
}

function buildFactorialViewModel(runName, report, manifest, logs, basePath) {
  const rankings = report.ranking ?? [];
  const agentRows = Object.entries(report.agent_performance_table ?? {}).map(([agent, metrics]) => ({
    agent,
    ...metrics,
    rank: rankings.findIndex((entry) => entry.agent === agent) + 1,
  }));
  agentRows.sort((left, right) => left.rank - right.rank);

  const rq = report.rq_model_vs_strategy ?? {};
  const effect = rq.effect_decomposition ?? {};
  const terms = effect.terms ?? {};
  const dominantMain = effect.dominant_main_effect ?? { term: "n/a", partial_eta_squared: NaN };
  const modelLeader = pickBy(agentRows, "mean_profit", "max", ["cvar_5"]);
  const safest = pickBy(agentRows, "ruin_probability", "min", ["cvar_5", "mean_profit"]);
  const bestTail = pickBy(agentRows, "cvar_5", "max", ["mean_profit"]);
  const strategyRows = Object.entries(rq.mean_profit?.by_strategy ?? {}).map(([strategyId, summary]) => ({
    strategyId,
    label: resolveStrategyLabel(report, strategyId),
    estimate: Number(summary?.estimate ?? NaN),
  }));
  const strategyLeader = pickBy(strategyRows, "estimate", "max", []);

  const overviewSignals = [
    {
      label: "주효과 우세",
      value: prettyEffectLabel(dominantMain.term),
      meta: `η²p ${formatMetric(dominantMain.partial_eta_squared, "value")}`,
    },
    {
      label: "모델 평균수익 1위",
      value: modelLeader?.agent ?? "n/a",
      meta: formatMetric(modelLeader?.mean_profit, "value"),
    },
    {
      label: "전략 평균수익 1위",
      value: strategyLeader?.label ?? "n/a",
      meta: formatMetric(strategyLeader?.estimate, "value"),
    },
  ];

  const overviewNotes = [
    `model η²p=${formatMetric(terms.model?.partial_eta_squared, "value")}, strategy η²p=${formatMetric(terms.strategy?.partial_eta_squared, "value")}, interaction η²p=${formatMetric(terms.interaction?.partial_eta_squared, "value")}다. RQ1은 model과 strategy의 상대 크기로 읽는다.`,
    `${modelLeader?.agent ?? "n/a"}가 모델 마진 평균수익 ${formatMetric(modelLeader?.mean_profit, "value")}로 선두고, ${bestTail?.agent ?? "n/a"}의 model-marginal cvar_5는 ${formatMetric(bestTail?.cvar_5, "value")}다.`,
    `${strategyLeader?.label ?? "n/a"}가 전략 마진 평균수익 ${formatMetric(strategyLeader?.estimate, "value")}를 기록했다. 이 번들의 base_seed는 ${(manifest.config?.base_seeds ?? []).join(", ") || "n/a"}다.`,
  ];

  const manifestFacts = [
    { label: "study_type", value: report.study_type ?? manifest.config?.experiment ?? "blocked_factorial_llm" },
    { label: "model_panel", value: formatInt(report.model_panel?.length ?? manifest.config?.model_panel?.length ?? 0) },
    { label: "strategies", value: formatInt(report.strategy_panel?.length ?? manifest.config?.strategy_count ?? 0) },
    { label: "base_seeds", value: (manifest.config?.base_seeds ?? []).join(", ") || "n/a" },
    { label: "session_hands", value: formatInt(manifest.config?.session_hands ?? 0) },
    { label: "factorial_block", value: manifest.config?.factorial_design?.factorial_block_id ?? "n/a", multiline: true },
  ];

  return {
    runName,
    report,
    manifest,
    logs,
    studyType: "blocked_factorial_llm",
    agentRows,
    metricColumns: FACTORIAL_METRIC_COLUMNS,
    headline: composeFactorialHeadline(runName, dominantMain, modelLeader, strategyLeader),
    overviewSignals,
    overviewNotes,
    manifestFacts,
    rawLinks: buildRawLinks(basePath, manifest),
    crossPlay: summarizeCrossPlay(report.cross_play_results ?? {}, "blocked_factorial_llm"),
    logSummary: summarizeFactorialDiagnostics(report, logs),
    methodNotes: FACTORIAL_METHOD_NOTES,
  };
}

function buildRawLinks(basePath, manifest) {
  const preferred = ["report.json", "manifest.json", "session_observations.csv", "session_logs.jsonl", "cross_play_results.json", "agent_performance_table.csv"];
  const discovered = [];
  const seen = new Set();

  preferred.forEach((fileName) => {
    discovered.push({ label: fileName, href: `${basePath}/${fileName}` });
    seen.add(fileName);
  });

  Object.values(manifest?.artifacts ?? {}).forEach((item) => {
    const fileName = extractFileName(item?.path);
    if (!fileName || seen.has(fileName)) {
      return;
    }
    discovered.push({ label: fileName, href: `${basePath}/${fileName}` });
    seen.add(fileName);
  });
  return discovered;
}

function resolveStrategyLabel(report, strategyId) {
  const entry = (report.strategy_panel ?? []).find((item) => item.strategy_id === strategyId);
  return entry?.label ?? strategyId;
}

function summarizeCrossPlay(crossPlayResults, studyType) {
  const entries = Object.values(crossPlayResults ?? {});
  if (!entries.length) {
    return {
      lineupRows: [],
      notes: ["표시할 cross-play 결과가 없다."],
    };
  }

  const lineupRows = entries.map((entry) => {
    const profits = Object.entries(entry.profit_by_seat ?? {}).map(([seat, profit]) => ({
      seat: Number(seat),
      profit: Number(profit ?? 0),
      agent: entry.seat_to_name?.[seat] ?? entry.layout?.[Number(seat)] ?? `seat_${seat}`,
    }));
    const winner = profits.reduce((best, item) => (item.profit > best.profit ? item : best), profits[0]);
    const loser = profits.reduce((worst, item) => (item.profit < worst.profit ? item : worst), profits[0]);
    return {
      strategy: entry.strategy_label ?? entry.strategy_id ?? "-",
      layout: Array.isArray(entry.layout) ? entry.layout.join(" / ") : String(entry.layout ?? "-"),
      winner: winner.agent,
      winnerProfit: winner.profit,
      loser: loser.agent,
      loserProfit: loser.profit,
      spread: winner.profit - loser.profit,
    };
  });

  lineupRows.sort((left, right) => right.spread - left.spread);
  const strongest = lineupRows[0];
  const note = studyType === "blocked_factorial_llm"
    ? `${strongest.strategy} 전략의 ${strongest.layout} 셀에서 ${strongest.winner}가 가장 크게 앞섰고 1위-최하위 차이는 ${formatMetric(strongest.spread, "value")}다.`
    : `${strongest.winner}가 가장 크게 앞선 라인업은 ${strongest.layout}이고, 1위와 최하위 차이는 ${formatMetric(strongest.spread, "value")}다.`;

  return {
    lineupRows: lineupRows.slice(0, 12),
    notes: [note, studyType === "blocked_factorial_llm" ? "factorial dashboard는 layout과 strategy를 함께 한 셀로 읽는다." : "좌석은 절대값이 아니라 상대 위치라서, 별도 좌석 민감도 표는 숨겼다."],
  };
}

function summarizeLegacyLogs(logs) {
  const eventCounts = new Map();
  const groupedIncidents = new Map();

  logs.forEach((entry) => {
    const event = stripEventType(entry.event ?? "UNKNOWN");
    eventCounts.set(event, (eventCounts.get(event) ?? 0) + 1);

    if (entry.event === "EventType.SHOWDOWN_EVAL") {
      const key = [
        entry.layout_id,
        entry.session_id,
        entry.hand_id,
        entry.seat,
        entry.ev_gain,
        entry.actual_payout,
        entry.counterfactual_payout,
      ].join("|");
      if (!groupedIncidents.has(key)) {
        groupedIncidents.set(key, {
          agent: entry.layout?.[entry.seat] ?? `seat_${entry.seat}`,
          layout: entry.layout?.join(" / ") ?? "-",
          handId: entry.hand_id,
          sessionId: entry.session_id,
          evGain: entry.ev_gain,
          actualPayout: entry.actual_payout,
          counterfactualPayout: entry.counterfactual_payout,
          repeats: 0,
        });
      }
      groupedIncidents.get(key).repeats += 1;
    }
  });

  return {
    eventRows: Array.from(eventCounts.entries())
      .filter(([name]) => !name.startsWith("SHOWDOWN"))
      .sort((left, right) => right[1] - left[1]),
    incidents: Array.from(groupedIncidents.values())
      .sort((left, right) => left.evGain - right.evGain || right.repeats - left.repeats)
      .slice(0, 12),
  };
}

function summarizeFactorialDiagnostics(report, logs) {
  const eventCounts = new Map();
  logs.forEach((entry) => {
    const event = stripEventType(entry.event ?? "UNKNOWN");
    eventCounts.set(event, (eventCounts.get(event) ?? 0) + 1);
  });

  const terms = report.rq_model_vs_strategy?.effect_decomposition?.terms ?? {};
  const effectRows = ["model", "strategy", "interaction"].map((term) => ({
    term,
    df: Number(terms[term]?.df ?? NaN),
    sumSquares: Number(terms[term]?.sum_squares ?? NaN),
    meanSquare: Number(terms[term]?.mean_square ?? NaN),
    fStatistic: terms[term]?.f_statistic,
    eta: Number(terms[term]?.partial_eta_squared ?? NaN),
  }));

  return {
    eventRows: Array.from(eventCounts.entries()).sort((left, right) => right[1] - left[1]),
    effectRows,
  };
}

function composeLegacyHeadline({ highestMean, safest, sharpestTail, runName }) {
  const clauses = [];
  clauses.push(`${runName}에서는 ${highestMean?.agent ?? "n/a"}가 평균수익 ${formatMetric(highestMean?.mean_profit, "value")}로 선두다.`);
  if (highestMean?.agent === safest?.agent) {
    clauses.push(`같은 에이전트가 파산확률 ${formatMetric(safest?.ruin_probability, "percent")}도 기록해 수익과 생존성이 같은 축에 있다.`);
  } else {
    clauses.push(`하지만 최저 파산확률은 ${safest?.agent ?? "n/a"}(${formatMetric(safest?.ruin_probability, "percent")})라서 공격성과 방어력이 분리된다.`);
  }
  clauses.push(`${sharpestTail?.agent ?? "n/a"}의 cvar_5가 가장 높아 하위 꼬리구간 방어도 별도 축으로 확인해야 한다.`);
  return clauses.join(" ");
}

function composeFactorialHeadline(runName, dominantMain, modelLeader, strategyLeader) {
  return `${runName} factorial 번들에서는 ${prettyEffectLabel(dominantMain?.term)}가 주효과 우세로 기록됐다. 모델 마진 평균수익 1위는 ${modelLeader?.agent ?? "n/a"}, 전략 마진 평균수익 1위는 ${strategyLeader?.label ?? "n/a"}다.`;
}

function render(model) {
  dom.runLabel.textContent = `Run: ${model.runName}`;
  dom.runTitle.textContent = `${model.runName} 결과 리포트`;

  dom.manifestFacts.innerHTML = model.manifestFacts
    .map((item) => {
      const className = item.multiline ? "fact-list__value fact-list__value--multiline" : "fact-list__value";
      const value = item.multiline
        ? escapeHtml(item.value).replaceAll("\n", "<br>")
        : escapeHtml(item.value);
      return `<dt>${escapeHtml(item.label)}</dt><dd class="${className}">${value}</dd>`;
    })
    .join("");

  dom.rawLinks.innerHTML = model.rawLinks
    .map((item) => `<li><a href="${escapeAttr(item.href)}" target="_blank" rel="noreferrer">${escapeHtml(item.label)}</a></li>`)
    .join("");

  dom.overviewLede.textContent = model.headline;
  dom.signalGrid.innerHTML = model.overviewSignals
    .map(
      (signal) => `
        <article class="signal">
          <p class="signal__label">${escapeHtml(signal.label)}</p>
          <p class="signal__value">${escapeHtml(signal.value)}</p>
          <p class="signal__meta">${escapeHtml(signal.meta)}</p>
        </article>
      `
    )
    .join("");

  renderCallouts(dom.overviewNotes, model.overviewNotes);
  renderRiskReturnPlot(model.agentRows, model.studyType);
  renderAgentTable(model.agentRows, model.metricColumns);
  renderLineupTable(model.crossPlay.lineupRows, model.studyType);
  renderCallouts(dom.crossPlayNotes, model.crossPlay.notes);
  renderEventBars(model.logSummary.eventRows);
  renderShowdownTable(model.agentRows, model.studyType);
  renderIncidentTable(model.logSummary, model.studyType);
  renderMethodNotes(model.methodNotes);
}

function renderRiskReturnPlot(agentRows, studyType) {
  if (!agentRows.length) {
    dom.riskReturnPlot.innerHTML = "<p>표시할 에이전트 요약이 없다.</p>";
    return;
  }

  const width = 900;
  const height = 440;
  const padding = { top: 40, right: 38, bottom: 56, left: 78 };
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const xValues = agentRows.map((row) => Number(row.mean_profit ?? 0));
  const yValues = agentRows.map((row) => Number(row.cvar_5 ?? 0));
  const sizeValues = agentRows.map((row) => {
    const value = Number(row.variance);
    if (Number.isFinite(value)) {
      return value;
    }
    return Number(row.block_count ?? row.sample_count ?? 1);
  });

  const xMin = Math.min(...xValues);
  const xMax = Math.max(...xValues);
  const yMin = Math.min(...yValues);
  const yMax = Math.max(...yValues);
  const sizeMin = Math.min(...sizeValues);
  const sizeMax = Math.max(...sizeValues);

  const scaleX = (value) => padding.left + normalize(value, xMin, xMax === xMin ? xMin + 1 : xMax) * plotWidth;
  const scaleY = (value) => padding.top + (1 - normalize(value, yMin, yMax === yMin ? yMin + 1 : yMax)) * plotHeight;
  const scaleR = (value) => 9 + normalize(value, sizeMin, sizeMax === sizeMin ? sizeMin + 1 : sizeMax) * 18;

  const xTicks = buildTicks(xMin, xMax, 5);
  const yTicks = buildTicks(yMin, yMax, 5);

  const points = agentRows
    .map((row, index) => {
      const x = scaleX(Number(row.mean_profit ?? 0));
      const y = scaleY(Number(row.cvar_5 ?? 0));
      const r = scaleR(sizeValues[index]);
      const color = pickAgentColor(index);
      return `
        <g>
          <circle cx="${x}" cy="${y}" r="${r}" fill="${color.fill}" stroke="${color.stroke}" stroke-width="1.5"></circle>
        </g>
      `;
    })
    .join("");

  const xAxisTicks = xTicks
    .map((value) => {
      const x = scaleX(value);
      return `
        <g>
          <line x1="${x}" y1="${padding.top}" x2="${x}" y2="${height - padding.bottom}" stroke="rgba(24,20,17,0.1)"></line>
          <text x="${x}" y="${height - padding.bottom + 24}" text-anchor="middle" font-size="11" font-family="var(--mono)" fill="#625950">${formatMetric(value, "value")}</text>
        </g>
      `;
    })
    .join("");

  const yAxisTicks = yTicks
    .map((value) => {
      const y = scaleY(value);
      return `
        <g>
          <line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" stroke="rgba(24,20,17,0.1)"></line>
          <text x="${padding.left - 10}" y="${y + 4}" text-anchor="end" font-size="11" font-family="var(--mono)" fill="#625950">${formatMetric(value, "value")}</text>
        </g>
      `;
    })
    .join("");

  const sizeLabel = studyType === "blocked_factorial_llm" ? "block/sample count" : "variance";
  const xLabel = studyType === "blocked_factorial_llm" ? "model-marginal mean_profit →" : "mean_profit →";
  const yLabel = studyType === "blocked_factorial_llm" ? "model-marginal cvar_5 →" : "cvar_5 →";

  dom.riskReturnPlot.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="risk-return plot">
      <rect x="${padding.left}" y="${padding.top}" width="${plotWidth}" height="${plotHeight}" fill="rgba(255,255,255,0.65)" stroke="rgba(24,20,17,0.16)"></rect>
      ${xAxisTicks}
      ${yAxisTicks}
      <line x1="${padding.left}" y1="${height - padding.bottom}" x2="${width - padding.right}" y2="${height - padding.bottom}" stroke="#181411"></line>
      <line x1="${padding.left}" y1="${padding.top}" x2="${padding.left}" y2="${height - padding.bottom}" stroke="#181411"></line>
      <text x="${width / 2}" y="${height - 12}" text-anchor="middle" font-size="12" font-family="var(--sans)" fill="#625950">${xLabel}</text>
      <text x="20" y="${height / 2}" text-anchor="middle" transform="rotate(-90 20 ${height / 2})" font-size="12" font-family="var(--sans)" fill="#625950">${yLabel}</text>
      <text x="${width - padding.right}" y="22" text-anchor="end" font-size="12" font-family="var(--sans)" fill="#625950">점 크기 = ${sizeLabel}</text>
      ${points}
    </svg>
    <div class="plot-legend">
      ${agentRows
        .map((row, index) => {
          const color = pickAgentColor(index);
          const sizeMeta = studyType === "blocked_factorial_llm"
            ? `blocks ${formatMetric(row.block_count, "count")} / samples ${formatMetric(row.sample_count, "count")}`
            : `σ² ${formatMetric(row.variance, "value")}`;
          return `
            <div class="plot-legend__item">
              <span class="plot-legend__swatch" style="background:${color.fill}; color:${color.stroke}"></span>
              <div class="plot-legend__name">${escapeHtml(row.agent)}</div>
              <div class="plot-legend__meta">${formatMetric(row.mean_profit, "value")} / ${formatMetric(row.cvar_5, "value")} / ${sizeMeta}</div>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderAgentTable(agentRows, metricColumns) {
  dom.agentTableHead.innerHTML = `
    <tr>
      <th>Rank</th>
      <th>Agent</th>
      ${metricColumns.map((column) => `<th title="${escapeHtml(column.title ?? column.label)}">${column.label}</th>`).join("")}
    </tr>
  `;

  if (!agentRows.length) {
    dom.agentTableBody.innerHTML = `<tr><td colspan="${metricColumns.length + 2}">표시할 요약이 없다.</td></tr>`;
    return;
  }

  dom.agentTableBody.innerHTML = agentRows
    .map((row) => {
      const metricCells = metricColumns.map((column) => {
        const rawValue = Number(row[column.key]);
        const className = metricTone(column, rawValue, agentRows);
        return `<td class="numeric ${className}">${formatMetric(rawValue, column.mode)}</td>`;
      }).join("");
      return `
        <tr>
          <td class="rank">${row.rank}</td>
          <td class="metric-name">${escapeHtml(row.agent)}</td>
          ${metricCells}
        </tr>
      `;
    })
    .join("");
}

function renderLineupTable(lineupRows, studyType) {
  if (studyType === "blocked_factorial_llm") {
    dom.lineupTableHead.innerHTML = `
      <tr>
        <th>Strategy</th>
        <th>Layout</th>
        <th>Winner</th>
        <th>Winner Profit</th>
        <th>Spread</th>
      </tr>
    `;
    dom.lineupTableBody.innerHTML = lineupRows
      .map(
        (row) => `
          <tr>
            <td>${escapeHtml(row.strategy)}</td>
            <td>${escapeHtml(row.layout)}</td>
            <td class="metric-name">${escapeHtml(row.winner)}</td>
            <td class="numeric">${formatMetric(row.winnerProfit, "value")}</td>
            <td class="numeric">${formatMetric(row.spread, "value")}</td>
          </tr>
        `
      )
      .join("");
    return;
  }

  dom.lineupTableHead.innerHTML = `
    <tr>
      <th>Layout</th>
      <th>Winner</th>
      <th>Winner Profit</th>
      <th>Loser</th>
      <th>Spread</th>
    </tr>
  `;
  dom.lineupTableBody.innerHTML = lineupRows
    .map(
      (row) => `
        <tr>
          <td>${escapeHtml(row.layout)}</td>
          <td class="metric-name">${escapeHtml(row.winner)}</td>
          <td class="numeric">${formatMetric(row.winnerProfit, "value")}</td>
          <td>${escapeHtml(row.loser)}</td>
          <td class="numeric">${formatMetric(row.spread, "value")}</td>
        </tr>
      `
    )
    .join("");
}

function renderEventBars(eventRows) {
  if (!eventRows.length) {
    dom.eventBars.innerHTML = "<p>표시할 이벤트 카운트가 없다.</p>";
    return;
  }

  const maxCount = Math.max(...eventRows.map((item) => item[1]), 1);
  dom.eventBars.innerHTML = eventRows
    .slice(0, 8)
    .map(([name, count]) => {
      const width = (count / maxCount) * 100;
      return `
        <article class="event-bar">
          <div class="event-bar__label">${escapeHtml(name)}</div>
          <div class="event-bar__track">
            <div class="event-bar__fill" style="width:${width}%"></div>
          </div>
          <div class="event-bar__value">${formatInt(count)}</div>
        </article>
      `;
    })
    .join("");
}

function renderShowdownTable(agentRows, studyType) {
  if (studyType === "blocked_factorial_llm") {
    dom.showdownTableHead.innerHTML = `
      <tr>
        <th>Model</th>
        <th>Mean</th>
        <th>CVaR</th>
        <th>Ruin</th>
        <th>Samples</th>
        <th>Blocks</th>
      </tr>
    `;
    dom.showdownTableBody.innerHTML = agentRows
      .map(
        (row) => `
          <tr>
            <td class="metric-name">${escapeHtml(row.agent)}</td>
            <td class="numeric">${formatMetric(Number(row.mean_profit), "value")}</td>
            <td class="numeric">${formatMetric(Number(row.cvar_5), "value")}</td>
            <td class="numeric">${formatMetric(Number(row.ruin_probability), "percent")}</td>
            <td class="numeric">${formatMetric(Number(row.sample_count), "count")}</td>
            <td class="numeric">${formatMetric(Number(row.block_count), "count")}</td>
          </tr>
        `
      )
      .join("");
    return;
  }

  dom.showdownTableHead.innerHTML = `
    <tr>
      <th>Agent</th>
      <th>Proposal</th>
      <th>Accept</th>
      <th>Reject</th>
      <th>EV Gain</th>
      <th>Misplay</th>
    </tr>
  `;
  dom.showdownTableBody.innerHTML = agentRows
    .map(
      (row) => `
        <tr>
          <td class="metric-name">${escapeHtml(row.agent)}</td>
          <td class="numeric">${formatMetric(Number(row.proposal_rate), "ratio")}</td>
          <td class="numeric">${formatMetric(Number(row.accept_rate), "percent")}</td>
          <td class="numeric">${formatMetric(Number(row.reject_rate), "percent")}</td>
          <td class="numeric ${Number(row.showdown_ev_gain) >= 0 ? "positive" : "negative"}">${formatMetric(Number(row.showdown_ev_gain), "value")}</td>
          <td class="numeric ${Number(row.showdown_misplay_rate) <= 0.2 ? "positive" : "negative"}">${formatMetric(Number(row.showdown_misplay_rate), "percent")}</td>
        </tr>
      `
    )
    .join("");
}

function renderIncidentTable(logSummary, studyType) {
  if (studyType === "blocked_factorial_llm") {
    const rows = logSummary.effectRows ?? [];
    dom.incidentTableHead.innerHTML = `
      <tr>
        <th>Term</th>
        <th>df</th>
        <th>SS</th>
        <th>MS</th>
        <th>η²_p</th>
        <th>F</th>
      </tr>
    `;
    dom.incidentTableBody.innerHTML = rows
      .map(
        (row) => `
          <tr>
            <td class="metric-name">${escapeHtml(prettyEffectLabel(row.term))}</td>
            <td class="numeric">${formatMetric(row.df, "count")}</td>
            <td class="numeric">${formatMetric(row.sumSquares, "value")}</td>
            <td class="numeric">${formatMetric(row.meanSquare, "value")}</td>
            <td class="numeric ${row.eta >= 0.5 ? "positive" : row.eta <= 0.05 ? "negative" : ""}">${formatMetric(row.eta, "value")}</td>
            <td class="numeric">${formatMetric(Number(row.fStatistic), "value")}</td>
          </tr>
        `
      )
      .join("");
    return;
  }

  const incidents = logSummary.incidents ?? [];
  dom.incidentTableHead.innerHTML = `
    <tr>
      <th>Agent</th>
      <th>EV Gain</th>
      <th>Actual</th>
      <th>Counterfactual</th>
      <th>Repeats</th>
      <th>Case</th>
    </tr>
  `;
  dom.incidentTableBody.innerHTML = incidents
    .map(
      (incident) => `
        <tr>
          <td class="metric-name">${escapeHtml(incident.agent)}</td>
          <td class="numeric negative">${formatMetric(Number(incident.evGain), "value")}</td>
          <td class="numeric">${formatMetric(Number(incident.actualPayout), "value")}</td>
          <td class="numeric">${formatMetric(Number(incident.counterfactualPayout), "value")}</td>
          <td class="numeric">${formatInt(incident.repeats)}</td>
          <td>${escapeHtml(`${incident.layout} / session ${incident.sessionId} / hand ${incident.handId}`)}</td>
        </tr>
      `
    )
    .join("");
}

function renderMethodNotes(notes) {
  dom.methodGrid.innerHTML = notes.map(
    (note) => `
      <article class="method">
        <h4>${escapeHtml(note.title)}</h4>
        <p>${escapeHtml(note.description)}</p>
      </article>
    `
  ).join("");
}

function renderCallouts(target, notes) {
  target.innerHTML = notes
    .map(
      (note, index) => `
        <article class="callout">
          <div class="callout__index">${String(index + 1).padStart(2, "0")}</div>
          <p>${escapeHtml(note)}</p>
        </article>
      `
    )
    .join("");
}

function renderError(runName, error) {
  dom.runLabel.textContent = `Run: ${runName}`;
  dom.runTitle.textContent = `${runName} 결과를 불러오지 못함`;
  dom.errorPanel.classList.remove("hidden");
  const localFileHint = window.location.protocol === "file:" ? "file://로 직접 열면 fetch가 막힐 수 있다. 로컬 서버로 열어야 한다." : "";
  dom.errorText.textContent = `${error.message}. ${localFileHint}`.trim();
  setStatus("로드 실패");
}

function hideError() {
  dom.errorPanel.classList.add("hidden");
  dom.errorText.textContent = "";
}

function updateRawLinks(basePath) {
  dom.rawLinks.innerHTML = [
    { label: "report.json", href: `${basePath}/report.json` },
    { label: "manifest.json", href: `${basePath}/manifest.json` },
    { label: "session_observations.csv", href: `${basePath}/session_observations.csv` },
    { label: "session_logs.jsonl", href: `${basePath}/session_logs.jsonl` },
  ]
    .map((item) => `<li><a href="${escapeAttr(item.href)}" target="_blank" rel="noreferrer">${escapeHtml(item.label)}</a></li>`)
    .join("");
}

function updateQuery(runName) {
  const url = new URL(window.location.href);
  url.searchParams.set("run", runName);
  window.history.replaceState({}, "", url);
}

function setStatus(message) {
  dom.statusText.textContent = message;
}

function initSectionSpy() {
  const links = Array.from(document.querySelectorAll(".section-nav a"));
  const sections = links
    .map((link) => document.querySelector(link.getAttribute("href")))
    .filter(Boolean);

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) {
          return;
        }
        const activeId = `#${entry.target.id}`;
        links.forEach((link) => {
          link.classList.toggle("is-active", link.getAttribute("href") === activeId);
        });
      });
    },
    { rootMargin: "-35% 0px -55% 0px", threshold: 0.05 }
  );

  sections.forEach((section) => observer.observe(section));
}

function pickBy(rows, metric, mode, tieBreakers = []) {
  const compare = mode === "max"
    ? (left, right) => left > right
    : (left, right) => left < right;

  return rows.reduce((best, row) => {
    const rowValue = Number(row?.[metric]);
    if (!Number.isFinite(rowValue)) {
      return best;
    }
    if (!best) {
      return row;
    }
    const bestValue = Number(best?.[metric]);
    if (!Number.isFinite(bestValue) || compare(rowValue, bestValue)) {
      return row;
    }
    if (rowValue === bestValue) {
      for (const tieBreaker of tieBreakers) {
        const leftTie = Number(row?.[tieBreaker]);
        const rightTie = Number(best?.[tieBreaker]);
        if (Number.isFinite(leftTie) && Number.isFinite(rightTie)) {
          if (leftTie > rightTie) {
            return row;
          }
          if (leftTie < rightTie) {
            return best;
          }
        }
      }
    }
    return best;
  }, null);
}

function metricTone(column, value, rows) {
  if (!Number.isFinite(value)) {
    return "";
  }
  const values = rows.map((row) => Number(row[column.key])).filter(Number.isFinite);
  if (!values.length) {
    return "";
  }
  const best = column.better === "lower" ? Math.min(...values) : Math.max(...values);
  const worst = column.better === "lower" ? Math.max(...values) : Math.min(...values);
  if (value === best) {
    return "positive";
  }
  if (value === worst) {
    return "negative";
  }
  return "";
}

function stripEventType(name) {
  return String(name).replace(/^EventType\./, "");
}

function pickAgentColor(index) {
  const palette = [
    { fill: "rgba(143, 59, 29, 0.20)", stroke: "#8f3b1d" },
    { fill: "rgba(36, 92, 72, 0.20)", stroke: "#245c48" },
    { fill: "rgba(13, 92, 154, 0.16)", stroke: "#0d5c9a" },
    { fill: "rgba(104, 77, 146, 0.18)", stroke: "#684d92" },
  ];
  return palette[index % palette.length];
}

function buildTicks(min, max, count) {
  if (min === max) {
    return [min];
  }
  const ticks = [];
  for (let index = 0; index < count; index += 1) {
    ticks.push(min + ((max - min) * index) / (count - 1));
  }
  return ticks;
}

function normalize(value, min, max) {
  if (max === min) {
    return 0.5;
  }
  return (value - min) / (max - min);
}

function formatMetric(value, mode) {
  if (!Number.isFinite(value)) {
    return "n/a";
  }
  if (mode === "percent") {
    return `${(value * 100).toFixed(value < 0.1 ? 1 : 0)}%`;
  }
  if (mode === "ratio") {
    if (value === 0) {
      return "0.00";
    }
    return value >= 1000 || Math.abs(value) < 0.01 ? value.toExponential(2) : value.toFixed(2);
  }
  if (mode === "count") {
    return formatInt(value);
  }
  if (Math.abs(value) >= 1_000_000 || (Math.abs(value) > 0 && Math.abs(value) < 0.001)) {
    return value.toExponential(2);
  }
  if (Math.abs(value) >= 1000) {
    return formatInt(value);
  }
  return value.toFixed(Math.abs(value) < 10 ? 2 : 1);
}

function formatInt(value) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: Number.isInteger(value) ? 0 : 1,
  }).format(value);
}

function prettyEffectLabel(term) {
  if (term === "model") return "Model";
  if (term === "strategy") return "Strategy";
  if (term === "interaction") return "Interaction";
  return String(term ?? "n/a");
}

function extractFileName(path) {
  const value = String(path ?? "").trim();
  if (!value) {
    return "";
  }
  const parts = value.split("/");
  return parts[parts.length - 1];
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttr(value) {
  return escapeHtml(value);
}
