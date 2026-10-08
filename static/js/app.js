"use strict";

/* ==========================================================================
   Helpers
   ========================================================================== */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const REDUCED_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}
const pct = (x) => `${(x * 100).toFixed(1)}%`;
const shortHash = (h) => (h ? `${h.slice(0, 10)}…${h.slice(-6)}` : "—");
const fmtDate = (iso) => (iso ? new Date(iso).toLocaleString() : "—");

const ICONS = {
  check: '<svg class="ic" viewBox="0 0 24 24"><path d="M5 12l5 5 9-10"/></svg>',
  alert: '<svg class="ic" viewBox="0 0 24 24"><path d="M12 3l9.5 17h-19z"/><path d="M12 10v4M12 17h.01"/></svg>',
  x: '<svg class="ic" viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  shield: '<svg class="ic" viewBox="0 0 24 24"><path d="M12 2l8 3v6c0 5-3.5 9-8 11-4.5-2-8-6-8-11V5z"/><path d="M8.5 12l2.5 2.5 4.5-5"/></svg>',
  chain: '<svg class="ic" viewBox="0 0 24 24"><path d="M10 13a5 5 0 0 0 7.07 0l3-3a5 5 0 0 0-7.07-7.07l-1.5 1.5"/><path d="M14 11a5 5 0 0 0-7.07 0l-3 3a5 5 0 0 0 7.07 7.07l1.5-1.5"/></svg>',
};

async function api(path, options = {}) {
  let res;
  try {
    res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new Error("Cannot reach the server. Is the Flask app running?");
  }
  const data = await res.json().catch(() => ({}));
  if (res.status === 404 && !data.error) {
    throw new Error("The backend API isn't running at this address. Start it with `python app.py` and open http://127.0.0.1:5000");
  }
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function setLoading(form, loading) {
  const btn = form.querySelector("button[type=submit]");
  btn.disabled = loading;
  btn.querySelector(".spinner").hidden = !loading;
}

function showError(el, message) {
  el.textContent = message || "";
  el.hidden = !message;
}

/** "Decoding" effect: random hex characters settle into the final text from left to right. */
function scramble(el, finalText, duration = 900) {
  if (REDUCED_MOTION) { el.textContent = finalText; return; }
  const chars = "0123456789abcdef";
  const start = performance.now();
  (function tick(now) {
    const progress = Math.min((now - start) / duration, 1);
    const settled = Math.floor(progress * finalText.length);
    let out = finalText.slice(0, settled);
    for (let i = settled; i < finalText.length; i++) {
      out += /[0-9a-fx]/i.test(finalText[i]) ? chars[(Math.random() * 16) | 0] : finalText[i];
    }
    el.textContent = out;
    if (progress < 1) requestAnimationFrame(tick);
  })(start);
}
function runScrambles(root) {
  $$("[data-scramble]", root).forEach((el, i) => setTimeout(() => scramble(el, el.dataset.scramble), i * 150));
}

/** Animated number count-up. */
function countTo(el, value, { decimals = 0, suffix = "", duration = 1600 } = {}) {
  if (value == null || Number.isNaN(value)) { el.textContent = "—"; return; }
  if (REDUCED_MOTION) { el.textContent = value.toFixed(decimals) + suffix; return; }
  const start = performance.now();
  (function tick(now) {
    const t = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = (value * eased).toFixed(decimals) + suffix;
    if (t < 1) requestAnimationFrame(tick);
  })(start);
}

/* run callbacks once the intro has finished */
const readyQueue = [];
function whenReady(fn) {
  if (document.body.classList.contains("site-ready")) fn();
  else readyQueue.push(fn);
}

/* ==========================================================================
   Cinematic intro
   ========================================================================== */
(function intro() {
  const introEl = $("#intro");
  const finish = () => {
    document.body.classList.remove("intro-active");
    document.body.classList.add("site-ready");
    readyQueue.splice(0).forEach((fn) => fn());
  };
  if (REDUCED_MOTION) {
    introEl.remove();
    finish();
    return;
  }

  // floating "misinformation" words
  const words = ["BREAKING", "VIRAL", "SHOCKING", "UNVERIFIED", "SOURCE?", "EXCLUSIVE", "RUMOR", "HOAX",
    "MISLEADING", "SHARE NOW", "100% TRUE", "LEAKED", "CLICKBAIT", "FACT?", "MUST READ", "ANONYMOUS"];
  const wordsEl = $("#intro-words");
  words.forEach((w, i) => {
    const s = document.createElement("span");
    s.textContent = w;
    if (i % 3 === 0) s.className = "hot";
    else if (i % 4 === 1) s.className = "warm";
    s.style.left = `${3 + Math.random() * Math.max(10, 80 - w.length * 3.2)}%`;
    s.style.top = `${6 + Math.random() * 84}%`;
    s.style.fontSize = `${0.8 + Math.random() * 1.5}rem`;
    s.style.setProperty("--delay", `${0.3 + Math.random() * 1.4}s`);
    wordsEl.appendChild(s);
  });

  // title letters
  const title = $("#intro-title");
  title.innerHTML = [...title.textContent].map((ch, i) =>
    ch === " " ? " " : `<span class="ch" style="--i:${i}">${escapeHtml(ch)}</span>`).join("");

  // boot log
  const log = $("#intro-log");
  const messages = [
    [3700, "Loading NLP pipeline (NLTK)…"],
    [4200, "Initializing AI models…"],
    [4700, "Connecting to Ethereum ledger…"],
    [5200, "System ready ✓"],
  ];
  const timers = messages.map(([t, msg]) => setTimeout(() => { log.textContent = msg; }, t));
  const titleText = title.textContent;
  timers.push(setTimeout(() => {
    title.textContent = titleText;
    title.classList.add("gold-shimmer", "lit");
  }, 4500));

  let exited = false;
  function exit() {
    if (exited) return;
    exited = true;
    timers.forEach(clearTimeout);
    introEl.classList.add("exit");
    setTimeout(finish, 350);
    setTimeout(() => introEl.remove(), 1400);
  }
  timers.push(setTimeout(exit, 5800));
  $("#intro-skip").addEventListener("click", exit);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") exit(); });
})();

/* ==========================================================================
   Background: blockchain / neural network particles
   ========================================================================== */
(function network() {
  const canvas = $("#bg-network");
  const ctx = canvas.getContext("2d");
  let w = 0, h = 0, nodes = [];
  const mouse = { x: -9999, y: -9999 };
  const LINK = 150;

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = window.innerWidth;
    h = window.innerHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = Math.round(Math.min(48, (w * h) / 30000));
    nodes = Array.from({ length: count }, () => ({
      x: Math.random() * w, y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.18, vy: (Math.random() - 0.5) * 0.18,
      r: Math.random() * 1.3 + 0.5,
      c: Math.random() < 0.75 ? "216,180,106" : "184,196,220",
    }));
  }

  function draw() {
    ctx.clearRect(0, 0, w, h);
    for (const n of nodes) {
      n.x += n.vx; n.y += n.vy;
      if (n.x < 0 || n.x > w) n.vx *= -1;
      if (n.y < 0 || n.y > h) n.vy *= -1;
      const dx = mouse.x - n.x, dy = mouse.y - n.y, d = Math.hypot(dx, dy);
      if (d < 180 && d > 1) { n.x += dx / d * 0.12; n.y += dy / d * 0.12; }
    }
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        if (d < LINK) {
          ctx.strokeStyle = `rgba(${a.c},${(1 - d / LINK) * 0.16})`;
          ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
        }
      }
      const n = nodes[i];
      const md = Math.hypot(mouse.x - n.x, mouse.y - n.y);
      if (md < 180) {
        ctx.strokeStyle = `rgba(216,180,106,${(1 - md / 180) * 0.25})`;
        ctx.beginPath(); ctx.moveTo(n.x, n.y); ctx.lineTo(mouse.x, mouse.y); ctx.stroke();
      }
      ctx.fillStyle = `rgba(${n.c},0.7)`;
      ctx.beginPath(); ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2); ctx.fill();
    }
  }

  function loop() {
    if (!document.hidden) draw();
    requestAnimationFrame(loop);
  }

  resize();
  window.addEventListener("resize", resize);
  window.addEventListener("mousemove", (e) => { mouse.x = e.clientX; mouse.y = e.clientY; });
  window.addEventListener("mouseout", () => { mouse.x = mouse.y = -9999; });
  if (REDUCED_MOTION) draw(); else loop();
})();

/* ==========================================================================
   Luxury micro-interactions: cursor glow, scroll progress, magnetic buttons
   ========================================================================== */
const glow = $("#cursor-glow");
window.addEventListener("pointermove", (e) => {
  if (e.pointerType === "mouse") glow.style.transform = `translate(${e.clientX}px, ${e.clientY}px)`;
}, { passive: true });

const progressBar = $("#progress");
function updateProgress() {
  const max = document.documentElement.scrollHeight - window.innerHeight;
  progressBar.style.transform = `scaleX(${max > 0 ? window.scrollY / max : 0})`;
}
window.addEventListener("scroll", updateProgress, { passive: true });

if (!REDUCED_MOTION) {
  $$(".magnetic").forEach((btn) => {
    btn.addEventListener("pointermove", (e) => {
      const r = btn.getBoundingClientRect();
      btn.style.transform = `translate(${(e.clientX - r.left - r.width / 2) * 0.25}px, ${(e.clientY - r.top - r.height / 2) * 0.35}px)`;
    });
    btn.addEventListener("pointerleave", () => { btn.style.transform = ""; });
  });
}

/* ==========================================================================
   Navigation, scroll reveal, spotlight, tilt
   ========================================================================== */
const nav = $("#nav");
window.addEventListener("scroll", () => nav.classList.toggle("scrolled", window.scrollY > 20), { passive: true });

const menuBtn = $("#menu-btn"), navLinks = $("#nav-links");
menuBtn.addEventListener("click", () => {
  const open = navLinks.classList.toggle("open");
  menuBtn.setAttribute("aria-expanded", String(open));
});
$$("a", navLinks).forEach((a) => a.addEventListener("click", () => {
  navLinks.classList.remove("open");
  menuBtn.setAttribute("aria-expanded", "false");
}));

// highlight the nav link of the section in view
const sectionObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (!entry.isIntersecting) return;
    $$("a", navLinks).forEach((a) => a.classList.toggle("active", a.getAttribute("href") === `#${entry.target.id}`));
  });
}, { rootMargin: "-45% 0px -50% 0px" });
$$("main section[id]").forEach((s) => sectionObserver.observe(s));

// reveal-on-scroll
const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add("in");
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.12 });
whenReady(() => $$(".reveal").forEach((el) => revealObserver.observe(el)));

// mouse-follow spotlight on cards
document.addEventListener("pointermove", (e) => {
  const card = e.target.closest(".spot");
  if (!card) return;
  const rect = card.getBoundingClientRect();
  card.style.setProperty("--mx", `${e.clientX - rect.left}px`);
  card.style.setProperty("--my", `${e.clientY - rect.top}px`);
});

// 3-D tilt of the hero scanner card
const tiltEl = $(".tilt");
if (tiltEl && !REDUCED_MOTION) {
  const hero = $(".hero");
  hero.addEventListener("pointermove", (e) => {
    const r = hero.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - 0.5;
    const y = (e.clientY - r.top) / r.height - 0.5;
    tiltEl.style.transform = `rotateY(${-12 + x * 14}deg) rotateX(${7 - y * 10}deg)`;
  });
  hero.addEventListener("pointerleave", () => { tiltEl.style.transform = ""; });
}

/* ==========================================================================
   Status, stats & models
   ========================================================================== */
async function loadStatus() {
  try {
    const s = await api("/api/status");
    const pm = $("#pill-model"), pc = $("#pill-chain");
    const nModels = s.models.available.length;
    pm.innerHTML = `<i class="live"></i>${nModels ? `${nModels} AI models` : "No model"}`;
    pm.className = `pill ${nModels ? "ok" : "bad"}`;
    const chain = s.blockchain;
    pc.innerHTML = `<i class="live"></i>${chain.connected ? `Ethereum · block ${chain.block_number}` : "Blockchain offline"}`;
    pc.className = `pill ${chain.connected ? "ok" : "bad"}`;
    pc.title = chain.error || chain.contract_address || "";
    $("#hero-block").textContent = chain.connected ? `#${chain.block_number}` : "#—";
    whenReady(() => {
      countTo($("#stat-models"), nModels);
      countTo($("#stat-records"), chain.connected ? chain.record_count : null);
    });
    return s;
  } catch {
    return null;
  }
}

async function loadSourcesStat() {
  try {
    const { sources } = await api("/api/sources");
    whenReady(() => countTo($("#stat-sources"), sources.length));
  } catch {
    whenReady(() => countTo($("#stat-sources"), null));
  }
}

let modelsData = null;
async function loadModels() {
  try {
    modelsData = await api("/api/models");
  } catch (err) {
    $("#model-select").innerHTML = "<option value=''>Unavailable</option>";
    $("#model-grid").innerHTML = `<p class="muted">${escapeHtml(err.message)}</p>`;
    return;
  }
  const { models, default_model: def, dataset } = modelsData;

  // model selector
  $("#model-select").innerHTML = models.length
    ? models.map((m) => `<option value="${m.name}" ${m.name === def ? "selected" : ""}>${escapeHtml(m.display_name)}${m.name === def ? " — recommended" : ""}</option>`).join("")
    : "<option value=''>No trained model</option>";

  // hero accuracy stat: best FakeNewsNet test accuracy
  const fnn = models.map((m) => m.test_by_dataset?.FakeNewsNet?.accuracy).filter((x) => x != null);
  whenReady(() => countTo($("#stat-acc"), fnn.length ? Math.max(...fnn) * 100 : null, { decimals: 1, suffix: "%" }));

  // evaluation section
  if (dataset) {
    $("#dataset-info").textContent = `${dataset.sources.join(" + ")} — ${dataset.train.toLocaleString()} training, `
      + `${dataset.valid.toLocaleString()} validation and ${dataset.test.toLocaleString()} test samples.`;
  }
  const metric = (label, v) => `<div class="metric"><span>${label}</span><div class="bar"><div class="bar-fill" data-w="${(v * 100).toFixed(1)}"></div></div><span>${pct(v)}</span></div>`;
  $("#model-grid").innerHTML = models.map((m, i) => {
    const t = m.test, by = m.test_by_dataset || {};
    return `<article class="mcard reveal ${m.name === def ? "best" : ""}" style="--d:${i}">
      ${m.name === def ? '<span class="tag">Default</span>' : ""}
      <h3>${escapeHtml(m.display_name)}</h3>
      <p class="sub">FakeNewsNet ${by.FakeNewsNet ? pct(by.FakeNewsNet.accuracy) : "—"} · LIAR ${by.LIAR ? pct(by.LIAR.accuracy) : "—"}</p>
      ${metric("Accuracy", t.accuracy)}${metric("Precision", t.precision)}${metric("Recall", t.recall)}${metric("F1-score", t.f1)}
    </article>`;
  }).join("") || "<p class='muted'>No trained models yet. Run <code>python -m ml.train</code>.</p>";

  const barObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      $$(".bar-fill[data-w]", entry.target).forEach((b) => { b.style.width = `${b.dataset.w}%`; });
      barObserver.unobserve(entry.target);
    });
  }, { threshold: 0.3 });
  $$(".mcard").forEach((c) => { barObserver.observe(c); whenReady(() => revealObserver.observe(c)); });
}

/* ==========================================================================
   Verification rendering (shared by Analyze and Trace)
   ========================================================================== */
const STATUS = {
  "Verified": { cls: "verified", icon: ICONS.shield },
  "Unverified": { cls: "unverified", icon: ICONS.alert },
  "Source Mismatch": { cls: "mismatch", icon: ICONS.x },
  "No Source": { cls: "nosource", icon: ICONS.alert },
};

function recordDetails(r) {
  if (!r) return "";
  return `<dl class="kv">
    <dt>Content hash</dt><dd class="mono" data-scramble="${escapeHtml(r.content_hash)}">${escapeHtml(r.content_hash)}</dd>
    <dt>Original source</dt><dd>${escapeHtml(r.source || "—")}</dd>
    ${r.source_url ? `<dt>Source URL</dt><dd>${escapeHtml(r.source_url)}</dd>` : ""}
    <dt>AI result</dt><dd>${escapeHtml(r.label)} (${pct(r.confidence)}, ${escapeHtml(r.model)})</dd>
    <dt>Registered</dt><dd>${fmtDate(r.registered_at)}</dd>
    <dt>Transaction</dt><dd class="mono" data-scramble="${escapeHtml(r.tx_hash || "—")}">${escapeHtml(r.tx_hash || "—")}</dd>
    <dt>Submitted by</dt><dd class="mono">${escapeHtml(r.submitter)}</dd>
    <dt>Integrity</dt><dd>${r.integrity_verified
      ? `<span class="badge badge-verified">${ICONS.check} Intact — matches on-chain event</span>`
      : `<span class="badge badge-bad">${ICONS.x} Could not be verified</span>`}</dd>
  </dl>`;
}

function miniChain(r, isNew) {
  if (!r || r.block_number == null) return "";
  return `<div class="mini-chain">
      <div class="mini-block ghost"><span class="muted">Block</span><b>#${r.block_number - 1}</b></div>
      <div class="mini-link"></div>
      <div class="mini-block current"><span class="muted">${isNew ? "New block" : "Recorded in block"}</span><b>#${r.block_number}</b></div>
    </div>`;
}

function verificationHtml(v) {
  if (v.available === false) {
    return `<div class="status-box"><div class="status-head"><span class="badge badge-bad">${ICONS.x} Blockchain unavailable</span></div>
      <p class="muted small">${escapeHtml(v.error)}</p></div>`;
  }
  const s = STATUS[v.status] || STATUS["No Source"];
  const note = v.newly_recorded === true
    ? "A new record was written to the Ethereum ledger."
    : v.previously_recorded ? "This content was already on the ledger — showing the original record." : "";
  return `<div class="status-box">
      <div class="status-head">
        <span class="badge badge-${s.cls}">${s.icon} ${escapeHtml(v.status)}</span>
        ${note ? `<span class="badge badge-chain">${ICONS.chain} ${v.newly_recorded ? "Recorded" : "On ledger"}</span>` : ""}
      </div>
      <p>${escapeHtml(v.detail)}</p>
      ${note ? `<p class="muted small">${note}</p>` : ""}
      ${miniChain(v.record, v.newly_recorded === true)}
      ${v.record ? recordDetails(v.record)
        : `<dl class="kv"><dt>Content hash</dt><dd class="mono" data-scramble="${escapeHtml(v.content_hash)}">${escapeHtml(v.content_hash)}</dd></dl>`}
    </div>`;
}

/* ==========================================================================
   Analyze
   ========================================================================== */
const newsText = $("#news-text");
newsText.addEventListener("input", () => { $("#char-count").textContent = newsText.value.length; });

function showState(name) {
  ["idle", "scan", "result"].forEach((s) => { $(`#state-${s}`).hidden = s !== name; });
}

$("#clear-btn").addEventListener("click", () => {
  $("#analyze-form").reset();
  $("#char-count").textContent = "0";
  showError($("#analyze-error"), "");
  showState("idle");
});

/** Animate the pipeline steps while the request runs; resolves once all steps are shown. */
function runScanSteps(modelName) {
  const steps = $$("#scan-steps li");
  $("#scan-model-step").textContent = `Running ${modelName}`;
  steps.forEach((li) => li.classList.remove("active", "done"));
  const STEP_MS = REDUCED_MOTION ? 0 : 420;
  steps.forEach((li, i) => setTimeout(() => {
    if (i > 0) steps[i - 1].classList.replace("active", "done");
    li.classList.add("active");
  }, i * STEP_MS));
  return sleep(steps.length * STEP_MS);
}

$("#analyze-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget, errEl = $("#analyze-error");
  const text = newsText.value.trim();
  if (text.split(/\s+/).filter(Boolean).length < 3) {
    showError(errEl, "Please enter a news headline or article of at least 3 words.");
    return;
  }
  showError(errEl, "");
  setLoading(form, true);

  const select = $("#model-select");
  $("#scan-excerpt").textContent = text.length > 420 ? `${text.slice(0, 420)}…` : text;
  showState("scan");
  if (window.innerWidth < 960) $("#result").scrollIntoView({ behavior: "smooth", block: "start" });
  const stepsDone = runScanSteps(select.selectedOptions[0]?.text.replace(" — recommended", "") || "AI model");

  try {
    const [data] = await Promise.all([
      api("/api/analyze", {
        method: "POST",
        body: {
          text,
          source: $("#news-source").value.trim(),
          source_url: $("#news-url").value.trim(),
          model: select.value || null,
          record: $("#record-chain").checked,
        },
      }),
      stepsDone,
    ]);
    $$("#scan-steps li").forEach((li) => { li.classList.remove("active"); li.classList.add("done"); });
    await sleep(REDUCED_MOTION ? 0 : 350);
    renderResult(data);
    loadStatus();
    if (ledgerLoaded) loadLedger();
  } catch (err) {
    showState("idle");
    showError(errEl, err.message);
  } finally {
    setLoading(form, false);
  }
});

function renderResult({ prediction: p, blockchain: v }) {
  const cls = p.label.toLowerCase();
  showState("result");

  const stamp = $("#verdict-label");
  stamp.textContent = p.label.toUpperCase();
  stamp.className = `stamp ${cls}`;
  void stamp.offsetWidth;            // restart the slam animation
  stamp.classList.add("slam");

  const consoleEl = $("#result");
  consoleEl.classList.remove("flash-fake", "flash-real");
  void consoleEl.offsetWidth;
  consoleEl.classList.add(`flash-${cls}`);

  const gauge = $("#gauge"), fg = $("#gauge-fg");
  gauge.className = `gauge ${cls}`;
  fg.style.transition = "none";
  fg.style.strokeDashoffset = "326.73";
  void fg.offsetWidth;
  fg.style.transition = "";
  fg.style.strokeDashoffset = String(326.73 * (1 - p.confidence));
  countTo($("#gauge-num"), p.confidence * 100, { decimals: 1, duration: 1400 });

  ["real", "fake"].forEach((k) => { $(`#bar-${k}`).style.width = "0"; });
  requestAnimationFrame(() => {
    $("#bar-real").style.width = pct(p.probabilities.Real);
    $("#bar-fake").style.width = pct(p.probabilities.Fake);
  });
  $("#pct-real").textContent = pct(p.probabilities.Real);
  $("#pct-fake").textContent = pct(p.probabilities.Fake);
  $("#model-used").textContent = `Classified by ${p.model_display_name}`;

  const chainEl = $("#chain-result");
  chainEl.innerHTML = verificationHtml(v);
  runScrambles(chainEl);
}

/* ==========================================================================
   Trace
   ========================================================================== */
$("#trace-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget, errEl = $("#trace-error");
  showError(errEl, "");
  setLoading(form, true);
  try {
    const v = await api("/api/verify", {
      method: "POST",
      body: { text: $("#trace-text").value.trim(), source: $("#trace-source").value.trim() },
    });
    const out = $("#trace-result");
    out.innerHTML = `<h3 class="sub-h">Trace result</h3><div class="state">${verificationHtml(v)}</div>`;
    runScrambles(out);
  } catch (err) {
    showError(errEl, err.message);
  } finally {
    setLoading(form, false);
  }
});

$("#hash-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.currentTarget, errEl = $("#hash-error");
  const hash = $("#hash-input").value.trim();
  if (!/^(0x)?[0-9a-fA-F]{64}$/.test(hash)) {
    showError(errEl, "Enter a valid 32-byte hex hash (0x followed by 64 hex characters).");
    return;
  }
  showError(errEl, "");
  setLoading(form, true);
  try {
    const r = await api(`/api/records/${encodeURIComponent(hash)}`);
    const out = $("#trace-result");
    out.innerHTML = `<h3 class="sub-h">Ledger record</h3><div class="status-box state">${miniChain(r, false)}${recordDetails(r)}</div>`;
    runScrambles(out);
  } catch (err) {
    showError(errEl, err.message);
  } finally {
    setLoading(form, false);
  }
});

/* ==========================================================================
   Ledger
   ========================================================================== */
let ledgerLoaded = false;
async function loadLedger() {
  ledgerLoaded = true;
  const tbody = $("#ledger-table tbody"), errEl = $("#ledger-error");
  showError(errEl, "");
  try {
    const [records, sources, status] = await Promise.all([
      api("/api/records?limit=50"), api("/api/sources"), api("/api/status"),
    ]);
    const s = status.blockchain;
    $("#chain-meta").textContent = s.connected
      ? `Contract ${s.contract_address} · chain ID ${s.chain_id} · block ${s.block_number}` : "";
    $("#ledger-total").textContent = `(${records.total} total)`;

    // chain of blocks: oldest → newest, newest highlighted
    const latest = records.records.slice(0, 8).reverse();
    const strip = $("#chain-strip");
    strip.innerHTML = latest.map((r, i) => `${i ? '<div class="clink"></div>' : ""}
      <div class="cblock ${i === latest.length - 1 ? "latest" : ""}" style="--i:${i}" title="${escapeHtml(r.content_hash)}">
        <div class="bn">BLOCK #${r.block_number ?? "—"}</div>
        <div class="bh">${shortHash(r.content_hash)}</div>
        <div class="bs">${escapeHtml(r.source || "Unknown source")}</div>
        <span class="badge badge-${r.label.toLowerCase()}">${escapeHtml(r.label)} · ${pct(r.confidence)}</span>
      </div>`).join("");
    strip.scrollLeft = strip.scrollWidth;

    tbody.innerHTML = records.records.map((r) => `<tr>
        <td>${fmtDate(r.registered_at)}</td>
        <td class="mono" title="${escapeHtml(r.content_hash)}">${shortHash(r.content_hash)}</td>
        <td>${escapeHtml(r.source || "—")}</td>
        <td><span class="badge badge-${r.label.toLowerCase()}">${escapeHtml(r.label)}</span> <span class="muted">${pct(r.confidence)}</span></td>
        <td class="mono">#${r.block_number ?? "—"}</td>
        <td>${r.integrity_verified ? `<span class="ok-ic">${ICONS.check}</span> intact` : `<span class="bad-ic">${ICONS.x}</span>`}</td></tr>`).join("")
      || "<tr><td colspan='6' class='muted'>No records yet. Analyze some news to create the first ledger entry.</td></tr>";

    $("#sources-list").innerHTML = sources.sources.map((src) => `<span class="src-chip">${ICONS.shield}${escapeHtml(src)}</span>`).join("")
      || "<span class='muted'>No verified sources registered.</span>";
  } catch (err) {
    tbody.innerHTML = "";
    $("#chain-strip").innerHTML = "";
    showError(errEl, err.message);
  }
}
$("#refresh-ledger").addEventListener("click", loadLedger);

// load the ledger the first time its section scrolls into view
const ledgerObserver = new IntersectionObserver((entries) => {
  if (entries.some((e) => e.isIntersecting)) {
    loadLedger();
    ledgerObserver.disconnect();
  }
}, { rootMargin: "200px" });
ledgerObserver.observe($("#ledger"));

/* ==========================================================================
   Init
   ========================================================================== */
loadStatus();
loadSourcesStat();
loadModels();
