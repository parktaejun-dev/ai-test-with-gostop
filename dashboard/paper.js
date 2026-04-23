const BUNDLE_INDEX_PATH = "../paper/bundles/index.json";

const SUMMARY = {
  blocked_factorial_llm: {
    en: "This archive page shows the main factorial paper bundle. It emphasizes effect decomposition, model-marginal summaries, and reproducible bundle links over a hero layout.",
    kr: "이 아카이브는 factorial 메인 논문 번들을 보여준다. 히어로형 요약 대신 효과크기 분해, 모델 마진 요약, 재현 가능한 번들 링크를 앞세운다.",
  },
  baseline: {
    en: "This archive page shows the appendix calibration bundle. It preserves the original baseline benchmark figures and artifact trail in a document-style layout.",
    kr: "이 아카이브는 appendix calibration 번들을 보여준다. 기존 baseline benchmark 그림과 아티팩트 경로를 문서형 화면에 보존한다.",
  },
};

document.addEventListener("DOMContentLoaded", init);

async function init() {
  try {
    const bundleIndex = await fetchJson(BUNDLE_INDEX_PATH);
    const bundleId = resolveBundleId(bundleIndex);
    const bundle = bundleIndex.bundles?.[bundleId];
    if (!bundle) {
      throw new Error(`bundle not found: ${bundleId}`);
    }

    const [report, manifest, assetManifest] = await Promise.all([
      fetchJson(bundle.report_path),
      fetchJson(bundle.manifest_path),
      fetchJson(bundle.asset_manifest_path),
    ]);

    renderTopbar(bundle);
    renderRecord(report, manifest, bundle, assetManifest);
    renderAbstract(bundle.study_type);
    renderFindings(report, bundle);
    renderAgentTable(report, bundle.study_type);
    renderFigures(assetManifest);
    renderArtifacts(manifest, assetManifest);
    renderSourceFiles(manifest, assetManifest);
    revealSections();
    setStatus(`${bundle.label} loaded`);
  } catch (error) {
    showError(error);
  }
}

function resolveBundleId(bundleIndex) {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("bundle");
  if (requested && bundleIndex.bundles?.[requested]) {
    return requested;
  }
  return bundleIndex.default_bundle || Object.keys(bundleIndex.bundles ?? {})[0] || "main";
}

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${path} returned ${response.status}`);
  }
  return response.json();
}

function renderTopbar(bundle) {
  const brand = document.querySelector(".brand");
  const dashboardLink = document.querySelector('[data-nav="dashboard"]');
  const latexLink = document.querySelector('[data-nav="latex"]');
  const summaryLink = document.querySelector('[data-nav="summary"]');
  const reportLink = document.querySelector('[data-nav="report"]');

  brand.href = bundle.dashboard_run ? `index.html?run=${encodeURIComponent(bundle.dashboard_run)}` : "index.html";
  dashboardLink.href = brand.href;
  latexLink.href = "../paper/arxiv_main.tex";
  summaryLink.href = "../paper/bilingual_summary.md";
  reportLink.href = bundle.report_path;
}

function renderRecord(report, manifest, bundle, assetManifest) {
  const sessionCount = Number(manifest.session_observation_count ?? 0);
  const studyType = bundle.study_type === "blocked_factorial_llm" ? "blocked_factorial_llm" : "baseline";
  const facts = studyType === "blocked_factorial_llm"
    ? [
        ["Bundle", bundle.label],
        ["Run", bundle.run_name ?? manifest.run_name ?? bundle.dashboard_run ?? "main"],
        ["Study", report.study_type ?? manifest.config?.experiment ?? "blocked_factorial_llm"],
        ["Models", formatInt(report.model_panel?.length ?? manifest.config?.model_panel?.length ?? 0)],
        ["Strategies", formatInt(report.strategy_panel?.length ?? manifest.config?.strategy_count ?? 0)],
        ["Observations", formatInt(sessionCount)],
      ]
    : [
        ["Bundle", bundle.label],
        ["Run", bundle.run_name ?? manifest.run_name ?? bundle.dashboard_run ?? "appendix"],
        ["Agents", formatInt(manifest.agents?.length ?? 0)],
        ["Lineups", formatInt(manifest.lineup_count ?? 0)],
        ["Observations", formatInt(sessionCount)],
        ["Artifacts", formatInt((assetManifest.artifact_links ?? []).length)],
      ];

  renderDefinitionList("#record-facts", facts);
  renderMetaStrip("#record-meta", facts);
  const invocation = bundle.source_results_dir ? `published from ${bundle.source_results_dir}` : "published bundle";
  document.querySelector("#invocation-text").textContent = invocation;
}

function renderAbstract(studyType) {
  const summary = SUMMARY[studyType === "blocked_factorial_llm" ? "blocked_factorial_llm" : "baseline"];
  document.querySelector("#abstract-en").textContent = summary.en;
  document.querySelector("#abstract-kr").textContent = summary.kr;
}

function renderFindings(report, bundle) {
  const studyType = bundle.study_type;
  const items = studyType === "blocked_factorial_llm"
    ? buildFactorialFindings(report)
    : buildBaselineFindings(report);

  document.querySelector("#finding-lines").innerHTML = items
    .map(
      (item) => `
        <div class="finding-row">
          <div class="finding-row__index">${escapeHtml(item.index)}</div>
          <div class="finding-row__text">${escapeHtml(item.text)}</div>
          <div class="finding-row__tag">${escapeHtml(item.tag)}</div>
        </div>
      `
    )
    .join("");
}

function buildBaselineFindings(report) {
  const rows = buildAgentRows(report);
  const meanLeader = rows[0] ?? null;
  const tailLeader = [...rows].sort((left, right) => Number(right.cvar_5 ?? -Infinity) - Number(left.cvar_5 ?? -Infinity))[0] ?? null;
  const ruinLeader = [...rows].sort((left, right) => Number(left.ruin_probability ?? Infinity) - Number(right.ruin_probability ?? Infinity))[0] ?? null;
  const layoutSummary = report.inferential_statistics?.rq4_layout_effect?.per_agent ?? {};
  const layoutLeader = Object.entries(layoutSummary)
    .map(([agent, summary]) => ({ agent, eta: Number(summary?.eta_squared ?? 0) }))
    .sort((left, right) => right.eta - left.eta)[0] ?? null;

  return [
    { index: "01", text: meanLeader ? `${meanLeader.agent} leads mean profit at ${formatNum(meanLeader.mean_profit)}.` : "Mean-profit ranking unavailable.", tag: "mean" },
    { index: "02", text: tailLeader ? `${tailLeader.agent} has the best CVaR 5% at ${formatNum(tailLeader.cvar_5)}.` : "Tail-risk ranking unavailable.", tag: "cvar" },
    { index: "03", text: ruinLeader ? `${ruinLeader.agent} has the lowest ruin probability at ${formatPct(ruinLeader.ruin_probability)}.` : "Ruin summary unavailable.", tag: "ruin" },
    { index: "04", text: layoutLeader ? `${layoutLeader.agent} shows the strongest layout sensitivity (eta² ${formatNum(layoutLeader.eta)}).` : "Layout-effect summary unavailable.", tag: "layout" },
  ];
}

function buildFactorialFindings(report) {
  const rows = buildAgentRows(report);
  const meanLeader = rows[0] ?? null;
  const effect = report.rq_model_vs_strategy?.effect_decomposition ?? {};
  const terms = effect.terms ?? {};
  const dominantMain = effect.dominant_main_effect ?? { term: "n/a", partial_eta_squared: NaN };
  const byStrategy = report.rq_model_vs_strategy?.mean_profit?.by_strategy ?? {};
  const strategyLeader = Object.entries(byStrategy)
    .map(([strategyId, summary]) => ({ strategyId, label: resolveStrategyLabel(report, strategyId), estimate: Number(summary?.estimate ?? NaN) }))
    .sort((left, right) => right.estimate - left.estimate)[0] ?? null;
  const safest = [...rows].sort((left, right) => Number(left.ruin_probability ?? Infinity) - Number(right.ruin_probability ?? Infinity))[0] ?? null;

  return [
    { index: "01", text: `${prettyEffectLabel(dominantMain.term)} is the dominant main effect (η²p ${formatNum(dominantMain.partial_eta_squared)}).`, tag: "main" },
    { index: "02", text: `Model η²p = ${formatNum(terms.model?.partial_eta_squared)}, strategy η²p = ${formatNum(terms.strategy?.partial_eta_squared)}, interaction η²p = ${formatNum(terms.interaction?.partial_eta_squared)}.`, tag: "eta" },
    { index: "03", text: meanLeader ? `${meanLeader.agent} leads model-marginal mean profit at ${formatNum(meanLeader.mean_profit)}.` : "Model summary unavailable.", tag: "model" },
    { index: "04", text: strategyLeader ? `${strategyLeader.label} leads strategy-marginal mean profit at ${formatNum(strategyLeader.estimate)}; lowest ruin remains ${safest?.agent ?? "n/a"} at ${formatPct(safest?.ruin_probability)}.` : "Strategy summary unavailable.", tag: "strategy" },
  ];
}

function renderAgentTable(report, studyType) {
  const rows = buildAgentRows(report);
  const tableHead = document.querySelector("#agent-table thead");
  const tableBody = document.querySelector("#agent-table tbody");

  if (studyType === "blocked_factorial_llm") {
    tableHead.innerHTML = `
      <tr>
        <th>Rank</th>
        <th>Model</th>
        <th>Mean profit</th>
        <th>CVaR 5%</th>
        <th>Ruin</th>
        <th>Samples</th>
        <th>Blocks</th>
      </tr>
    `;
    tableBody.innerHTML = rows
      .map(
        (row) => `
          <tr>
            <td>${escapeHtml(formatInt(row.rank))}</td>
            <td>${escapeHtml(row.agent ?? "")}</td>
            <td>${escapeHtml(formatNum(row.mean_profit))}</td>
            <td>${escapeHtml(formatNum(row.cvar_5))}</td>
            <td>${escapeHtml(formatPct(row.ruin_probability))}</td>
            <td>${escapeHtml(formatInt(row.sample_count ?? 0))}</td>
            <td>${escapeHtml(formatInt(row.block_count ?? 0))}</td>
          </tr>
        `
      )
      .join("");
    return;
  }

  tableHead.innerHTML = `
    <tr>
      <th>Rank</th>
      <th>Agent</th>
      <th>Mean profit</th>
      <th>CVaR 5%</th>
      <th>Ruin</th>
      <th>Win rate</th>
    </tr>
  `;
  tableBody.innerHTML = rows
    .map(
      (row) => `
        <tr>
          <td>${escapeHtml(formatInt(row.rank))}</td>
          <td>${escapeHtml(row.agent ?? "")}</td>
          <td>${escapeHtml(formatNum(row.mean_profit))}</td>
          <td>${escapeHtml(formatNum(row.cvar_5))}</td>
          <td>${escapeHtml(formatPct(row.ruin_probability))}</td>
          <td>${escapeHtml(formatPct(row.win_rate))}</td>
        </tr>
      `
    )
    .join("");
}

function renderFigures(assetManifest) {
  const grid = document.querySelector("#figure-grid");
  const figures = assetManifest?.figures ?? [];
  grid.innerHTML = figures
    .map(
      (figure) => `
        <figure class="figure-card">
          <img src="${escapeAttr(figure.path)}" alt="${escapeAttr(figure.title)}" loading="lazy" />
          <figcaption>
            <span class="figure-card__title">${escapeHtml(figure.title)}</span>
            <span>${escapeHtml(figure.caption ?? figure.key ?? "")}</span>
          </figcaption>
        </figure>
      `
    )
    .join("");
}

function renderArtifacts(manifest, assetManifest) {
  const grid = document.querySelector("#artifact-grid");
  const rows = assetManifest?.artifact_links ?? [];
  grid.innerHTML = rows
    .map((item) => {
      const checksum = String(item?.sha256 ?? "").trim();
      return `
        <div class="artifact-row">
          <div>
            <strong><a href="${escapeAttr(item.path)}" target="_blank" rel="noreferrer">${escapeHtml(item.label)}</a></strong>
            <span>${escapeHtml(item.path)}</span>
          </div>
          <div class="artifact-row__meta">${escapeHtml(checksum ? checksum.slice(0, 12) : "bundle")}</div>
        </div>
      `;
    })
    .join("");
}

function renderSourceFiles(manifest, assetManifest) {
  const root = document.querySelector("#source-files");
  const lines = [];
  Object.values(manifest?.artifacts ?? {}).forEach((artifact) => {
    const fileName = extractFileName(artifact?.path);
    if (fileName) {
      lines.push({ label: fileName, path: artifact.path });
    }
  });
  Object.entries(assetManifest?.sources ?? {}).forEach(([label, path]) => {
    lines.push({ label, path });
  });
  root.innerHTML = lines
    .map((item) => `<li><span>${escapeHtml(item.label)}</span><small>${escapeHtml(String(item.path))}</small></li>`)
    .join("");
}

function renderDefinitionList(selector, pairs) {
  const root = document.querySelector(selector);
  if (!root) {
    return;
  }
  root.innerHTML = pairs
    .map(
      ([label, value]) => `
        <div>
          <dt>${escapeHtml(label)}</dt>
          <dd>${escapeHtml(value)}</dd>
        </div>
      `
    )
    .join("");
}

function renderMetaStrip(selector, pairs) {
  const root = document.querySelector(selector);
  if (!root) {
    return;
  }
  root.innerHTML = pairs
    .map(
      ([label, value]) => `
        <div class="meta-item">
          <div class="meta-item__label">${escapeHtml(label)}</div>
          <div class="meta-item__value">${escapeHtml(value)}</div>
        </div>
      `
    )
    .join("");
}

function buildAgentRows(report) {
  const rankings = report.ranking ?? [];
  const rankMap = new Map(rankings.map((entry, index) => [entry.agent, index + 1]));
  return Object.entries(report.agent_performance_table ?? {})
    .map(([agent, summary]) => ({ agent, ...summary, rank: rankMap.get(agent) ?? 0 }))
    .sort((left, right) => left.rank - right.rank || String(left.agent).localeCompare(String(right.agent)));
}

function resolveStrategyLabel(report, strategyId) {
  const entry = (report.strategy_panel ?? []).find((item) => item.strategy_id === strategyId);
  return entry?.label ?? strategyId;
}

function countArtifacts(manifest) {
  return Object.keys(manifest?.artifacts ?? {}).length;
}

function truncate(value, maxLength) {
  const text = String(value ?? "");
  if (text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength - 1)}…`;
}

function extractFileName(path) {
  const value = String(path ?? "").trim();
  if (!value) {
    return "";
  }
  const parts = value.split("/");
  return parts[parts.length - 1];
}

function prettyEffectLabel(term) {
  if (term === "model") return "Model";
  if (term === "strategy") return "Strategy";
  if (term === "interaction") return "Interaction";
  return String(term ?? "n/a");
}

function formatNum(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) {
    return "n/a";
  }
  if (Math.abs(num) >= 1000) {
    return formatInt(num);
  }
  return num.toFixed(Math.abs(num) < 10 ? 2 : 1);
}

function formatPct(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) {
    return "n/a";
  }
  return `${(num * 100).toFixed(num < 0.1 ? 1 : 0)}%`;
}

function formatInt(value) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: Number.isInteger(value) ? 0 : 1,
  }).format(value);
}

function revealSections() {
  document.querySelectorAll(".section-block, .side-block, .record-head").forEach((node) => {
    node.classList.add("is-visible");
  });
}

function setStatus(message) {
  document.querySelector("#load-status").textContent = message;
}

function showError(error) {
  document.querySelector("#archive-error").classList.remove("hidden");
  document.querySelector("#error-text").textContent = error.message || String(error);
  setStatus("Load failed");
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
