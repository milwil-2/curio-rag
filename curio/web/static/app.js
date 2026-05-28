// Curio frontend — vanilla JS, no deps.
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

// ---------- Eval banner ----------

async function loadEvalBanner() {
  try {
    const res = await fetch("/api/eval");
    if (!res.ok) throw new Error("eval fetch failed");
    const data = await res.json();
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

// ---------- Question flow ----------

$form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = $input.value.trim();
  if (q.length < 3) return;
  await runQuestion(q);
});

async function runQuestion(question) {
  clearColumns();
  setSubmitDisabled(true);
  setStatus("Retrieving chunks…");

  let retrieveData;
  try {
    const res = await fetch("/api/retrieve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    if (res.status === 429) {
      setStatus("Rate limited — please slow down and try again in a minute.");
      setSubmitDisabled(false);
      return;
    }
    if (!res.ok) throw new Error("retrieve failed: " + res.status);
    retrieveData = await res.json();
  } catch (err) {
    setStatus("Retrieval failed. Please try again.");
    setSubmitDisabled(false);
    return;
  }

  for (const s of STRATEGIES) {
    renderChunks(s, retrieveData[s] || []);
  }

  setStatus("Generating answers…");

  // Stream all three in parallel; re-enable button when every one closes.
  const closes = STRATEGIES.map((s) => streamAnswer(s, question));
  try {
    await Promise.allSettled(closes);
  } finally {
    setStatus("");
    setSubmitDisabled(false);
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
    let settled = false;
    const done = () => {
      if (settled) return;
      settled = true;
      $answer.classList.remove("streaming");
      try {
        es.close();
      } catch (_) {}
      resolve();
    };

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
        // textContent append — safe against any HTML in the model output.
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
  }
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

function setSubmitDisabled(disabled) {
  $submit.disabled = disabled;
  $submit.textContent = disabled ? "Working…" : "Compare";
}

// ---------- Init ----------

loadEvalBanner();
