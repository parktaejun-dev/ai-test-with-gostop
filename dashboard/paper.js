const qwenRows = [
  {
    model: "qwen3.5-397b-a17b",
    params: "397B / A17B",
    meanProfit: 996.25,
    cvar5: -1850.08,
    winRate: 0.3021,
    samples: 48,
    leader: true,
  },
  {
    model: "qwen3.5-122b-a10b",
    params: "122B / A10B",
    meanProfit: -51.75,
    cvar5: -4145.33,
    winRate: 0.3542,
    samples: 48,
  },
  {
    model: "qwen3-coder-480b-a35b-instruct",
    params: "480B / A35B",
    meanProfit: -198.92,
    cvar5: -5084.75,
    winRate: 0.2396,
    samples: 48,
  },
  {
    model: "qwen3-coder-30b-a3b-instruct",
    params: "30B / A3B",
    meanProfit: -745.58,
    cvar5: -5269.25,
    winRate: 0.1042,
    samples: 48,
  },
];

const nvidiaRows = [
  {
    model: "nvidia/nemotron-3-super-120b-a12b",
    scale: "~120B",
    meanProfit: 500.65,
    cvar5: -1384.17,
    winRate: 0.2708,
    samples: 48,
    leader: true,
  },
  {
    model: "mistralai/mistral-small-4-119b-2603",
    scale: "~119B",
    meanProfit: -73.19,
    cvar5: -4150.0,
    winRate: 0.2917,
    samples: 48,
  },
  {
    model: "qwen/qwen3.5-122b-a10b",
    scale: "122B",
    meanProfit: -172.85,
    cvar5: -3350.42,
    winRate: 0.1875,
    samples: 48,
  },
  {
    model: "stockmark/stockmark-2-100b-instruct",
    scale: "~100B",
    meanProfit: -254.6,
    cvar5: -4267.08,
    winRate: 0.25,
    samples: 48,
  },
];

const tinyNvidiaRows = [
  {
    model: "ibm/granite-3.0-3b-a800m-instruct",
    scale: "3B / A800M",
    meanProfit: 381.25,
    cvar5: -1966.67,
    winRate: 0.3125,
    samples: 48,
    leader: true,
  },
  {
    model: "meta/llama-3.2-1b-instruct",
    scale: "1B",
    meanProfit: -20.83,
    cvar5: -2083.33,
    winRate: 0.2708,
    samples: 48,
  },
  {
    model: "google/gemma-2-2b-it",
    scale: "2B",
    meanProfit: -68.75,
    cvar5: -3833.33,
    winRate: 0.25,
    samples: 48,
  },
  {
    model: "microsoft/phi-4-mini-instruct",
    scale: "mini",
    meanProfit: -291.67,
    cvar5: -3916.67,
    winRate: 0.1667,
    samples: 48,
  },
];

const qwenPolicyRows = [
  { policyKo: "균형", policyEn: "Balanced", model: "qwen3-4b", meanProfit: 224.88, cvar5: -1166.67 },
  { policyKo: "분석", policyEn: "Analytic", model: "qwen3-4b", meanProfit: 412.33, cvar5: -2566.83 },
  { policyKo: "보수", policyEn: "Conservative", model: "qwen3-8b", meanProfit: 238.08, cvar5: -1301.67 },
  { policyKo: "공격", policyEn: "Aggressive", model: "qwen3-14b", meanProfit: 254.08, cvar5: -1284.33 },
];

const nvidiaPolicyRows = [
  {
    policyKo: "균형",
    policyEn: "Balanced",
    model: "nvidia/nemotron-3-super-120b-a12b",
    meanProfit: 645.17,
    cvar5: -2067.0,
  },
  {
    policyKo: "분석",
    policyEn: "Analytic",
    model: "nvidia/nemotron-3-super-120b-a12b",
    meanProfit: 598.92,
    cvar5: -2067.0,
  },
  {
    policyKo: "보수",
    policyEn: "Conservative",
    model: "nvidia/nemotron-3-super-120b-a12b",
    meanProfit: 416.67,
    cvar5: -1850.0,
  },
  {
    policyKo: "공격",
    policyEn: "Aggressive",
    model: "nvidia/nemotron-3-super-120b-a12b",
    meanProfit: 598.83,
    cvar5: -3701.67,
  },
];

document.addEventListener("DOMContentLoaded", () => {
  renderRows("qwen-table-ko", qwenRows, "params");
  renderRows("qwen-table-en", qwenRows, "params");
  renderRows("nvidia-table-ko", nvidiaRows, "scale");
  renderRows("nvidia-table-en", nvidiaRows, "scale");
  renderRows("tiny-nvidia-table-ko", tinyNvidiaRows, "scale");
  renderRows("tiny-nvidia-table-en", tinyNvidiaRows, "scale");
  renderPolicyRows("qwen-policy-table-ko", qwenPolicyRows, "ko");
  renderPolicyRows("qwen-policy-table-en", qwenPolicyRows, "en");
  renderPolicyRows("nvidia-policy-table-ko", nvidiaPolicyRows, "ko");
  renderPolicyRows("nvidia-policy-table-en", nvidiaPolicyRows, "en");
  document.querySelector("#render-date").textContent = new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());
});

function renderRows(tableId, rows, scaleKey) {
  const tbody = document.querySelector(`#${tableId} tbody`);
  tbody.innerHTML = rows
    .map(
      (row) => `
        <tr${row.leader ? ' class="leader"' : ""}>
          <td class="model-name">${escapeHtml(row.model)}</td>
          <td>${escapeHtml(row[scaleKey])}</td>
          <td>${formatNumber(row.meanProfit)}</td>
          <td>${formatNumber(row.cvar5)}</td>
          <td>${formatRate(row.winRate)}</td>
          <td>${row.samples}</td>
        </tr>
      `
    )
    .join("");
}

function renderPolicyRows(tableId, rows, locale) {
  const tbody = document.querySelector(`#${tableId} tbody`);
  const policyKey = locale === "ko" ? "policyKo" : "policyEn";
  tbody.innerHTML = rows
    .map(
      (row) => `
        <tr>
          <td>${escapeHtml(row[policyKey])}</td>
          <td class="model-name">${escapeHtml(row.model)}</td>
          <td>${formatNumber(row.meanProfit)}</td>
          <td>${formatNumber(row.cvar5)}</td>
        </tr>
      `
    )
    .join("");
}

function formatNumber(value) {
  return Number(value).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatRate(value) {
  return Number(value).toFixed(4);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[char];
  });
}
