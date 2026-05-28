// Curio frontend: vanilla JS, no deps.
// Behavior:
//   1. On load: fetch /api/eval and render the banner.
//   2. On submit: clear columns, POST /api/retrieve, render chunks per strategy,
//      then open one EventSource per strategy and append streaming deltas.
//   3. Re-enable submit button once all three streams complete (success or fail).
//   4. Always render text via textContent (no innerHTML on untrusted strings).

const STRATEGIES = ["naive", "hybrid", "hybrid_rerank"];
const CHUNK_PREVIEW_CHARS = 300;

const $form = document.getElementById("ask-form");
const $input = document.getElementById("question");
const $submit = document.getElementById("submit-btn");
const $status = document.getElementById("status");
const $evalBanner = document.getElementById("eval-banner");
const $exampleBtn = document.getElementById("example-btn");
const $exampleText = document.getElementById("example-text");
const $shuffleBtn = document.getElementById("shuffle-btn");

// ---------- Eval banner ----------

// Eval data (recall@k + multipliers) cached from /api/eval, reused for the
// per-column benchmark scorecards.
let evalData = null;

// Maps a column's data-strategy id to the eval JSON's strategy key.
const EVAL_KEY = {
  naive: "Naive dense",
  hybrid: "Hybrid (RRF)",
  hybrid_rerank: "Hybrid + rerank",
};

async function loadEvalBanner() {
  try {
    const res = await fetch("/api/eval");
    if (!res.ok) throw new Error("eval fetch failed");
    const data = await res.json();
    evalData = data;
    renderEvalBanner(data);
  } catch (err) {
    setText($evalBanner, "Eval stats unavailable.");
  }
}

function renderEvalBanner(data) {
  // Clear, then populate. Be defensive about shape.
  while ($evalBanner.firstChild) $evalBanner.removeChild($evalBanner.firstChild);

  if (data && data.error) {
    setText($evalBanner, data.error);
    return;
  }

  const recall = data && data.recall_at_k;
  const mult = data && data.multipliers_vs_naive;

  if (!recall) {
    setText($evalBanner, "Eval stats unavailable.");
    return;
  }

  $evalBanner.appendChild(makeLabel("Recall@5"));

  const strategiesAtK5 = recall["5"] || recall[5] || {};
  for (const s of STRATEGIES) {
    if (strategiesAtK5[s] == null) continue;
    const stat = document.createElement("span");
    stat.className = "eval-stat";

    const name = document.createElement("span");
    name.textContent = prettyStrategy(s) + ":";

    const val = document.createElement("span");
    val.className = "eval-value";
    val.textContent = formatRecall(strategiesAtK5[s]);

    stat.appendChild(name);
    stat.appendChild(val);

    if (mult && mult["5"] && mult["5"][s] != null && s !== "naive") {
      const m = document.createElement("span");
      m.className = "eval-multiplier";
      m.textContent = "(" + formatMultiplier(mult["5"][s]) + "× vs naive)";
      stat.appendChild(m);
    }

    $evalBanner.appendChild(stat);
  }
}

function makeLabel(text) {
  const el = document.createElement("span");
  el.className = "eval-label";
  el.textContent = text;
  return el;
}

function prettyStrategy(s) {
  if (s === "naive") return "naive";
  if (s === "hybrid") return "hybrid";
  if (s === "hybrid_rerank") return "hybrid+rerank";
  return s;
}

function formatRecall(v) {
  if (typeof v === "number") return v.toFixed(2);
  if (v && typeof v === "object") {
    // Possible shape { mean: 0.4, ... }
    if (typeof v.mean === "number") return v.mean.toFixed(2);
    if (typeof v.recall === "number") return v.recall.toFixed(2);
  }
  return String(v);
}

function formatMultiplier(v) {
  if (typeof v === "number") return v.toFixed(2);
  return String(v);
}

// ---------- Example questions ----------

let examplePool = [];
let currentExample = null;

async function loadExamples() {
  try {
    const res = await fetch("/api/examples?n=20");
    if (!res.ok) throw new Error("examples fetch failed");
    const data = await res.json();
    examplePool = Array.isArray(data.examples) ? data.examples : [];
    pickRandomExample();
  } catch (_) {
    setText($exampleText, "Ask something about quantum mechanics or thermodynamics…");
    $exampleBtn.disabled = true;
    $shuffleBtn.disabled = true;
  }
}

function pickRandomExample() {
  if (!examplePool.length) return;
  let next;
  // Avoid immediately repeating the same example.
  do {
    next = examplePool[Math.floor(Math.random() * examplePool.length)];
  } while (examplePool.length > 1 && next === currentExample);
  currentExample = next;
  setText($exampleText, currentExample);
  $input.placeholder = currentExample;
}

function fillFromExample() {
  if (!currentExample) return;
  $input.value = currentExample;
  $input.focus();
  // Move cursor to end so Backspace edits work intuitively.
  const end = $input.value.length;
  $input.setSelectionRange(end, end);
}

$input.addEventListener("keydown", (e) => {
  // While a run is in flight the field is locked; don't mutate it.
  if (inFlight) return;
  if (e.key === "Tab" && !e.shiftKey && !$input.value && currentExample) {
    e.preventDefault();
    fillFromExample();
  }
});

$exampleBtn.addEventListener("click", () => fillFromExample());
$shuffleBtn.addEventListener("click", () => pickRandomExample());

// ---------- Question flow ----------

// Run state: a single run owns one retrieve fetch and three answer streams.
let inFlight = false;
let retrieveController = null; // AbortController for the /api/retrieve fetch
let activeStreams = []; // EventSource objects currently open

$form.addEventListener("submit", async (e) => {
  e.preventDefault();
  // Pressing Enter in the readonly field during a run must do nothing.
  if (inFlight) return;
  const q = $input.value.trim();
  if (q.length < 3) return;
  await runQuestion(q);
});

// One click handler: when running, the submit button acts as Stop.
$submit.addEventListener("click", (e) => {
  if (inFlight) {
    e.preventDefault();
    stopRun();
  }
});

function stopRun() {
  // Abort the retrieve fetch if it's still in flight.
  if (retrieveController) {
    try {
      retrieveController.abort();
    } catch (_) {}
  }
  // Close every open answer stream.
  closeAllStreams();
  setRunning(false);
  setStatus("Stopped.");
}

function closeAllStreams() {
  // Snapshot: each done() splices the stream out of activeStreams as it runs.
  for (const es of activeStreams.slice()) {
    if (typeof es._done === "function") {
      es._done(); // closes the socket and resolves its pending promise
    } else {
      try {
        es.close();
      } catch (_) {}
    }
  }
  activeStreams = [];
}

async function runQuestion(question) {
  clearColumns();
  setRunning(true);
  setStatus("Retrieving chunks…");

  retrieveController = new AbortController();

  let retrieveData;
  try {
    const res = await fetch("/api/retrieve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal: retrieveController.signal,
    });
    if (res.status === 429) {
      setStatus("Rate limited. Please slow down and try again in a minute.");
      setRunning(false);
      return;
    }
    if (!res.ok) throw new Error("retrieve failed: " + res.status);
    retrieveData = await res.json();
  } catch (err) {
    // A Stop during retrieval aborts the fetch -> AbortError. stopRun() has
    // already unlocked and set the status, so don't clobber it.
    if (err && err.name === "AbortError") return;
    setStatus("Retrieval failed. Please try again.");
    setRunning(false);
    return;
  } finally {
    retrieveController = null;
  }

  for (const s of STRATEGIES) {
    renderChunks(s, retrieveData[s] || []);
    renderMetric(s);
  }

  setStatus("Generating answers…");

  // Stream all three in parallel; unlock when every one closes.
  const closes = STRATEGIES.map((s) => streamAnswer(s, question));
  try {
    await Promise.allSettled(closes);
  } finally {
    // If a Stop already unlocked us, leave its "Stopped." status alone.
    if (inFlight) {
      setStatus("");
      setRunning(false);
      // After a question finishes, surface a fresh suggestion for the next ask.
      pickRandomExample();
    }
  }
}

function streamAnswer(strategy, question) {
  return new Promise((resolve) => {
    const $answer = panelEl(strategy, "answer");
    $answer.classList.remove("error");
    $answer.classList.add("streaming");
    setText($answer, "");

    const url =
      "/api/answer?strategy=" +
      encodeURIComponent(strategy) +
      "&question=" +
      encodeURIComponent(question);

    const es = new EventSource(url);
    activeStreams.push(es);
    let settled = false;
    const done = () => {
      if (settled) return;
      settled = true;
      $answer.classList.remove("streaming");
      try {
        es.close();
      } catch (_) {}
      const i = activeStreams.indexOf(es);
      if (i !== -1) activeStreams.splice(i, 1);
      resolve();
    };
    // Expose the resolver so a Stop can settle this promise (not just close
    // the socket) and avoid leaving Promise.allSettled pending forever.
    es._done = done;

    es.onmessage = (event) => {
      let payload;
      try {
        payload = JSON.parse(event.data);
      } catch (_) {
        return;
      }
      if (payload.error) {
        $answer.classList.add("error");
        setText($answer, "(generation failed)");
        done();
        return;
      }
      if (payload.done) {
        done();
        return;
      }
      if (typeof payload.delta === "string") {
        // textContent append: safe against any HTML in the model output.
        $answer.appendChild(document.createTextNode(payload.delta));
      }
    };

    es.onerror = () => {
      if (!settled) {
        $answer.classList.add("error");
        if (!$answer.textContent) setText($answer, "(generation failed)");
      }
      done();
    };
  });
}

// ---------- Rendering ----------

function clearColumns() {
  for (const s of STRATEGIES) {
    setText(panelEl(s, "chunks"), "");
    setText(panelEl(s, "answer"), "");
    panelEl(s, "answer").classList.remove("error", "streaming");
    clearMetric(s);
  }
}

function clearMetric(strategy) {
  const el = panelEl(strategy, "metric");
  if (!el) return;
  while (el.firstChild) el.removeChild(el.firstChild);
  el.hidden = true;
}

// Per-method benchmark scorecard. Shows the eval's recall-multiplier vs the
// dense baseline at k=1/3/5. This is the AGGREGATE eval result (15 fixtures),
// not a score for the live query — the note makes that explicit.
function renderMetric(strategy) {
  const el = panelEl(strategy, "metric");
  if (!el) return;
  while (el.firstChild) el.removeChild(el.firstChild);

  const mult = evalData && evalData.multipliers_vs_naive;
  if (!mult) {
    el.hidden = true;
    return;
  }

  const isBaseline = strategy === "naive";

  const title = document.createElement("div");
  title.className = "metric-title";
  title.textContent = isBaseline ? "Dense baseline" : "Recall vs baseline";
  el.appendChild(title);

  const row = document.createElement("div");
  row.className = "metric-row";
  for (const k of ["1", "3", "5"]) {
    const cell = document.createElement("span");
    cell.className = "metric-cell";

    const kEl = document.createElement("span");
    kEl.className = "metric-k";
    kEl.textContent = "@" + k;

    const vEl = document.createElement("span");
    vEl.className = "metric-val";
    if (isBaseline) {
      vEl.textContent = "1.0×";
    } else {
      const m = mult[k] && mult[k][EVAL_KEY[strategy]];
      vEl.textContent = typeof m === "number" ? m.toFixed(1) + "×" : "—";
      if (typeof m === "number" && m > 1.0) vEl.classList.add("up");
    }

    cell.appendChild(kEl);
    cell.appendChild(vEl);
    row.appendChild(cell);
  }
  el.appendChild(row);

  const note = document.createElement("div");
  note.className = "metric-note";
  note.textContent = "eval benchmark · 15 fixtures, not this query";
  el.appendChild(note);

  el.hidden = false;
}

function renderChunks(strategy, chunks) {
  const $chunks = panelEl(strategy, "chunks");
  setText($chunks, "");

  if (!chunks.length) {
    const ph = document.createElement("div");
    ph.className = "placeholder";
    ph.textContent = "No chunks retrieved.";
    $chunks.appendChild(ph);
    return;
  }

  for (const c of chunks) {
    $chunks.appendChild(buildChunkCard(c));
  }
}

function buildChunkCard(c) {
  const card = document.createElement("div");
  card.className = "chunk";

  const meta = document.createElement("div");
  meta.className = "chunk-meta";

  const badge = document.createElement("span");
  badge.className = "source-badge";
  badge.textContent = c.source || "unknown";
  meta.appendChild(badge);

  if (typeof c.score === "number") {
    const score = document.createElement("span");
    score.className = "score";
    score.textContent = c.score.toFixed(2);
    meta.appendChild(score);
  }

  card.appendChild(meta);

  const text = document.createElement("div");
  text.className = "chunk-text";
  text.textContent = truncate(c.text || "", CHUNK_PREVIEW_CHARS);
  card.appendChild(text);

  const footer = document.createElement("div");
  footer.className = "chunk-footer";
  footer.textContent = "(id: " + (c.id != null ? c.id : "?") + ")";
  card.appendChild(footer);

  return card;
}

function truncate(s, n) {
  if (s.length <= n) return s;
  return s.slice(0, n).trimEnd() + "…";
}

// ---------- Helpers ----------

function panelEl(strategy, role) {
  return document.querySelector(
    '.col[data-strategy="' + strategy + '"] [data-role="' + role + '"]'
  );
}

function setText(el, text) {
  el.textContent = text;
}

function setStatus(msg) {
  setText($status, msg || "");
}

function setRunning(running) {
  inFlight = running;
  // Lock the question with readonly (not disabled) so the text stays visible.
  $input.readOnly = running;
  // Lock the example-suggestion controls so they can't mutate the field.
  $exampleBtn.disabled = running;
  $shuffleBtn.disabled = running;
  // The submit button stays ENABLED while running so it can act as Stop.
  $submit.disabled = false;
  $submit.textContent = running ? "Stop" : "Compare";
  $submit.classList.toggle("stopping", running);
}

// ---------- Init ----------

loadEvalBanner();
loadExamples();
