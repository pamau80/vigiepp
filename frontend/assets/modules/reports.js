import { $, $$ } from "./dom.js";

/** Centro de informes y notificaciones. */
export function createReportsController({ api, els, getProfiles }) {
  let lastStats = null;
  let notifConfig = {};
  let currentRep = null;

function fillRepProfiles() {
  if (!els.repProfile || !getProfiles().length) return;
  const cur = els.repProfile.value;
  els.repProfile.innerHTML =
    `<option value="">Todos</option>` +
    getProfiles().map((p) => `<option value="${p.id}">${p.name}</option>`).join("");
  if (cur) els.repProfile.value = cur;
}

function repQuery() {
  const days = els.repDays?.value || "7";
  const profile = els.repProfile?.value || "";
  const q = new URLSearchParams({ days });
  if (profile) q.set("profile", profile);
  return q;
}

async function fetchStats() {
  lastStats = await api(`/api/reports/stats?${repQuery()}`);
  const t = lastStats.totals || {};
  if (els.repSideSummary) {
    els.repSideSummary.textContent = `${t.scans || 0} escaneos · ${t.compliance_rate || 0}% cumple`;
  }
  if (els.repSideList) {
    els.repSideList.innerHTML = `
      <li><span>Cumple</span><span class="conf">${t.compliant || 0}</span></li>
      <li><span>No cumple</span><span class="conf">${t.non_compliant || 0}</span></li>
      <li><span>Enrolados</span><span class="conf">${t.workers_enrolled || 0}</span></li>`;
  }
  return lastStats;
}

function metricHtml(stats) {
  const t = stats.totals || {};
  return `<div class="rep-hero">
    <div class="rep-metric"><b>${t.scans || 0}</b><span>Escaneos</span></div>
    <div class="rep-metric"><b>${t.compliance_rate || 0}%</b><span>Cumplimiento</span></div>
    <div class="rep-metric"><b>${t.safety_score ?? t.compliance_rate ?? 0}</b><span>Safety Score</span></div>
    <div class="rep-metric"><b>${t.non_compliant || 0}</b><span>Incumplimientos</span></div>
    <div class="rep-metric"><b>${t.workers_enrolled || 0}</b><span>Personas</span></div>
  </div>`;
}

function barsHtml(rows, labelKey, countKey) {
  const max = Math.max(1, ...rows.map((r) => r[countKey] || 0));
  return rows
    .map((r) => {
      const pct = Math.round(((r[countKey] || 0) / max) * 100);
      return `<div class="bar-row"><span>${r[labelKey]}</span><div class="bar-track"><i style="width:${pct}%"></i></div><span>${r[countKey]}</span></div>`;
    })
    .join("");
}

function tableWorkers(rows) {
  if (!rows.length) return `<p class="muted">Sin datos en este rango</p>`;
  return `<table class="rep-table"><thead><tr><th>Trabajador</th><th>RUT</th><th>OK</th><th>Falla</th><th>Score</th><th>Total</th></tr></thead><tbody>
    ${rows
      .map(
        (w) =>
          `<tr><td>${w.name || "—"}</td><td>${w.rut || "—"}</td><td>${w.ok}</td><td>${w.bad}</td><td>${w.safety_score ?? "—"}</td><td>${w.total}</td></tr>`
      )
      .join("")}
  </tbody></table>`;
}

function downloadUrl(path) {
  const a = document.createElement("a");
  a.href = path;
  a.download = "";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

async function openReport(key) {
  currentRep = key;
  $$(".rep-item").forEach((b) => b.classList.toggle("active", b.dataset.rep === key));
  if (!els.reportsContent) return;
  els.reportsContent.innerHTML = `<p class="muted">Cargando…</p>`;

  try {
    if (key.startsWith("notif_")) {
      await renderNotifView(key);
      return;
    }

    if (key === "csv_all") {
      downloadUrl(`/api/reports/export.csv?${repQuery()}`);
      els.reportsContent.innerHTML = `<h3 class="rep-section-title">Exportar CSV</h3><p>Descarga iniciada (todos los escaneos del rango).</p>`;
      return;
    }
    if (key === "csv_bad") {
      const q = repQuery();
      q.set("only_bad", "true");
      downloadUrl(`/api/reports/export.csv?${q}`);
      els.reportsContent.innerHTML = `<h3 class="rep-section-title">Incumplimientos CSV</h3><p>Descarga iniciada.</p>`;
      return;
    }
    if (key === "txt") {
      downloadUrl(`/api/reports/summary.txt?${repQuery()}`);
      els.reportsContent.innerHTML = `<h3 class="rep-section-title">Resumen TXT</h3><p>Descarga iniciada.</p>`;
      return;
    }

    const stats = await fetchStats();
    const days = Number(els.repDays?.value || 7);

    if (key === "safety_score") {
      const score = stats.totals?.safety_score ?? stats.totals?.compliance_rate ?? 0;
      const br = stats.totals?.safety_breakdown || {};
      const ranked = [...(stats.worker_ranking || [])].sort(
        (a, b) => (b.safety_score || 0) - (a.safety_score || 0)
      );
      els.reportsContent.innerHTML = `
        <h3 class="rep-section-title">Safety Score</h3>
        <div class="rep-hero">
          <div class="rep-metric"><b>${score}</b><span>Nota global /100</span></div>
          <div class="rep-metric"><b>${stats.totals?.compliance_rate || 0}%</b><span>Cumplimiento</span></div>
          <div class="rep-metric"><b>${stats.totals?.scans || 0}</b><span>Escaneos</span></div>
        </div>
        <p class="card-meta">Últimos ${days} días · pondera cumplimiento, faltas críticas y desconocidos.</p>
        <ul class="item-list">
          <li><span>Penalización desconocidos</span><span class="conf">-${br.penalty_unknown ?? 0}</span></li>
          <li><span>Penalización EPP crítico</span><span class="conf">-${br.penalty_critical_missing ?? 0}</span></li>
          <li><span>Eventos EPP crítico</span><span class="conf">${br.critical_missing_events ?? 0}</span></li>
        </ul>
        <h4>Por trabajador</h4>
        ${tableWorkers(ranked)}`;
    } else if (key === "overview") {
      els.reportsContent.innerHTML = `
        <h3 class="rep-section-title">Resumen general</h3>
        ${metricHtml(stats)}
        <p class="card-meta">Últimos ${days} días${stats.profile ? ` · perfil ${stats.profile}` : ""}.</p>
        <h4>EPP faltante</h4>
        ${barsHtml(stats.missing_epp || [], "item", "count") || `<p class="muted">Sin faltantes</p>`}`;
    } else if (key === "byday") {
      els.reportsContent.innerHTML = `
        <h3 class="rep-section-title">Cumplimiento por día</h3>
        ${metricHtml(stats)}
        <table class="rep-table"><thead><tr><th>Día</th><th>Total</th><th>OK</th><th>Falla</th></tr></thead>
        <tbody>${(stats.by_day || [])
          .map((d) => `<tr><td>${d.day}</td><td>${d.total}</td><td>${d.ok}</td><td>${d.bad}</td></tr>`)
          .join("") || `<tr><td colspan="4">Sin datos</td></tr>`}</tbody></table>`;
    } else if (key === "ranking") {
      els.reportsContent.innerHTML = `
        <h3 class="rep-section-title">Ranking trabajadores</h3>
        <p class="card-meta">Ordenado por incumplimientos.</p>
        ${tableWorkers(stats.worker_ranking || [])}`;
    } else if (key === "missing") {
      els.reportsContent.innerHTML = `
        <h3 class="rep-section-title">EPP faltante frecuente</h3>
        ${barsHtml(stats.missing_epp || [], "item", "count") || `<p class="muted">Sin datos</p>`}`;
    } else if (key === "profiles") {
      els.reportsContent.innerHTML = `
        <h3 class="rep-section-title">Por perfil de faena</h3>
        ${barsHtml(stats.by_profile || [], "profile", "count") || `<p class="muted">Sin datos</p>`}`;
    } else if (key === "unknown") {
      els.reportsContent.innerHTML = `
        <h3 class="rep-section-title">Sin identidad</h3>
        ${metricHtml(stats)}
        <p>Escaneos sin trabajador asociado: <strong>${stats.totals?.unknown_scans || 0}</strong></p>
        <p class="card-meta">Enrolá en Personas para reducir desconocidos.</p>`;
    } else if (key === "daily" || key === "weekly" || key === "monthly" || key === "print") {
      const map = { daily: 1, weekly: 7, monthly: 30, print: days };
      if (key !== "print") els.repDays.value = String(map[key]);
      const report = await api(`/api/reports/print?${repQuery()}`);
      els.reportsContent.innerHTML = `
        <h3 class="rep-section-title">${report.title || "Informe"}</h3>
        ${metricHtml(report.stats || stats)}
        <div class="rep-actions">
          <button type="button" class="btn primary" id="btnPrintRep">Imprimir / PDF</button>
          <button type="button" class="btn secondary" id="btnCopyRep">Copiar texto</button>
          <button type="button" class="btn ghost" id="btnDlTxt">Descargar TXT</button>
        </div>
        <pre class="rep-pre" id="repPrintText">${(report.text || "").replace(/</g, "&lt;")}</pre>`;
      $("#btnPrintRep")?.addEventListener("click", () => {
        const q = repQuery().toString();
        const w = window.open(`/api/reports/print.html?${q}`, "_blank");
        if (w) {
          w.addEventListener("load", () => {
            try {
              w.focus();
              w.print();
            } catch (_) {}
          });
        }
      });
      $("#btnCopyRep")?.addEventListener("click", async () => {
        await navigator.clipboard.writeText(report.text || "");
        els.repSideSummary.textContent = "Informe copiado al portapapeles";
      });
      $("#btnDlTxt")?.addEventListener("click", () => downloadUrl(`/api/reports/summary.txt?${repQuery()}`));
    } else {
      els.reportsContent.innerHTML = `<p class="muted">Opción no implementada</p>`;
    }
  } catch (err) {
    els.reportsContent.innerHTML = `<p class="muted">${err.message}</p>`;
  }
}

async function renderNotifView(key) {
  notifConfig = await api("/api/notifications/config");
  const ch = notifConfig.channels || {};
  const tpl = notifConfig.template || {};

  if (key === "notif_setup") {
    const ac = notifConfig.access_control || {};
    const gate = ac.gate || {};
    const mb = gate.modbus || {};
    const hd = gate.http_dual || {};
    const wg = gate.wiegand || {};
    const et = notifConfig.email_transport || {};
    const emailHint =
      et.mode === "resend"
        ? "Email real vía Resend"
        : et.mode === "smtp"
          ? `Email real vía SMTP (${et.smtp_host || "host"})`
          : "Sin SMTP/Resend → solo abre mailto en el navegador";
    const driver = gate.driver || "esp32";
    els.reportsContent.innerHTML = `
      <h3 class="rep-section-title">Canales de notificación</h3>
      <p class="card-meta">${emailHint}</p>
      <form class="rep-form" id="notifChannelsForm">
        <label><span>Webhook (Slack / Teams / Discord / genérico)</span>
          <input type="checkbox" id="nWhEn" ${ch.webhook?.enabled ? "checked" : ""}/> Activar
          <input type="url" id="nWhUrl" placeholder="https://hooks.slack.com/..." value="${ch.webhook?.url || ""}"/>
        </label>
        <label><span>WhatsApp / API webhook</span>
          <input type="checkbox" id="nWaEn" ${ch.whatsapp_webhook?.enabled ? "checked" : ""}/> Activar
          <input type="url" id="nWaUrl" placeholder="https://..." value="${ch.whatsapp_webhook?.url || ""}"/>
        </label>
        <label><span>WhatsApp Business Cloud (Meta)</span>
          <input type="checkbox" id="nWaCloudEn" ${ch.whatsapp_cloud?.enabled ? "checked" : ""}/> Activar
          <small class="card-meta">Token en WHATSAPP_TOKEN / VIGIEPP_WHATSAPP_TOKEN del servidor</small>
          <input type="text" id="nWaCloudPhoneId" placeholder="Phone number ID" value="${ch.whatsapp_cloud?.phone_number_id || ""}"/>
          <input type="text" id="nWaCloudTo" placeholder="+56912345678 o varios separados por coma" value="${ch.whatsapp_cloud?.to || ""}"/>
        </label>
        <label><span>Email</span>
          <input type="checkbox" id="nEmEn" ${ch.email?.enabled ? "checked" : ""}/> Activar
          <input type="email" id="nEmTo" placeholder="seguridad@empresa.cl" value="${ch.email?.to || ""}"/>
          <input type="email" id="nEmCc" placeholder="cc opcional" value="${ch.email?.cc || ""}"/>
        </label>
        <p class="card-kicker">Driver de acceso físico</p>
        <label><span>Torniquete / relé / Wiegand</span>
          <select id="nGateDriver">
            <option value="esp32" ${driver === "esp32" ? "selected" : ""}>ESP32 HTTP (/ok /alarma)</option>
            <option value="modbus" ${driver === "modbus" ? "selected" : ""}>Modbus TCP (coils)</option>
            <option value="http_dual" ${driver === "http_dual" ? "selected" : ""}>HTTP dual (allow/deny URL)</option>
            <option value="wiegand" ${driver === "wiegand" ? "selected" : ""}>Gateway Wiegand HTTP</option>
          </select>
          <input type="checkbox" id="nGateHwEn" ${gate.enabled ? "checked" : ""}/> Activar driver
        </label>
        <div id="nGateEsp32" class="${driver === "esp32" ? "" : "hidden"}">
          <p class="card-kicker">ESP32 / baliza</p>
          <input type="url" id="nHwUrl" placeholder="http://192.168.1.50" value="${gate.esp32?.base_url || ac.hardware?.base_url || ""}"/>
          <label class="check"><input type="checkbox" id="nHwBad" ${gate.on_non_compliant !== false ? "checked" : ""}/> Alarma en incumplimiento EPP</label>
          <label class="check"><input type="checkbox" id="nHwUnk" ${gate.on_unknown_face !== false ? "checked" : ""}/> Alarma en rostro desconocido</label>
          <label class="check"><input type="checkbox" id="nHwOk" ${gate.auto_ok !== false ? "checked" : ""}/> /ok automático si EPP cumple</label>
        </div>
        <div id="nGateModbus" class="${driver === "modbus" ? "" : "hidden"}">
          <p class="card-kicker">Modbus TCP</p>
          <input type="text" id="nMbHost" placeholder="192.168.1.20" value="${mb.host || ""}"/>
          <input type="number" id="nMbPort" placeholder="502" value="${mb.port || 502}"/>
          <input type="number" id="nMbUnit" placeholder="Unit ID" value="${mb.unit_id || 1}"/>
          <input type="number" id="nMbCoilAllow" placeholder="Coil allow" value="${mb.coil_allow || 0}"/>
          <input type="number" id="nMbCoilDeny" placeholder="Coil deny" value="${mb.coil_deny || 1}"/>
        </div>
        <div id="nGateHttp" class="${driver === "http_dual" ? "" : "hidden"}">
          <p class="card-kicker">HTTP dual</p>
          <input type="url" id="nHdAllow" placeholder="URL allow" value="${hd.allow_url || ""}"/>
          <input type="url" id="nHdDeny" placeholder="URL deny" value="${hd.deny_url || ""}"/>
        </div>
        <div id="nGateWiegand" class="${driver === "wiegand" ? "" : "hidden"}">
          <p class="card-kicker">Wiegand gateway</p>
          <input type="url" id="nWgBase" placeholder="http://192.168.1.30" value="${wg.base_url || ""}"/>
          <input type="text" id="nWgAllow" placeholder="/open" value="${wg.allow_path || "/open"}"/>
          <input type="text" id="nWgDeny" placeholder="/close" value="${wg.deny_path || "/close"}"/>
        </div>
        <div class="rep-actions" style="margin:0.5rem 0 1rem">
          <button type="button" class="btn secondary" id="btnHwAlarma">Probar deny</button>
          <button type="button" class="btn secondary" id="btnHwOk">Probar allow</button>
        </div>
        <pre class="rep-pre" id="hwTestOut" style="display:none">—</pre>
        <p class="card-kicker">Abrir acceso (portería lógica)</p>
        <label><span>Control de acceso</span>
          <input type="checkbox" id="nAcEn" ${ac.enabled ? "checked" : ""}/> Activar gate
          <small class="card-meta">Allow solo si identidad conocida + EPP OK. Driver físico según selección arriba.</small>
          <label class="check"><input type="checkbox" id="nAcId" ${ac.require_identity !== false ? "checked" : ""}/> Exigir identidad</label>
          <label class="check"><input type="checkbox" id="nAcNf" ${ac.notify !== false ? "checked" : ""}/> Notificar decisión</label>
        </label>
        <button class="btn primary" type="submit">Guardar canales</button>
      </form>`;
    const toggleGatePanels = () => {
      const d = $("#nGateDriver")?.value || "esp32";
      $("#nGateEsp32")?.classList.toggle("hidden", d !== "esp32");
      $("#nGateModbus")?.classList.toggle("hidden", d !== "modbus");
      $("#nGateHttp")?.classList.toggle("hidden", d !== "http_dual");
      $("#nGateWiegand")?.classList.toggle("hidden", d !== "wiegand");
    };
    $("#nGateDriver")?.addEventListener("change", toggleGatePanels);
    const hwTest = async (action) => {
      const out = $("#hwTestOut");
      if (out) out.style.display = "block";
      try {
        const res = await api("/api/notifications/hardware/test", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action }),
        });
        if (out) out.textContent = JSON.stringify(res, null, 2);
        els.repSideSummary.textContent = res.ok ? `Hardware ${action} OK` : `Hardware error: ${res.detail || ""}`;
      } catch (err) {
        if (out) out.textContent = String(err.message || err);
      }
    };
    $("#btnHwAlarma")?.addEventListener("click", () => hwTest("alarma"));
    $("#btnHwOk")?.addEventListener("click", () => hwTest("ok"));
    $("#notifChannelsForm")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const body = {
        channels: {
          webhook: { enabled: $("#nWhEn").checked, url: $("#nWhUrl").value.trim() },
          whatsapp_webhook: { enabled: $("#nWaEn").checked, url: $("#nWaUrl").value.trim() },
          whatsapp_cloud: {
            enabled: $("#nWaCloudEn").checked,
            phone_number_id: $("#nWaCloudPhoneId").value.trim(),
            to: $("#nWaCloudTo").value.trim(),
          },
          email: {
            enabled: $("#nEmEn").checked,
            to: $("#nEmTo").value.trim(),
            cc: $("#nEmCc")?.value.trim() || "",
          },
        },
        access_control: {
          enabled: $("#nAcEn").checked,
          require_identity: $("#nAcId").checked,
          notify: $("#nAcNf").checked,
          hardware: {
            enabled: $("#nGateDriver").value === "esp32" && $("#nGateHwEn").checked,
            base_url: $("#nHwUrl").value.trim(),
            alarma_path: "/alarma",
            ok_path: "/ok",
            method: "GET",
            on_non_compliant: $("#nHwBad").checked,
            on_unknown_face: $("#nHwUnk").checked,
            auto_ok: $("#nHwOk").checked,
          },
          gate: {
            enabled: $("#nGateHwEn").checked,
            driver: $("#nGateDriver").value,
            on_non_compliant: $("#nHwBad").checked,
            on_unknown_face: $("#nHwUnk").checked,
            auto_ok: $("#nHwOk").checked,
            esp32: {
              enabled: $("#nGateDriver").value === "esp32" && $("#nGateHwEn").checked,
              base_url: $("#nHwUrl").value.trim(),
              alarma_path: "/alarma",
              ok_path: "/ok",
              method: "GET",
            },
            modbus: {
              host: $("#nMbHost").value.trim(),
              port: Number($("#nMbPort").value) || 502,
              unit_id: Number($("#nMbUnit").value) || 1,
              coil_allow: Number($("#nMbCoilAllow").value) || 0,
              coil_deny: Number($("#nMbCoilDeny").value) || 1,
            },
            http_dual: {
              allow_url: $("#nHdAllow").value.trim(),
              deny_url: $("#nHdDeny").value.trim(),
            },
            wiegand: {
              base_url: $("#nWgBase").value.trim(),
              allow_path: $("#nWgAllow").value.trim() || "/open",
              deny_path: $("#nWgDeny").value.trim() || "/close",
            },
          },
        },
      };
      const res = await api("/api/notifications/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      notifConfig = res.config;
      els.repSideSummary.textContent = "Canales guardados";
    });
    return;
  }

  if (key === "notif_rules") {
    els.reportsContent.innerHTML = `
      <h3 class="rep-section-title">Reglas de alerta</h3>
      <p class="card-meta">La coolora es por persona + tipo de alerta (no bloquea a otros).</p>
      <form class="rep-form" id="notifRulesForm">
        <label><input type="checkbox" id="nEnabled" ${notifConfig.enabled ? "checked" : ""}/> Activar notificaciones</label>
        <label><input type="checkbox" id="nOnBad" ${notifConfig.on_non_compliant ? "checked" : ""}/> Avisar en incumplimiento EPP</label>
        <label><input type="checkbox" id="nOnUnknown" ${notifConfig.on_unknown_face ? "checked" : ""}/> Avisar rostro desconocido</label>
        <label><input type="checkbox" id="nOnZone" ${notifConfig.on_zone_alert !== false ? "checked" : ""}/> Avisar zonas / near-miss</label>
        <label><input type="checkbox" id="nOnlyKnown" ${notifConfig.only_known_workers ? "checked" : ""}/> Solo trabajadores conocidos (EPP)</label>
        <label><span>Cooldownora entre avisos (segundos)</span>
          <input type="number" id="nCooldown" min="0" max="3600" value="${notifConfig.cooldown_seconds ?? 120}"/>
        </label>
        <button class="btn primary" type="submit">Guardar reglas</button>
      </form>`;
    $("#notifRulesForm")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const res = await api("/api/notifications/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          enabled: $("#nEnabled").checked,
          on_non_compliant: $("#nOnBad").checked,
          on_unknown_face: $("#nOnUnknown").checked,
          on_zone_alert: $("#nOnZone").checked,
          only_known_workers: $("#nOnlyKnown").checked,
          cooldown_seconds: Number($("#nCooldown").value) || 0,
        }),
      });
      notifConfig = res.config;
      els.repSideSummary.textContent = "Reglas guardadas";
    });
    return;
  }

  if (key === "notif_template") {
    els.reportsContent.innerHTML = `
      <h3 class="rep-section-title">Plantilla de mensaje</h3>
      <p class="card-meta">Variables: {name} {rut} {profile} {summary} {missing} {ts}</p>
      <form class="rep-form" id="notifTplForm">
        <label><span>Asunto</span><input type="text" id="nSub" value="${(tpl.subject || "").replace(/"/g, "&quot;")}"/></label>
        <label><span>Cuerpo</span><textarea id="nBody">${tpl.body || ""}</textarea></label>
        <button class="btn primary" type="submit">Guardar plantilla</button>
      </form>`;
    $("#notifTplForm")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const res = await api("/api/notifications/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ template: { subject: $("#nSub").value, body: $("#nBody").value } }),
      });
      notifConfig = res.config;
      els.repSideSummary.textContent = "Plantilla guardada";
    });
    return;
  }

  if (key === "notif_test") {
    els.reportsContent.innerHTML = `
      <h3 class="rep-section-title">Probar / enviar ahora</h3>
      <p>Envía una alerta de prueba por los canales activos o dispara el ESP32.</p>
      <div class="rep-actions">
        <button type="button" class="btn primary" id="btnNotifTest">Enviar prueba</button>
        <button type="button" class="btn secondary" id="btnNotifManual">Enviar alerta manual</button>
        <button type="button" class="btn secondary" id="btnHwAlarma2">ESP32 /alarma</button>
        <button type="button" class="btn secondary" id="btnHwOk2">ESP32 /ok</button>
      </div>
      <pre class="rep-pre" id="notifTestOut">—</pre>`;
    $("#btnNotifTest")?.addEventListener("click", async () => {
      const res = await api("/api/notifications/test", { method: "POST" });
      $("#notifTestOut").textContent = JSON.stringify(res, null, 2);
      if (res.mailto) window.location.href = res.mailto;
    });
    $("#btnNotifManual")?.addEventListener("click", async () => {
      const res = await api("/api/notifications/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "Alerta manual",
          summary: "Envío manual desde Informes",
          missing: ["casco"],
          force: true,
        }),
      });
      $("#notifTestOut").textContent = JSON.stringify(res, null, 2);
      if (res.mailto) window.location.href = res.mailto;
    });
    $("#btnHwAlarma2")?.addEventListener("click", async () => {
      const res = await api("/api/notifications/hardware/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "alarma" }),
      });
      $("#notifTestOut").textContent = JSON.stringify(res, null, 2);
    });
    $("#btnHwOk2")?.addEventListener("click", async () => {
      const res = await api("/api/notifications/hardware/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "ok" }),
      });
      $("#notifTestOut").textContent = JSON.stringify(res, null, 2);
    });
    return;
  }

  if (key === "notif_log") {
    const log = await api("/api/notifications/log?limit=40");
    els.reportsContent.innerHTML = `
      <h3 class="rep-section-title">Historial de envíos</h3>
      <table class="rep-table"><thead><tr><th>Fecha</th><th>Tipo</th><th>Estado</th><th>Asunto</th></tr></thead>
      <tbody>${
        log.length
          ? log
              .map(
                (r) =>
                  `<tr><td>${(r.ts || "").slice(0, 19)}</td><td>${r.kind || "—"}</td><td>${r.ok ? "OK" : "Falló"}</td><td>${r.subject || "—"}</td></tr>`
              )
              .join("")
          : `<tr><td colspan="4">Sin envíos aún</td></tr>`
      }</tbody></table>`;
  }
}

  return { openReport, fillRepProfiles, fetchStats, downloadUrl, getCurrentRep: () => currentRep };
}
