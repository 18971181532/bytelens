"use strict";

/* ----------------------------- utilities ----------------------------- */
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

async function api(path) {
  const res = await fetch(path);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || res.statusText);
  }
  return res.json();
}

function fmtBytes(n) {
  if (n < 1024) return n + " B";
  const u = ["KB", "MB", "GB", "TB"];
  let v = n / 1024, i = 0;
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++; }
  return v.toFixed(v < 10 ? 2 : 1) + " " + u[i];
}

function hex(n) { return "0x" + n.toString(16); }

/* hi-DPI canvas setup. MUST set an explicit CSS height and use the
   six-argument setTransform; reading canvas.height back would multiply
   devicePixelRatio on every resize. */
function fitCanvas(cv, cssH) {
  cv.style.width = "";
  cv.style.height = "";
  const cssW = cv.clientWidth || cv.parentElement.clientWidth || 800;
  cv.style.width = cssW + "px";
  cv.style.height = cssH + "px";
  const dpr = window.devicePixelRatio || 1;
  cv.width = Math.round(cssW * dpr);
  cv.height = Math.round(cssH * dpr);
  const ctx = cv.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, w: cssW, h: cssH };
}

const COL = {
  muted: "#8a96ad", line: "#243049", accent: "#4fc3f7",
  accent2: "#7c83ff", good: "#46d68a", warn: "#f0b849",
  bad: "#f06a6a", purple: "#b388ff", grid: "#1d2638"
};

function heatColor(v) {
  // v in 0..1: dark navy -> cyan -> near-white
  const stops = [
    [13, 16, 26], [20, 45, 80], [30, 110, 150],
    [79, 195, 247], [220, 245, 255]
  ];
  v = Math.max(0, Math.min(1, v));
  const t = v * (stops.length - 1);
  const i = Math.floor(t), f = t - i;
  const a = stops[i], b = stops[Math.min(i + 1, stops.length - 1)];
  const c = a.map((x, k) => Math.round(x + (b[k] - x) * f));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

/* ------------------------------- tabs -------------------------------- */
$$(".tab").forEach((t) => {
  t.addEventListener("click", () => {
    $$(".tab").forEach((x) => x.classList.remove("active"));
    $$(".panel").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    $("#tab-" + t.dataset.tab).classList.add("active");
    dispatchEvent(new Event("tab:" + t.dataset.tab));
  });
});

/* ----------------------------- overview ------------------------------ */
let OVERVIEW = null;

function kvRow(k, v) {
  return `<tr><td>${k}</td><td>${v}</td></tr>`;
}

function drawGauge(ent) {
  const { ctx, w, h } = fitCanvas($("#gaugeCanvas"), 220);
  const cx = w / 2, cy = h - 30, r = Math.min(w, h * 2) / 2 - 24;
  const start = Math.PI, end = 2 * Math.PI;
  ctx.lineCap = "round";
  ctx.lineWidth = 18;
  ctx.beginPath(); ctx.arc(cx, cy, r, start, end);
  ctx.strokeStyle = "#1d2638"; ctx.stroke();
  const frac = ent / 8;
  const grad = ctx.createLinearGradient(cx - r, 0, cx + r, 0);
  grad.addColorStop(0, COL.good);
  grad.addColorStop(0.6, COL.warn);
  grad.addColorStop(1, COL.bad);
  ctx.beginPath();
  ctx.arc(cx, cy, r, start, start + (end - start) * frac);
  ctx.strokeStyle = grad; ctx.stroke();
  ctx.fillStyle = COL.text || "#e4e9f2";
  ctx.fillStyle = "#e4e9f2";
  ctx.font = "bold 42px monospace";
  ctx.textAlign = "center";
  ctx.fillText(ent.toFixed(2), cx, cy - 18);
  ctx.font = "12px monospace";
  ctx.fillStyle = COL.muted;
  ctx.fillText("bits / byte  (0–8)", cx, cy + 6);
}

function drawComposition(comp) {
  const { ctx, w, h } = fitCanvas($("#compCanvas"), 120);
  const rows = [
    ["ASCII printable", comp.printable_ratio, COL.good],
    ["high bytes (≥0x80)", comp.high_ratio, COL.warn],
    ["null bytes", comp.null_ratio, COL.accent2],
    ["control / other", Math.max(0,
        1 - (comp.printable_ratio || 0) - (comp.high_ratio || 0)
          - (comp.null_ratio || 0) - ((comp.whitespace || 0) / comp.total)),
      COL.muted],
  ];
  const labelW = 170, barH = 20, gap = 12;
  rows.forEach((row, i) => {
    const [label, v, color] = row;
    const y = 10 + i * (barH + gap);
    ctx.fillStyle = COL.muted; ctx.font = "12px monospace";
    ctx.textAlign = "left"; ctx.fillText(label, 0, y + 14);
    const bx = labelW, bw = w - labelW - 70;
    ctx.fillStyle = "#1d2638";
    ctx.fillRect(bx, y, bw, barH);
    ctx.fillStyle = color;
    ctx.fillRect(bx, y, Math.max(2, bw * Math.min(1, v)), barH);
    ctx.fillStyle = COL.text; ctx.fillText((v * 100).toFixed(1) + "%",
      bx + bw + 10, y + 14);
  });
}

async function renderOverview() {
  if (!OVERVIEW) OVERVIEW = await api("/api/overview");
  const r = OVERVIEW, f = r.file, m = r.magic, e = r.entropy, c = r.histogram;
  $("#fileName").textContent = `${f.name}  ·  ${f.path}`;
  $("#metaPills").innerHTML = [
    fmtBytes(f.size), m.description, r.truncated ? "head only" : "full"
  ].map((x) => `<span class="pill">${x}</span>`).join("");

  $("#idTable").innerHTML = [
    kvRow("file", f.name),
    kvRow("size", `${f.size} bytes (${fmtBytes(f.size)})`),
    kvRow("analyzed", `${r.analyzed_bytes} bytes`),
    kvRow("magic", `${m.description} <b>.${m.extension}</b>`),
    kvRow("kind", m.kind),
    kvRow("distinct bytes", c.distinct),
    kvRow("strings", r.string_count),
  ].join("");

  $("#embedded").innerHTML = (r.carved && r.carved.length)
    ? "<h2 style='margin-top:14px'>Embedded files</h2>" +
      r.carved.slice(0, 12).map((x) =>
        `<span class="emb-chip">@${x.offset} ${x.extension}${
          x.size ? " " + fmtBytes(x.size) : ""}</span>`).join("")
    : "";

  drawGauge(e.entropy);
  $("#entropyCaption").textContent = e.classification;
  drawComposition(c.composition);

  $("#hashTable").innerHTML = Object.entries(r.hashes)
    .filter(([, v]) => typeof v === "string")
    .map(([k, v]) => kvRow(k, `<span class="mono">${v}</span>`)).join("");
}

/* -------------------------------- hex -------------------------------- */
let hexState = { offset: 0, length: 256 };

function byteClass(b) {
  if (b === 0) return "b-zero";
  if (b >= 128) return "b-high";
  return "b-print";
}

async function renderHex(offset, length) {
  hexState = { offset, length };
  const r = await api(`/api/hex?offset=${offset}&length=${length}`);
  $("#hexInfo").textContent =
    `${r.offset} – ${r.offset + r.length} of ${r.file_size}`;
  $("#hexOffset").value = r.offset;
  $("#hexLength").value = r.length;
  const rows = r.rows.map((row) => {
    const pairs = row.hex.map((hx, i) =>
      `<span class="${byteClass(parseInt(hx, 16))}">${hx}</span>`).join(" ");
    return `<div class="hex-row"><span class="off">${
      row.offset.toString(16).padStart(8, "0")}</span><span class="hexbytes">${
      pairs}</span><span class="ascii">${row.ascii}</span></div>`;
  }).join("");
  $("#hexBody").innerHTML = rows;
  $("#hexNext").disabled = r.next_offset === null;
  $("#hexPrev").disabled = r.prev_offset === null;
}

$("#hexGo").onclick = () =>
  renderHex(+$("#hexOffset").value || 0, +$("#hexLength").value || 256);
$("#hexNext").onclick = () =>
  renderHex(hexState.offset + hexState.length, hexState.length);
$("#hexPrev").onclick = () =>
  renderHex(Math.max(0, hexState.offset - hexState.length), hexState.length);
$("#hexOffset").addEventListener("keydown", (ev) => {
  if (ev.key === "Enter") $("#hexGo").click();
});

/* ------------------------------ strings ------------------------------ */
let stringOffset = 0, stringLimit = 200, stringQ = "";

async function renderStrings(append) {
  const r = await api(`/api/strings?offset=${stringOffset}&limit=${
    stringLimit}&q=${encodeURIComponent(stringQ)}`);
  $("#stringInfo").textContent =
    `${r.total} matches · showing ${Math.min(r.offset + r.limit, r.total)}`;
  const rows = r.strings.map((s) =>
    `<tr><td>${s.offset.toString(16).padStart(8, "0")}</td>` +
    `<td class="enc">${s.encoding}</td><td>${s.length}</td>` +
    `<td>${escapeHtml(s.value)}</td></tr>`).join("");
  const tbody = $("#stringTable tbody");
  if (append) tbody.insertAdjacentHTML("beforeend", rows);
  else tbody.innerHTML = rows;
  stringOffset += r.strings.length;
  $("#stringMore").disabled = stringOffset >= r.total;
}

function escapeHtml(s) {
  return s.replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

$("#stringSearch").addEventListener("input", function () {
  stringQ = this.value; stringOffset = 0;
  clearTimeout(this._t);
  this._t = setTimeout(() => renderStrings(false), 200);
});
$("#stringMore").onclick = () => renderStrings(true);

/* ----------------------------- structure ----------------------------- */
let STRUCT = null;
function renderStructTable(regions) {
  const rows = regions.map((r) =>
    `<tr><td>${r.name}</td><td>${r.start}</td><td>${r.end}</td>` +
    `<td>${r.detail || ""}</td></tr>`).join("");
  $("#structTable tbody").innerHTML = rows;
}

function drawStructMap(regions, fileSize) {
  const cv = $("#structCanvas");
  const { ctx, w, h } = fitCanvas(cv, 140);
  const padL = 8, padR = 8, y = 36, barH = 42;
  const bw = w - padL - padR;
  const palette = [COL.accent, COL.good, COL.warn, COL.purple, COL.accent2,
    COL.bad, "#5dd0c0", "#e08ad0"];
  ctx.fillStyle = "#1d2638";
  ctx.fillRect(padL, y, bw, barH);
  regions.forEach((r, i) => {
    const x0 = padL + (r.start / fileSize) * bw;
    const x1 = padL + (r.end / fileSize) * bw;
    ctx.fillStyle = palette[i % palette.length];
    ctx.fillRect(x0, y, Math.max(1.5, x1 - x0), barH);
    ctx._hit = ctx._hit || [];
  });
  ctx._hit = regions.map((r, i) => ({
    x: padL + (r.start / fileSize) * bw,
    w: Math.max(1.5, (r.end - r.start) / fileSize * bw),
    y, h: barH, region: r, color: palette[i % palette.length]
  }));
  ctx.fillStyle = COL.muted; ctx.font = "11px monospace";
  ctx.textAlign = "left"; ctx.fillText("0", padL, y + barH + 16);
  ctx.textAlign = "right";
  ctx.fillText(fileSize.toString(), padL + bw, y + barH + 16);
  cv.onmousemove = (ev) => {
    const rect = cv.getBoundingClientRect();
    const mx = ev.clientX - rect.left, my = ev.clientY - rect.top;
    const hit = ctx._hit.find((z) =>
      mx >= z.x && mx <= z.x + z.w && my >= z.y && my <= z.y + z.h);
    if (hit) {
      const r = hit.region;
      $("#structHint").textContent =
        `${r.name}  [${r.start}–${r.end}] ${r.detail || ""} (${r.kind})`;
      cv.style.cursor = "pointer";
    } else {
      $("#structHint").textContent = "hover a region to inspect";
      cv.style.cursor = "default";
    }
  };
}

async function renderStructure() {
  if (!STRUCT) STRUCT = await api("/api/structure");
  const f = OVERVIEW ? OVERVIEW.file : null;
  const size = f ? f.size : 1;
  $("#structMeta").innerHTML = Object.entries(STRUCT.meta)
    .filter(([, v]) => v === null ||
      ["string", "number", "boolean"].includes(typeof v))
    .map(([k, v]) => `<span class="pill">${k}: ${v}</span>`).join("");
  renderStructTable(STRUCT.regions);
  drawStructMap(STRUCT.regions, size || 1);
}

/* -------------------------------- map -------------------------------- */
async function renderMap() {
  const m = await api("/api/map");
  drawHeatmap(m.heatmap);
  drawEntropy(m.entropy);
  drawHistogram(m.histogram);
}

function drawHeatmap(hm) {
  const cv = $("#heatCanvas");
  const labelW = 38, topPad = 14;
  const { ctx, w, h } = fitCanvas(cv, 260);
  const gridW = w - labelW - 8;
  const plotH = h - topPad - 18;
  const cw = gridW / hm.columns;
  const ch = plotH / hm.buckets;
  let maxV = 0;
  for (let c = 0; c < hm.columns; c++)
    for (let b = 0; b < hm.buckets; b++)
      maxV = Math.max(maxV, hm.grid[c][b]);
  for (let c = 0; c < hm.columns; c++) {
    for (let b = 0; b < hm.buckets; b++) {
      const v = hm.grid[c][b] / (maxV || 1);
      ctx.fillStyle = heatColor(Math.pow(v, 0.6));
      ctx.fillRect(labelW + c * cw, topPad + b * ch,
        Math.ceil(cw), Math.ceil(ch));
    }
  }
  ctx.fillStyle = COL.muted; ctx.font = "10px monospace";
  ctx.textAlign = "right";
  for (let b = 0; b < hm.buckets; b++) {
    ctx.fillText(hm.bucket_labels[b], labelW - 6, topPad + b * ch + ch - 2);
  }
}

function drawEntropy(ent) {
  const cv = $("#entropyCanvas");
  const padL = 40, padR = 12, padT = 12, padB = 22;
  const { ctx, w, h } = fitCanvas(cv, 180);
  const plotW = w - padL - padR, plotH = h - padT - padB;
  const blocks = ent.blocks;
  // grid + y labels
  ctx.font = "10px monospace"; ctx.textAlign = "right";
  for (let v = 0; v <= 8; v += 2) {
    const y = padT + plotH - (v / 8) * plotH;
    ctx.strokeStyle = COL.grid; ctx.beginPath();
    ctx.moveTo(padL, y); ctx.lineTo(w - padR, y); ctx.stroke();
    ctx.fillStyle = COL.muted; ctx.fillText(v, padL - 6, y + 3);
  }
  // thresholds
  [[6.5, COL.warn, "compressed"], [7.3, COL.bad, "high"]].forEach(
    ([v, color, label]) => {
      const y = padT + plotH - (v / 8) * plotH;
      ctx.strokeStyle = color; ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(w - padR, y);
      ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = color; ctx.textAlign = "left";
      ctx.fillText(label + " " + v, padL + 4, y - 3);
    });
  if (!blocks.length) return;
  const maxOff = blocks[blocks.length - 1].offset;
  const X = (off) => padL + (off / Math.max(1, maxOff)) * plotW;
  const Y = (v) => padT + plotH - (v / 8) * plotH;
  ctx.beginPath();
  blocks.forEach((b, i) => {
    const x = X(b.offset), y = Y(b.entropy);
    i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  });
  ctx.strokeStyle = COL.accent; ctx.lineWidth = 1.6;
  ctx.stroke();
  ctx.lineTo(X(maxOff), Y(0)); ctx.lineTo(padL, Y(0));
  ctx.closePath();
  const grad = ctx.createLinearGradient(0, padT, 0, padT + plotH);
  grad.addColorStop(0, "rgba(79,195,247,.35)");
  grad.addColorStop(1, "rgba(79,195,247,.02)");
  ctx.fillStyle = grad; ctx.fill();
}

function drawHistogram(counts) {
  const cv = $("#histCanvas");
  const padL = 40, padR = 12, padT = 12, padB = 24;
  const { ctx, w, h } = fitCanvas(cv, 200);
  const plotW = w - padL - padR, plotH = h - padT - padB;
  const max = Math.max(1, ...counts);
  const bw = plotW / 256;
  for (let b = 0; b < 256; b++) {
    const bh = (counts[b] / max) * plotH;
    ctx.fillStyle = (b >= 32 && b < 127) ? COL.good
      : (b === 0 ? COL.accent2 : COL.warn);
    ctx.fillRect(padL + b * bw, padT + plotH - bh, Math.max(1, bw), bh);
  }
  ctx.fillStyle = COL.muted; ctx.font = "10px monospace";
  ctx.textAlign = "center";
  for (let b = 0; b < 256; b += 32) {
    const x = padL + b * bw;
    ctx.strokeStyle = COL.grid;
    ctx.beginPath(); ctx.moveTo(x, padT); ctx.lineTo(x, padT + plotH);
    ctx.stroke();
    ctx.fillText("0x" + b.toString(16).padStart(2, "0"), x, h - 6);
  }
}

/* ------------------------------ compare ------------------------------ */
async function doCompare() {
  const other = $("#otherPath").value.trim();
  if (!other) return;
  $("#compareStatus").textContent = "comparing…";
  try {
    const r = await api("/api/compare?other=" + encodeURIComponent(other));
    $("#compareResults").classList.remove("hidden");
    $("#compareKv").innerHTML = [
      kvRow("size A", `${r.size_a} (${fmtBytes(r.size_a)})`),
      kvRow("size B", `${r.size_b} (${fmtBytes(r.size_b)})`),
      kvRow("size delta", r.size_delta),
      kvRow("entropy A", r.entropy_a),
      kvRow("entropy B", r.entropy_b),
      kvRow("entropy delta", r.entropy_delta),
      kvRow("shared blocks", r.shared_blocks),
      kvRow("Jaccard similarity",
        `<b style="color:${r.jaccard_similarity > 0.5 ?
          COL.good : COL.warn}">${r.jaccard_similarity}</b>`),
      kvRow("strings added", r.strings_added.length),
      kvRow("strings removed", r.strings_removed.length),
    ].join("");
    $("#compareStatus").textContent =
      r.aligned ? "" : "sizes differ; aligned diff unavailable";
    drawSim(r.jaccard_similarity);
    drawDiff(r.aligned, r.size_a, r.size_b);
  } catch (e) {
    $("#compareStatus").textContent = "error: " + e.message;
  }
}

function drawSim(j) {
  const { ctx, w, h } = fitCanvas($("#simCanvas"), 200);
  const cx = w / 2, cy = h / 2, r = Math.min(w, h) / 2 - 24;
  ctx.lineWidth = 22; ctx.lineCap = "round";
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.strokeStyle = "#1d2638"; ctx.stroke();
  ctx.beginPath();
  ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * j);
  ctx.strokeStyle = j > 0.5 ? COL.good : COL.warn; ctx.stroke();
  ctx.fillStyle = "#e4e9f2"; ctx.textAlign = "center";
  ctx.font = "bold 30px monospace";
  ctx.fillText((j * 100).toFixed(1) + "%", cx, cy + 8);
  ctx.fillStyle = COL.muted; ctx.font = "12px monospace";
  ctx.fillText("block similarity", cx, cy + 30);
}

function drawDiff(aligned, sizeA, sizeB) {
  const cv = $("#diffCanvas");
  const { ctx, w, h } = fitCanvas(cv, 120);
  if (!aligned) {
    ctx.fillStyle = COL.muted; ctx.font = "13px monospace";
    ctx.textAlign = "center";
    ctx.fillText("files have different sizes — aligned map not shown",
      w / 2, h / 2);
    $("#diffLegend").innerHTML = "";
    return;
  }
  const map = aligned.map;
  const padT = 24, barH = 40;
  const maxD = 4096;
  const total = Math.ceil(sizeA / 4096);
  const bw = w / total;
  ctx.fillStyle = "#1d2638"; ctx.fillRect(0, padT, w, barH);
  map.forEach((blk) => {
    const x = (blk.offset / sizeA) * w;
    const v = blk.differing_bytes / blk.size;
    ctx.fillStyle = heatColor(v);
    ctx.fillRect(x, padT, Math.max(1, bw), barH);
  });
  ctx.fillStyle = COL.muted; ctx.font = "11px monospace";
  ctx.textAlign = "left";
  ctx.fillText(`${aligned.differing_bytes} differing bytes ` +
    `(${aligned.percent}%)`, 0, 16);
  $("#diffLegend").innerHTML =
    "<span><i class='swatch' style='background:#0d101a'></i>identical</span>" +
    "<span><i class='swatch' style='background:#1f6e96'></i>low</span>" +
    "<span><i class='swatch' style='background:#4fc3f7'></i>mid</span>" +
    "<span><i class='swatch' style='background:#dcf5ff'></i>high</span>";
}

$("#compareGo").onclick = doCompare;
$("#otherPath").addEventListener("keydown", (e) => {
  if (e.key === "Enter") doCompare();
});

/* --------------------------- boot + redraw --------------------------- */
addEventListener("tab:hex", () => {
  if (!$("#hexBody").children.length) renderHex(0, 256);
});
addEventListener("tab:strings", () => {
  if (!$("#stringTable tbody").children.length) renderStrings(false);
});
addEventListener("tab:structure", () => {
  if (!STRUCT) renderStructure();
});
addEventListener("tab:map", renderMap);
addEventListener("resize", () => {
  if (OVERVIEW) {
    drawGauge(OVERVIEW.entropy.entropy);
    drawComposition(OVERVIEW.histogram.composition);
  }
  if (STRUCT) renderStructure();
});

api("/api/health").then((h) => { $("#version").textContent = h.version; });
renderOverview();
