(() => {
  const api = window.RaptorAPI;
  const content = document.querySelector("#admin-content");
  const dialog = document.querySelector("#record-dialog");
  const form = document.querySelector("#record-form");
  const $ = (selector, root = document) => root.querySelector(selector);
  let currentPage = "dashboard", currentUser = null, permissions = {};
  let editing = null;
  let teams = [], tournaments = [];
  // CSP forbids inline onerror, so a missing avatar file is caught here
  // (capture phase: media error events do not bubble) and swapped for initials.
  document.addEventListener("error", event => {
    const img = event.target;
    if (!(img instanceof HTMLImageElement) || !img.classList.contains("admin-player-avatar-art")) return;
    const fallback = img.dataset.fallback || "?";
    const span = document.createElement("span");
    span.className = "admin-player-avatar-fallback";
    span.textContent = fallback;
    img.replaceWith(span);
    const holder = span.closest(".admin-player-avatar");
    if (holder) holder.classList.remove("has-art");
  }, true);
  const config = {
    players: { title: "Players", singular: "Player", fields: [{ key: "name", label: "Full name", required: true }, { key: "ign", label: "In-game name", required: true }, { key: "role", label: "Role", required: true }, { key: "game", label: "Game", type: "select", options: ["BGMI", "Free Fire", "Valorant", "Other"] }, { key: "team_id", label: "Team", type: "select", optionsFrom: "teams", optional: true }, { key: "status", label: "Status", type: "select", options: ["Active", "Inactive", "Trial"], required: true }, { key: "avatar", label: "Player art", type: "avatar", optional: true, wide: true }] },
    teams: { title: "Teams", singular: "Team", fields: [{ key: "name", label: "Team name", required: true }, { key: "game", label: "Game", type: "select", options: ["BGMI", "Free Fire", "Valorant", "Other"], required: true }, { key: "status", label: "Status", type: "select", options: ["Active", "Recruiting", "Inactive"] }, { key: "accent", label: "Team color", type: "select", options: ["violet", "amber", "pink", "cyan"] }, { key: "description", label: "Description", type: "textarea", wide: true }] },
    tournaments: { title: "Competitions", singular: "Competition", fields: [{ key: "name", label: "Competition name", required: true }, { key: "game", label: "Game", type: "select", options: ["BGMI", "Free Fire", "Valorant", "Other"], required: true }, { key: "team_id", label: "Team", type: "select", optionsFrom: "teams", optional: true }, { key: "date", label: "Date", type: "date", required: true }, { key: "prize_pool", label: "Prize pool (₹)", type: "number", min: "0", required: true }, { key: "status", label: "Status", type: "select", options: ["Upcoming", "Ongoing", "Completed"], required: true }, { key: "location", label: "Location", placeholder: "Online or city" }] },
    matches: { title: "Matches", singular: "Match", fields: [{ key: "name", label: "Match name", required: true }, { key: "game", label: "Game", type: "select", options: ["BGMI", "Free Fire", "Valorant", "Other"], required: true }, { key: "team_id", label: "Team", type: "select", optionsFrom: "teams", optional: true }, { key: "date", label: "Date", type: "date", required: true }, { key: "time", label: "Time", placeholder: "08:00 PM", required: true }, { key: "opponent", label: "Opponent" }, { key: "tournament_id", label: "Competition", type: "select", optionsFrom: "tournaments", optional: true }, { key: "status", label: "Status", type: "select", options: ["Upcoming", "Live", "Completed"], required: true }, { key: "result", label: "Result" }] },
    expenses: { title: "Expenses", singular: "Expense", fields: [{ key: "title", label: "Expense title", required: true }, { key: "category", label: "Category", type: "select", options: ["Tournament", "Equipment", "Travel", "Operations", "Other"], required: true }, { key: "amount", label: "Amount (₹)", type: "number", min: "0", step: "0.01", required: true }, { key: "date", label: "Date", type: "date", required: true }, { key: "notes", label: "Notes", type: "textarea", wide: true }] },
    performance_records: { title: "Performance", singular: "Performance record", fields: [{ key: "player_id", label: "Player", type: "select", optionsFrom: "players", required: true }, { key: "category", label: "Category", required: true }, { key: "score", label: "Score (0–100)", type: "number", min: "0", max: "100", required: true }, { key: "date", label: "Date", type: "date", required: true }, { key: "notes", label: "Notes", type: "textarea", wide: true }] }
  };
  const escape = value => String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const money = value => "₹ " + Number(value || 0).toLocaleString("en-IN", { maximumFractionDigits: 2 });
  const dateLabel = value => value ? new Date(value + "T00:00:00").toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) : "—";
  const timestampLabel = value => { if (!value) return "—"; const text = String(value); const date = new Date(text.includes("T") ? text : text.replace(" ", "T") + "Z"); return Number.isNaN(date.getTime()) ? text.slice(0, 10) : date.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }); };
  const columns = {
    players: [["name", "Name"], ["ign", "IGN"], ["role", "Role"], ["team_name", "Team"], ["status", "Status"]],
    teams: [["name", "Team"], ["game", "Game"], ["players_count", "Players"], ["status", "Status"]],
    tournaments: [["name", "Name"], ["game", "Game"], ["date", "Date"], ["prize_pool", "Prize Pool"], ["status", "Status"]],
    matches: [["name", "Match"], ["game", "Game"], ["date", "Date"], ["time", "Time"], ["opponent", "Opponent"], ["status", "Status"]],
    expenses: [["title", "Expense"], ["category", "Category"], ["date", "Date"], ["amount", "Amount"]],
    performance_records: [["date", "Date"], ["player_name", "Player"], ["category", "Category"], ["score", "Score"], ["team_name", "Team"]]
  };
  const svgIcon = (name, className = "ui-icon") => `<svg class="${className}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><use href="#icon-${name}"></use></svg>`;
  const icons = { players: svgIcon("user"), teams: svgIcon("shield"), tournaments: svgIcon("trophy"), matches: svgIcon("flag"), expenses: svgIcon("receipt"), performance: svgIcon("activity"), reports: svgIcon("chart") };
  const teamLogoKeys = ["raptor", "apex", "vitality", "phoenix", "shadow", "vortex"];
  const avatarPalettes = [["#6b3ce9", "#a476ff"], ["#d65a35", "#f3a15e"], ["#168a74", "#58d4b2"], ["#2d6ed6", "#6db7ff"], ["#b63c9e", "#f47bdb"], ["#a47a15", "#ecd06a"]];
  const normalizeKey = value => String(value ?? "").toLowerCase().replace(/[^a-z0-9]+/g, "");
  const initials = value => String(value ?? "").trim().split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0]).join("").toUpperCase() || "?";
  const teamLogoKey = team => { const key = normalizeKey(team?.name); return teamLogoKeys.find(candidate => key.includes(candidate)) || ""; };
  const AVATAR_FILES = ["01-hood.png", "02-raptor.png", "03-trooper.png", "04-oni.png", "05-wolf.png", "06-skull.png", "07-fox.png", "08-phoenix.png"];
  const avatarLabel = file => file.replace(/\.png$/i, "").replace(/^\d+-/, "").replace(/-/g, " ");
  // Role abbreviation for the small corner badge — the role must actually read.
  const ROLE_ABBREV = { igl: "IGL", leader: "IGL", shotcaller: "IGL", support: "SUP", supporter: "SUP", rusher: "RSH", assaulter: "ATK", entry: "ATK", initiator: "INI", flex: "FLX", duelist: "DUE", controller: "CTL", bomber: "BMB", sniper: "SNP", lurker: "LRK" };
  const roleAbbrev = role => {
    const key = normalizeKey(role);
    if (ROLE_ABBREV[key]) return ROLE_ABBREV[key];
    const hit = Object.keys(ROLE_ABBREV).find(candidate => key.includes(candidate));
    if (hit) return ROLE_ABBREV[hit];
    return String(role || "").trim().slice(0, 3).toUpperCase() || "?";
  };
  const roleTint = role => {
    const key = normalizeKey(role);
    if (key.includes("igl") || key.includes("lead") || key.includes("shotcaller")) return "#f0b429";
    if (key.includes("support")) return "#2fb37f";
    if (key.includes("assault") || key.includes("rush") || key.includes("entry") || key.includes("duel") || key.includes("bomb")) return "#ef5f6b";
    if (key.includes("initiat") || key.includes("control") || key.includes("flex")) return "#4aa8ff";
    if (key.includes("snipe") || key.includes("lurk")) return "#b06cff";
    return "#8b6cff";
  };
  const playerAvatar = player => {
    const name = player?.name || player?.ign || "Player";
    const art = String(player?.avatar || "").trim();
    const hasArt = AVATAR_FILES.includes(art);
    let hash = 0;
    for (const character of name) hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
    const [from, to] = avatarPalettes[hash % avatarPalettes.length];
    const visual = hasArt
      ? `<img class="admin-player-avatar-art" src="/assets/players/${escape(art)}" alt="" loading="lazy" decoding="async" data-fallback="${escape(initials(name))}">`
      : escape(initials(name));
    const role = String(player?.role || "").trim();
    const badge = role
      ? `<span class="admin-avatar-role" style="--role-tint:${roleTint(role)}" title="${escape(role)}">${escape(roleAbbrev(role))}</span>`
      : "";
    return `<span class="admin-player-avatar${hasArt ? " has-art" : ""}" style="--avatar-from:${from};--avatar-to:${to}" aria-hidden="true">${visual}${badge}</span>`;
  };
  const teamLogoTile = team => {
    const key = teamLogoKey(team);
    if (!key) return `<span class="admin-team-logo admin-team-logo-fallback" aria-hidden="true">${escape(initials(team?.name || "Team"))}</span>`;
    return `<span class="admin-team-logo"><img src="/assets/team-logos/${key}${key === "apex" ? ".jpg" : ".png"}" alt="" loading="lazy" decoding="async"></span>`;
  };
  function entityCell(entity, key, item) {
    if (entity === "players" && key === "name") return `<div class="admin-identity">${playerAvatar(item)}<span class="admin-identity-name">${escape(item[key] ?? "—")}</span></div>`;
    if (entity === "teams" && key === "name") return `<div class="admin-identity">${teamLogoTile(item)}<span class="admin-identity-name">${escape(item[key] ?? "—")}</span></div>`;
    if (key === "status") return `<span class="status-chip status-${escape(String(item[key] || "").toLowerCase())}">${escape(item[key] || "—")}</span>`;
    if (key === "date") return dateLabel(item[key]);
    if (key === "prize_pool" || key === "amount") return money(item[key]);
    return escape(item[key] ?? "—");
  }

  async function start() {
    try { currentUser = await api.me(); permissions = currentUser.permissions || {}; document.querySelector(".profile-name").textContent = currentUser.name; document.querySelector(".avatar").textContent = currentUser.name.slice(0, 1).toUpperCase(); const roleLabel = currentUser.role[0].toUpperCase() + currentUser.role.slice(1); const roleBadge = document.querySelector("#profile-role"); roleBadge.textContent = roleLabel; roleBadge.hidden = currentUser.name.trim().toLowerCase() === currentUser.role.toLowerCase(); document.querySelectorAll(".side-link[data-permission]").forEach(link => { link.hidden = !permissions[link.dataset.permission]; }); const preferencesCaption = document.querySelector(".nav-caption-second"); if (preferencesCaption) preferencesCaption.hidden = !permissions["system.configure"]; const requested = location.hash.slice(1) || "dashboard"; await renderPage(requested); }
    catch { location.replace("/login"); }
  }
  async function renderPage(page) {
    currentPage = ["dashboard", "assistant", "settings", "users", "assignments", "reports", ...Object.keys(config)].includes(page) ? page : "dashboard";
    const navLink = document.querySelector(`.side-link[data-page="${CSS.escape(currentPage)}"]`);
    if (navLink?.hidden) { currentPage = "dashboard"; history.replaceState(null, "", "#dashboard"); }
    document.querySelectorAll(".side-link").forEach(link => {
      const active = link.dataset.page === currentPage;
      link.classList.toggle("active", active);
      if (active) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
    const title = config[currentPage]?.title || ({ dashboard: "Dashboard", assistant: "Raptor AI", settings: "Settings", users: "Users", assignments: "Coach Assignments", reports: "Reports" })[currentPage];
    $("#crumb-current").textContent = title;
    content.innerHTML = `<div class="loading-state">Loading ${escape(title.toLowerCase())}…</div>`;
    try {
      if (currentPage === "dashboard") await renderDashboard();
      else if (config[currentPage]) await renderEntity(currentPage);
      else if (currentPage === "assistant") renderAssistant();
      else if (currentPage === "reports") await renderReports();
      else if (currentPage === "users") await renderUsers();
      else if (currentPage === "assignments") await renderAssignments();
      else renderSettings();
    } catch (error) { content.innerHTML = `<div class="empty-state">${escape(error.message)} <button class="button button-light" id="retry-page">Try again</button></div>`; $("#retry-page")?.addEventListener("click", () => renderPage(currentPage)); }
  }
  function heading(title, description, action = "") { return `<div class="page-heading"><div><h1>${escape(title)}</h1><p>${escape(description)}</p></div>${action}</div>`; }
  async function renderDashboard() {
    const data = await api.request("/api/dashboard");
    const statItems = [["players", "Players in scope", icons.players, ""], ["teams", "Teams in scope", icons.teams, "blue"], ["tournaments", "Competitions", icons.tournaments, "green"], ...(data.can_view_expenses ? [["expenses", "Total Expenses", icons.expenses, "orange"]] : [])];
    const stats = statItems.map(([key, label, icon, color]) => `<article class="stat-card"><span class="stat-icon ${color}">${icon}</span><span><small>${label}</small><strong>${key === "expenses" ? money(data.stats[key]) : data.stats[key]}</strong></span></article>`).join("");
    const matches = data.matches.length ? data.matches.map(m => `<article class="match-item"><span class="match-game-icon">${escape(m.game.slice(0, 2))}</span><span class="match-info"><b>${escape(m.name)}</b><small><span class="tourney-tag" data-col="game">${escape(m.game)}</span>${m.opponent ? ` · Raptor vs ${escape(m.opponent)}` : ""}</small></span><span class="match-date" data-col="date">${dateLabel(m.date)}<br>${escape(m.time)}</span></article>`).join("") : `<div class="empty-state">No upcoming matches yet.</div>`;
    const activity = data.activity.length ? data.activity.map(a => `<article class="activity-item"><span class="activity-icon">${escape((a.kind || "•").slice(0, 1).toUpperCase())}</span><span class="activity-info"><p>${escape(a.message)}</p><small>${escape(a.created_at)}</small></span></article>`).join("") : `<div class="empty-state">${["admin", "manager"].includes(currentUser.role) ? "Your recent activity will show up here." : "Activity is available to Admin and Manager accounts."}</div>`;
    const activityEyebrow = data.activity.length ? `<span class="eyebrow">LIVE</span>` : "";
    const statGridClass = statItems.length === 3 ? "stat-grid stat-grid-three" : "stat-grid";
    content.innerHTML = `${heading(`${currentUser.role[0].toUpperCase()}${currentUser.role.slice(1)} Dashboard`, `Welcome back, ${currentUser.name}. Here is your authorized workspace.`)}<div class="${statGridClass}">${stats}</div><div class="dashboard-grid"><section class="content-card"><div class="card-heading"><h2>Upcoming Matches</h2><a href="#matches" data-nav="matches">View all ${svgIcon("arrow-up-right")}</a></div><div class="match-list">${matches}</div></section><section class="content-card"><div class="card-heading"><h2>Recent Activity</h2>${activityEyebrow}</div><div class="activity-list">${activity}</div></section></div>`;
    content.querySelectorAll("[data-nav]").forEach(link => link.addEventListener("click", () => renderPage(link.dataset.nav)));
  }
  async function renderReports() {
    const data = await api.request("/api/reports");
    const items = [["teams", "Teams in scope", icons.teams, "blue"], ["players", "Players in scope", icons.players, ""], ["performance_records", "Performance records", icons.performance, "green"], ["matches", "Matches", icons.matches, ""], ["competitions", "Competitions", icons.tournaments, "blue"]];
    if (data.can_view_expenses) items.push(["expenses_total", "Recorded expenses", icons.expenses, "orange"]);
    const cards = items.map(([key, label, icon, color]) => `<article class="stat-card"><span class="stat-icon ${color}">${icon}</span><span><small>${label}</small><strong>${key === "expenses_total" ? money(data[key]) : data[key]}</strong></span></article>`).join("");
    const average = data.average_score === null ? "No performance scores recorded in your scope yet." : `Average performance score: ${data.average_score} / 100`;
    content.innerHTML = `${heading("Reports & Analytics", "Summary of information available to your role.")}<div class="stat-grid report-stat-grid">${cards}</div><section class="content-card"><div class="card-heading"><h2>Performance summary</h2><span class="eyebrow">AUTHORIZED SCOPE</span></div><p>${escape(average)}</p><p class="muted">Teams, players, matches, and scores are counted only for your linked or assigned teams.</p></section>`;
  }
  async function renderEntity(entity) {
    const requests = [api.request(`/api/entities/${entity}`), api.request("/api/entities/teams"), api.request("/api/entities/tournaments")];
    if (entity === "performance_records") requests.push(api.request("/api/entities/players"));
    const [response, teamResponse, tourResponse, playerResponse] = await Promise.all(requests);
    teams = teamResponse.items; tournaments = tourResponse.items;
    window.currentPlayers = playerResponse?.items || [];
    const items = response.items;
    const permissionPrefix = entity === "players" ? "roster" : entity === "expenses" ? "financial" : entity === "performance_records" ? "performance" : entity === "teams" ? "teams" : "matches";
    const canCreate = !!permissions[`${permissionPrefix}.create`], canUpdate = !!permissions[`${permissionPrefix}.update`], canDelete = !!permissions[`${permissionPrefix}.delete`];
    const hasActions = canUpdate || canDelete;
    const rows = items.map(item => `<tr>${columns[entity].map(([key]) => `<td data-col="${key}">${entityCell(entity, key, item)}</td>`).join("")}${hasActions ? `<td><div class="row-actions">${canUpdate ? `<button class="row-action edit" data-edit="${item.id}" aria-label="Edit ${escape(config[entity].singular)}">${svgIcon("edit")}</button>` : ""}${canDelete ? `<button class="row-action delete" data-delete="${item.id}" aria-label="Delete ${escape(config[entity].singular)}">${svgIcon("trash")}</button>` : ""}</div></td>` : ""}</tr>`).join("");
    const add = canCreate ? `<button class="button button-purple" id="add-record">${svgIcon("plus")} Add ${escape(config[entity].singular)}</button>` : "";
    content.innerHTML = `${heading(config[entity].title, `Authorized ${config[entity].title.toLowerCase()} for your role.`, add)}<section class="content-card data-card"><div class="data-toolbar"><h2>${escape(config[entity].title)} <span class="muted">(${items.length})</span></h2><span class="muted">Raptor Esports</span></div>${items.length ? `<div class="table-wrap"><table class="entity-table${hasActions ? " has-actions" : ""}"><thead><tr>${columns[entity].map(([key, label]) => `<th data-col="${key}"><span>${label}</span></th>`).join("")}${hasActions ? "<th><span>Action</span></th>" : ""}</tr></thead><tbody>${rows}</tbody></table></div>` : `<div class="empty-state">No ${escape(config[entity].title.toLowerCase())} in your access scope.</div>`}</section>`;
    $("#add-record")?.addEventListener("click", () => showForm(entity));
    content.querySelectorAll("[data-edit]").forEach(button => button.addEventListener("click", () => showForm(entity, items.find(item => item.id === Number(button.dataset.edit)))));
    content.querySelectorAll("[data-delete]").forEach(button => button.addEventListener("click", async () => { const item = items.find(row => row.id === Number(button.dataset.delete)); if (!window.confirm(`Delete ${item?.name || item?.title || config[entity].singular}? This action cannot be undone.`)) return; try { await api.request(`/api/entities/${entity}/${button.dataset.delete}`, { method: "DELETE" }); await renderPage(entity); } catch (error) { window.alert(error.message); } }));
  }
  function buildOptions(field, value) {
    let options = field.options || [];
    if (field.optionsFrom === "teams") options = teams.map(t => ({ value: t.id, label: t.name }));
    if (field.optionsFrom === "tournaments") options = tournaments.map(t => ({ value: t.id, label: t.name }));
    if (field.optionsFrom === "players") options = window.currentPlayers?.map(p => ({ value: p.id, label: p.name })) || [];
    const selectedValue = value ?? (field.optional ? "" : (typeof options[0] === "string" ? options[0] : options[0]?.value ?? ""));
    const empty = field.optional ? `<option value="" ${selectedValue === "" ? "selected" : ""}>None</option>` : "";
    return empty + options.map(option => { const optionValue = typeof option === "string" ? option : option.value; const label = typeof option === "string" ? option : option.label; return `<option value="${escape(optionValue)}" ${String(optionValue) === String(selectedValue) ? "selected" : ""}>${escape(label)}</option>`; }).join("");
  }
  function showForm(entity, record = null) {
    editing = record ? { entity, id: record.id } : { entity, id: null };
    $("#dialog-title").textContent = `${record ? "Edit" : "Add"} ${config[entity].singular}`;
    $("#dialog-error").textContent = "";
    $("#form-fields").innerHTML = config[entity].fields.map(field => {
      const value = record?.[field.key] ?? "";
      const isAvatar = field.type === "avatar";
      const label = isAvatar
        ? `<span class="field-label">${escape(field.label)}${field.required ? " *" : ""}</span>`
        : `<label for="field-${field.key}">${escape(field.label)}${field.required ? " *" : ""}</label>`;
      const attrs = `${field.required ? "required" : ""} ${field.min ? `min="${field.min}"` : ""} ${field.max ? `max="${field.max}"` : ""} ${field.step ? `step="${field.step}"` : ""}`;
      let input;
      if (isAvatar) {
        // Tile picker: one radio always checked (current art, else "None"),
        // so an edit without touching it re-submits the same value.
        const raw = String(value ?? "");
        const current = AVATAR_FILES.includes(raw) ? raw : "";
        const tiles = [{ file: "", label: "No art" }, ...AVATAR_FILES.map(file => ({ file, label: avatarLabel(file) }))];
        input = `<div class="avatar-picker" role="radiogroup" aria-label="${escape(field.label)}">${tiles.map(tile => {
          const visual = tile.file
            ? `<img src="/assets/players/${tile.file}" alt="" loading="lazy" decoding="async">`
            : `<span class="avatar-tile-none" aria-hidden="true">✕</span>`;
          return `<label class="avatar-tile"><input type="radio" name="${field.key}" value="${escape(tile.file)}" ${tile.file === current ? "checked" : ""}>${visual}<span class="avatar-tile-label">${escape(tile.label)}</span></label>`;
        }).join("")}</div>`;
      }
      else if (field.type === "select") input = `<select id="field-${field.key}" name="${field.key}" ${attrs}>${buildOptions(field, value)}</select>`;
      else if (field.type === "textarea") input = `<textarea id="field-${field.key}" name="${field.key}" maxlength="240" ${attrs}>${escape(value)}</textarea>`;
      else input = `<input id="field-${field.key}" name="${field.key}" type="${field.type || "text"}" value="${escape(value)}" placeholder="${escape(field.placeholder || "")}" maxlength="240" ${attrs}>`;
      return `<div class="field ${field.wide ? "field-wide" : ""}">${label}${input}</div>`;
    }).join("");
    dialog.showModal();
    $("#form-fields input, #form-fields select, #form-fields textarea")?.focus();
  }
  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (event.submitter?.value === "cancel") return dialog.close();
    if (!editing || !form.reportValidity()) return;
    const save = $("#save-record"), error = $("#dialog-error");
    save.disabled = true; save.textContent = "Saving…"; error.textContent = "";
    const values = Object.fromEntries(new FormData(form).entries());
    for (const key of ["team_id", "tournament_id"]) if (!values[key]) values[key] = null;
    for (const key of ["prize_pool", "amount"]) if (key in values) values[key] = Number(values[key]);
    try { await api.request(`/api/entities/${editing.entity}${editing.id ? `/${editing.id}` : ""}`, { method: editing.id ? "PUT" : "POST", body: values }); dialog.close(); await renderPage(editing.entity); }
    catch (err) { error.textContent = err.message; }
    finally { save.disabled = false; save.textContent = "Save changes"; }
  });
  function renderAssistant() {
    const financeSuggestion = permissions["financial.view"] ? `<button class="chat-suggest" data-prompt="Show me all expenses">All expenses</button>` : "";
    const activitySuggestion = ["admin", "manager"].includes(currentUser.role) ? `<button class="chat-suggest" data-prompt="Show me recent activity">Recent activity</button>` : "";
    const botMark = `<span class="bot-mark">${svgIcon("sparkles")}</span>`;
    content.innerHTML = `${heading("Raptor AI Assistant", "Ask about data available to your role.")}<section class="assistant-panel"><div class="assistant-intro">${botMark}<div><h2>Workspace assistant</h2><p>Role-aware workspace companion · live AI with local fallback</p></div></div><div class="chat-scroll" id="chat-scroll" aria-live="polite"><div class="chat-row">${botMark}<div class="chat-bubble">Hi ${escape(currentUser.name)}! I can answer questions about your authorized teams, matches, and performance data.</div></div><div class="chat-suggestions"><button class="chat-suggest" data-prompt="Show me our upcoming matches">Upcoming matches</button>${activitySuggestion}${financeSuggestion}</div></div><form id="chat-form" class="chat-form"><label class="sr-only" for="chat-question">Ask the assistant a question</label><input id="chat-question" maxlength="500" placeholder="Type your question…" autocomplete="off" enterkeyhint="send" required><button aria-label="Send question">${svgIcon("send")}</button></form></section>`;
    const chat = $("#chat-scroll");
    const addMessage = (text, role) => { const row = document.createElement("div"); row.className = `chat-row ${role}`; if (role !== "user") row.innerHTML = botMark; const bubble = document.createElement("div"); bubble.className = "chat-bubble"; bubble.textContent = text; row.append(bubble); chat.append(row); row.scrollIntoView({ block: "nearest", behavior: "smooth" }); };
    const ask = async question => { chat.querySelector(".chat-suggestions")?.remove(); addMessage(question, "user"); try { const data = await api.request("/api/assistant", { method: "POST", body: { question } }); addMessage(data.answer, "assistant"); } catch (error) { addMessage(error.message, "assistant"); } };
    chat.querySelectorAll("[data-prompt]").forEach(button => button.addEventListener("click", () => ask(button.dataset.prompt)));
    $("#chat-form").addEventListener("submit", event => { event.preventDefault(); const input = $("#chat-question"), question = input.value.trim(); if (!question) return; input.value = ""; ask(question); });
  }
  function renderSettings() {
    content.innerHTML = `${heading("Settings", "Local organization workspace preferences.")}<section class="content-card settings-card"><div class="card-heading"><h2>Organization</h2></div><div class="settings-row"><span>Workspace name<small>Raptor Esports</small></span><span class="status-chip status-active">Active</span></div><div class="settings-row"><span>Database<small>SQLite · local data/raptor.sqlite3</small></span><span class="status-chip status-active">Local</span></div><div class="settings-row"><span>Public home page<small>Raptor Esports landing page</small></span><a class="text-link" href="/">Open ${svgIcon("arrow-up-right")}</a></div><div class="settings-row"><span>Assistant<small>OpenAI-compatible · local fallback</small></span><span class="status-chip status-active">Ready</span></div></section>`;
  }
  async function renderUsers() {
    const [usersResponse, teamsResponse, playerResponse] = await Promise.all([api.request("/api/users"), api.request("/api/entities/teams"), api.request("/api/entities/players")]);
    const accounts = usersResponse.items, teamList = teamsResponse.items, playerList = playerResponse.items;
    window.currentPlayers = playerList;
    const roleNames = ["admin", "manager", "coach", "analyst", "player"];
    const linkedAccounts = new Map(accounts.filter(user => user.player_id).map(user => [Number(user.player_id), user]));
    const accountRows = accounts.map(user => {
      const editable = user.email !== currentUser.email;
      const roleCell = editable
        ? `<select class="table-select user-account-role" data-user-role="${user.id}" aria-label="Account role for ${escape(user.name)}">${roleNames.map(role => `<option value="${role}" ${role === user.role ? "selected" : ""}>${role}</option>`).join("")}</select>`
        : `<span class="status-chip">${escape(user.role)} · you</span>`;
      let teamCell;
      if (user.role === "coach" || user.role === "analyst") {
        const assigned = new Set((user.teams || []).map(team => Number(team.id)));
        teamCell = `<div class="team-checklist" data-user-teams="${user.id}" aria-label="Team access for ${escape(user.name)}">${teamList.map(team => `<label><input type="checkbox" value="${team.id}" ${assigned.has(Number(team.id)) ? "checked" : ""}> <span>${escape(team.name)}</span></label>`).join("") || '<span class="muted">No teams available</span>'}</div>`;
      } else if (user.role === "player") {
        teamCell = user.player ? `<span>${escape(user.player.team_name || "No team")}</span><small class="table-note">From linked player</small>` : '<span class="muted">No player linked</span>';
      } else {
        teamCell = '<span class="muted">Organization-wide</span>';
      }
      const linkedLine = user.player ? `Linked: ${user.player.name} · ${user.player.ign} · ${user.player.role || "—"} · ${user.player.game || "—"}` : "No linked player";
      const actions = editable ? `<div class="row-actions"><button class="button button-light button-small" data-save-user="${user.id}" aria-label="Save account for ${escape(user.name)}">Save</button><button class="row-action delete" data-delete-user="${user.id}" aria-label="Delete ${escape(user.email)}">${svgIcon("trash")}</button></div>` : '<span class="muted">Current session</span>';
      return `<tr><td><span class="table-primary">${escape(user.name)}</span><small class="table-note">${escape(user.email)}</small><small class="table-note">${escape(linkedLine)}</small><small class="table-note">Created ${timestampLabel(user.created_at)}</small></td><td>${roleCell}</td><td>${teamCell}</td><td>${actions}</td></tr>`;
    }).join("");
    const playerRows = playerList.map(player => {
      const account = linkedAccounts.get(Number(player.id));
      const teamOptions = [`<option value="" ${player.team_id == null ? "selected" : ""}>No team</option>`, ...teamList.map(team => `<option value="${team.id}" ${String(player.team_id) === String(team.id) ? "selected" : ""}>${escape(team.name)}</option>`)].join("");
      const statusOptions = ["Active", "Inactive", "Trial"].map(status => `<option value="${status}" ${status === player.status ? "selected" : ""}>${status}</option>`).join("");
      const loginLine = account ? `Login: ${account.email} · ${account.role}` : "No login account";
      return `<tr><td><div class="admin-user-player">${playerAvatar(player)}<div><span class="table-primary">${escape(player.name)}</span><small class="table-note">IGN ${escape(player.ign)} · ${escape(player.game || "—")}</small><small class="table-note">${escape(loginLine)}</small></div></div></td><td><input class="table-input user-role-input" data-player-role="${player.id}" value="${escape(player.role)}" maxlength="60" aria-label="In-game role for ${escape(player.name)}"></td><td><select class="table-select user-team-select" data-player-team="${player.id}" aria-label="Team for ${escape(player.name)}">${teamOptions}</select></td><td><select class="table-select user-status-select" data-player-status="${player.id}" aria-label="Status for ${escape(player.name)}">${statusOptions}</select></td><td><button class="button button-light button-small" data-save-player="${player.id}" aria-label="Save player ${escape(player.name)}">Save</button></td></tr>`;
    }).join("");
    const accountTable = accounts.length ? `<div class="table-wrap"><table class="user-table"><thead><tr><th><span>Account</span></th><th><span>Account role</span></th><th><span>Team access</span></th><th><span>Actions</span></th></tr></thead><tbody>${accountRows}</tbody></table></div>` : '<div class="empty-state">No login accounts yet.</div>';
    const playerTable = playerList.length ? `<div class="table-wrap"><table class="user-table"><thead><tr><th><span>Player</span></th><th><span>In-game role</span></th><th><span>Team</span></th><th><span>Status</span></th><th><span>Actions</span></th></tr></thead><tbody>${playerRows}</tbody></table></div>` : '<div class="empty-state">No player records yet.</div>';
    content.innerHTML = `${heading("User Management", "Manage login accounts, account roles, team access, and the full player roster.")}<div class="user-stack"><section class="content-card data-card"><div class="data-toolbar"><h2>Accounts <span class="muted">(${accounts.length})</span></h2><span class="muted">Role and team access</span></div>${accountTable}</section><section class="content-card data-card"><div class="data-toolbar"><h2>Players <span class="muted">(${playerList.length})</span></h2><span class="muted">In-game role, team, and status</span></div>${playerTable}</section><section class="content-card user-create-card"><div class="card-heading"><h2>Create account</h2><span class="muted">Adds a login account only</span></div><form id="user-create-form" class="form-fields" autocomplete="off"><div class="field"><label>Name</label><input name="name" maxlength="100" autocomplete="off" required></div><div class="field"><label>Email</label><input name="email" type="email" maxlength="200" autocomplete="off" required></div><div class="field"><label>Role</label><select name="role">${roleNames.map(role => `<option>${role}</option>`).join("")}</select></div><div class="field"><label>Temporary password</label><input name="password" type="password" minlength="8" autocomplete="new-password" required></div><div class="field"><label>Link player record (players only)</label><select name="player_id"><option value="">None</option>${playerList.map(player => `<option value="${player.id}">${escape(player.name)} · ${escape(player.ign)}</option>`).join("")}</select></div><div class="field"><label>Initial team access (coach/analyst)</label><select name="team_id"><option value="">None</option>${teamList.map(team => `<option value="${team.id}">${escape(team.name)}</option>`).join("")}</select></div><div class="field field-wide"><button class="button button-purple">${svgIcon("plus")} Create account</button><p id="user-form-error" class="form-message" role="alert"></p></div></form></section></div>`;
    const createForm = $("#user-create-form");
    createForm.addEventListener("submit", async event => { event.preventDefault(); const values = Object.fromEntries(new FormData(createForm)); for (const field of ["player_id", "team_id"]) values[field] = values[field] ? Number(values[field]) : null; try { await api.request("/api/users", { method: "POST", body: values }); await renderUsers(); } catch (error) { $("#user-form-error").textContent = error.message; } });
    content.querySelectorAll("[data-save-user]").forEach(button => button.addEventListener("click", async () => {
      const id = Number(button.dataset.saveUser);
      const role = $(`[data-user-role="${id}"]`)?.value || accounts.find(user => user.id === id)?.role;
      const teamIds = role === "coach" || role === "analyst" ? Array.from(content.querySelectorAll(`[data-user-teams="${id}"] input:checked`)).map(input => Number(input.value)) : [];
      button.disabled = true;
      try { await api.request(`/api/users/${id}`, { method: "PUT", body: { role, team_ids: teamIds } }); await renderUsers(); }
      catch (error) { window.alert(error.message); button.disabled = false; }
    }));
    content.querySelectorAll("[data-save-player]").forEach(button => button.addEventListener("click", async () => {
      const id = Number(button.dataset.savePlayer);
      const player = playerList.find(item => item.id === id);
      const role = $(`[data-player-role="${id}"]`)?.value.trim();
      const teamValue = $(`[data-player-team="${id}"]`)?.value;
      const status = $(`[data-player-status="${id}"]`)?.value;
      if (!role) { window.alert("Enter the player's in-game role."); return; }
      button.disabled = true;
      try { await api.request(`/api/entities/players/${id}`, { method: "PUT", body: { name: player.name, ign: player.ign, game: player.game, role, team_id: teamValue ? Number(teamValue) : null, status } }); await renderUsers(); }
      catch (error) { window.alert(error.message); button.disabled = false; }
    }));
    content.querySelectorAll("[data-delete-user]").forEach(button => button.addEventListener("click", async () => { if (!confirm("Delete this account?")) return; try { await api.request(`/api/users/${button.dataset.deleteUser}`, { method: "DELETE" }); await renderUsers(); } catch (error) { window.alert(error.message); } }));
  }
  async function renderAssignments() {
    const [assignmentResponse, staffResponse, teamResponse] = await Promise.all([api.request("/api/assignments"), api.request("/api/coaches"), api.request("/api/entities/teams")]);
    const assignments = assignmentResponse.items;
    content.innerHTML = `${heading("Coach Assignments", "Grant coaches and analysts access only to the teams they support.")}<div class="user-stack"><section class="content-card"><div class="card-heading"><h2>Grant team access</h2><span class="muted">Coach and analyst access</span></div><form id="assignment-form" class="form-fields"><div class="field"><label>Coach or analyst</label><select name="user_id" required>${staffResponse.items.map(user => `<option value="${user.id}">${escape(user.name)} · ${escape(user.role)}</option>`).join("")}</select></div><div class="field"><label>Team</label><select name="team_id" required>${teamResponse.items.map(team => `<option value="${team.id}">${escape(team.name)}</option>`).join("")}</select></div><div class="field field-wide"><button class="button button-purple">${svgIcon("user-check")} Assign team</button><p id="assignment-error" class="form-message" role="alert"></p></div></form></section><section class="content-card data-card"><div class="data-toolbar"><h2>Current assignments <span class="muted">(${assignments.length})</span></h2><span class="muted">Access map</span></div>${assignments.length ? `<div class="table-wrap"><table><thead><tr><th><span>Staff member</span></th><th><span>Role</span></th><th><span>Team</span></th><th><span>Action</span></th></tr></thead><tbody>${assignments.map(row => `<tr><td><span class="table-primary">${escape(row.user_name)}</span><small class="table-note">${escape(row.email)}</small></td><td>${escape(row.role)}</td><td>${escape(row.team_name)}</td><td><button class="row-action delete" data-remove-assignment="${row.user_id}/${row.team_id}" aria-label="Remove team assignment">${svgIcon("trash")}</button></td></tr>`).join("")}</tbody></table></div>` : `<div class="empty-state">No team assignments yet.</div>`}</section></div>`;
    $("#assignment-form").addEventListener("submit", async event => { event.preventDefault(); const values = Object.fromEntries(new FormData(event.currentTarget)); values.user_id = Number(values.user_id); values.team_id = Number(values.team_id); try { await api.request("/api/assignments", { method: "POST", body: values }); await renderAssignments(); } catch (error) { $("#assignment-error").textContent = error.message; } });
    content.querySelectorAll("[data-remove-assignment]").forEach(button => button.addEventListener("click", async () => { try { await api.request(`/api/assignments/${button.dataset.removeAssignment}`, { method: "DELETE" }); await renderAssignments(); } catch (error) { window.alert(error.message); } }));
  }
  const sidebar = $("#sidebar"), sidebarToggle = $("#sidebar-toggle"), sidebarBackdrop = $("#sidebar-backdrop");
  const setSidebar = open => { sidebar.classList.toggle("sidebar-open", open); sidebarToggle.setAttribute("aria-expanded", String(open)); sidebarBackdrop.classList.toggle("is-visible", open); document.body.classList.toggle("sidebar-is-open", open); if (open) document.querySelector(".raptor-chat.is-open [data-close]")?.click(); };
  document.querySelectorAll(".side-link").forEach(link => link.addEventListener("click", event => { event.preventDefault(); history.replaceState(null, "", link.getAttribute("href")); renderPage(link.dataset.page); setSidebar(false); }));
  sidebarToggle.addEventListener("click", () => setSidebar(!sidebar.classList.contains("sidebar-open")));
  sidebarBackdrop.addEventListener("click", () => setSidebar(false));
  window.addEventListener("resize", () => { if (window.innerWidth > 860) setSidebar(false); });
  $("#logout-button").addEventListener("click", async () => { try { await api.logout(); } finally { location.replace("/login"); } });
  document.addEventListener("keydown", event => { if (event.key === "Escape") setSidebar(false); });
  window.addEventListener("hashchange", () => { const page = location.hash.slice(1) || "dashboard"; if (page !== currentPage) renderPage(page); });
  start();
})();
