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

document.addEventListener("DOMContentLoaded", () => {
  renderRows("qwen-table", qwenRows, "params");
  renderRows("nvidia-table", nvidiaRows, "scale");
  document.querySelector("#render-date").textContent = new Intl.DateTimeFormat("en", {
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
