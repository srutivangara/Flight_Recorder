const $ = s => document.querySelector(s);
const esc = x => String(x ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

async function loadSessions(q = "") {
  const data = await fetch("/api/sessions?q=" + encodeURIComponent(q)).then(r => r.json());
  $("#sessionList").innerHTML = data.map((x, i) => `
    <div class="session ${i === 0 ? 'selected' : ''}" data-sid="${esc(x.session_id)}">
      <div class="sid">${esc(x.session_id)}</div>
      <div class="goal">${esc(x.goal)}</div>
      <span class="pill ${x.integrity ? 'good' : 'bad'}">${x.integrity ? 'CHAIN OK' : 'CHAIN TAMPERED'}</span>
      <span class="pill">${esc(x.prediction)}</span>
    </div>`).join("");
  
  document.querySelectorAll(".session").forEach(el => {
    el.onclick = () => selectSession(el.dataset.sid);
  });
  
  if (data[0]) selectSession(data[0].session_id);
}

async function selectSession(sid) {
  document.querySelectorAll(".session").forEach(x => {
    x.classList.toggle("selected", x.dataset.sid === sid);
  });

  const d = await fetch("/api/session/" + encodeURIComponent(sid)).then(r => r.json());
  
  // Force hide empty state and show detail
  const empty = $("#empty");
  const detail = $("#detail");
  if (empty) {
    empty.style.display = "none";
    empty.hidden = true;
  }
  if (detail) {
    detail.style.display = "block";
    detail.hidden = false;
  }

  const a = d.analysis;
  let flags = "";
  
  if (!a.integrity.ok) {
    flags += `<div class="alert bad"><b>⚠ Hash chain broken</b><br>First bad span: ${esc(a.integrity.first_bad_span)}</div>`;
  }
  if (a.suspicious_retrievals && a.suspicious_retrievals.length) {
    flags += `<div class="alert bad"><b>⚠ Suspicious retrieval</b><br>${a.suspicious_retrievals.join(", ")}</div>`;
  }
  if (a.failed_results && a.failed_results.length) {
    flags += `<div class="alert"><b>⚠ Tool failure</b></div>`;
  }
  if (a.unconfirmed_side_effects && a.unconfirmed_side_effects.length) {
    flags += `<div class="alert"><b>Human gate</b><br>${a.unconfirmed_side_effects.length} side-effecting action(s) not confirmed</div>`;
  }

  detail.innerHTML = `
    <div class="detail">
      <div class="eyebrow">${esc(a.session_id)}</div>
      <h2>${esc(a.prediction_label)}</h2>
      <p><b>User goal:</b> ${esc(a.user_goal)}</p>
      ${flags}
      <div class="score">
        <div class="score-card"><span class="muted">Confidence</span><b>${Math.round(a.confidence * 100)}%</b></div>
        <div class="score-card"><span class="muted">First cause</span><b>${esc(a.first_cause_span || "None")}</b></div>
        <div class="score-card"><span class="muted">Integrity</span><b>${a.integrity.ok ? "PASS" : "FAIL"}</b></div>
        <div class="score-card"><span class="muted">Agents</span><b>${(a.agents || []).length}</b></div>
      </div>
      <h3>Why the model chose this</h3>
      <div class="result-card">
        ${Object.entries(a.probabilities || {}).map(([k, v]) => `
          <div style="margin:9px 0">
            <div style="display:flex;justify-content:space-between">
              <span>${esc(k)}</span><b>${Math.round(v * 100)}%</b>
            </div>
            <div style="height:5px;background:#222c37;border-radius:4px;margin-top:4px">
              <div style="width:${Math.round(v * 100)}%;height:5px;background:var(--accent);border-radius:4px"></div>
            </div>
          </div>
        `).join("")}
      </div>
      <h3 style="margin-top:22px">Trace timeline</h3>
      <div class="timeline">
        ${(d.spans || []).map(sp => `
          <div class="span ${sp.is_predicted_cause ? "cause" : ""}">
            <div class="kind">${esc(sp.kind)}${sp.is_predicted_cause ? " • PREDICTED CAUSE" : ""}</div>
            ${sp.tool ? `<div class="tool">${esc(sp.tool)}</div>` : ""}
            ${sp.content ? `<div>${esc(sp.content)}</div>` : ""}
            ${sp.mandate ? `<div class="muted">Mandate: ${esc(sp.mandate)}</div>` : ""}
            ${sp.status ? `<div class="muted">Result: ${esc(sp.status)}</div>` : ""}
            ${sp.human_confirmed !== undefined ? `<div class="muted">Human confirmed: ${esc(sp.human_confirmed)}</div>` : ""}
          </div>
        `).join("")}
      </div>
    </div>
  `;
}

$("#search").oninput = e => loadSessions(e.target.value);

document.querySelectorAll(".tab").forEach(btn => {
  btn.onclick = () => {
    document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
    document.querySelectorAll(".tabpane").forEach(x => x.classList.remove("active"));
    btn.classList.add("active");
    $("#" + btn.dataset.tab).classList.add("active");
  };
});

$("#verifyBtn").onclick = async () => {
  const r = await fetch("/api/verify").then(x => x.json());
  $("#verifyResult").innerHTML = `
    <div class="result-card">
      <h3>${r.bad_count} broken chain(s)</h3>
      ${r.bad.map(x => `<p><b>${esc(x.session_id)}</b> — ${esc(x.first_bad_span)}</p>`).join("") || "<p class='muted'>All chains verified.</p>"}
    </div>
  `;
};

$("#policyBtn").onclick = async () => {
  const r = await fetch("/api/policy").then(x => x.json());
  $("#policyResult").innerHTML = `
    <div class="result-card">
      <div class="score">
        <div class="score-card"><span class="muted">Confirmations</span><b>${r.confirmation_count}</b></div>
        <div class="score-card"><span class="muted">Rate</span><b>${Math.round(r.confirmation_rate * 100)}%</b></div>
        <div class="score-card"><span class="muted">Friction</span><b>₹${r.friction_inr.toLocaleString()}</b></div>
      </div>
    </div>
  `;
};

async function loadClasses() {
  const r = await fetch("/api/train").then(x => x.json());
  $("#classGrid").innerHTML = Object.entries(r.classes)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `<div class="class"><b>${v}</b><span>${esc(r.class_labels[k])}</span></div>`)
    .join("");
}

loadSessions();
loadClasses();