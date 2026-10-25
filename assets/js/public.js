(() => {
  const api = window.RaptorAPI;
  const safe = value => String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const money = value => "₹" + Number(value || 0).toLocaleString("en-IN");
  const teamEmblem = (team, index) => {
    const name = String(team.name || "").toLowerCase();
    const designs = [
      ["raptor","#a879ff",'<path d="M10 32 27 7l-3 15 15-9-8 16 16-4-19 14-2 12-7-11-13 7 8-15z"/>'],
      ["phoenix","#ff9d45",'<path d="M28 5c4 12-5 12 7 20 7 6 3 15-4 19 1-8-5-9-6-15-3 7-11 9-7 17-13-9-8-23 2-29 0 6 3 8 4 10 4-9 7-13 4-22z"/>'],
      ["shadow","#a58bff",'<path d="m7 18 19-12-3 13 16-9-7 16 15-8-10 22-10 10-9-10z"/><path d="m18 29 9 3 10-5-9 12-9-4z" fill="#171126"/>'],
      ["vortex","#63d4ff",'<path d="M27 5a22 22 0 1 0 22 22 18 18 0 1 1-22-22zm1 11a11 11 0 1 0 11 11 8 8 0 1 1-11-11z"/>'],
      ["falcon","#e8c36b",'<path d="m5 18 20 5L16 8l19 11 14-5-12 14 6 18-16-10-12 9 4-16z"/>'],
      ["nova","#ff71d2",'<path d="m28 3 5 17 17-8-9 16 15 8-18 1-4 17-8-15-16 9 8-17-15-7 18-2z"/>'],
      ["titan","#7be0b2",'<path d="m28 4 21 9-4 21-17 18-17-18-4-21z"/><path d="m17 22 7-7 5 5 6-5 6 7-4 13-7 5-9-5z" fill="#14271f"/>'],
      ["eclipse","#f7d77b",'<circle cx="28" cy="28" r="21"/><circle cx="37" cy="20" r="18" fill="#20172c"/>'],
      ["reaper","#ff738a",'<path d="M30 6c-12 0-20 9-20 20 0 9 6 16 15 19l-2 7 9-5c9-5 15-12 15-22S39 6 30 6z"/><path d="m18 27 9 3-7 7zm21 0-9 3 7 7z" fill="#24131d"/>'],
      ["storm","#70a9ff",'<path d="m33 4-22 29h15l-3 20 23-31H31z"/>'],
      ["apex","#ff9b73",'<path d="m4 48 14-26 9 13 9-25 17 38z"/><path d="m23 35 8-14 10 21H15z" fill="#261720"/>'],
      ["hydra","#76e0d0",'<path d="M10 44c-5-9-2-20 7-24-2-9 6-15 13-10 8-5 16 1 14 10 9 4 12 15 6 24l-9-4H19z"/><circle cx="18" cy="24" r="2" fill="#132824"/><circle cx="29" cy="15" r="2" fill="#132824"/><circle cx="40" cy="24" r="2" fill="#132824"/>']
    ];
    const mark = designs.find(([key]) => name.includes(key)) || designs[index % designs.length];
    const suppliedLogo = ["raptor", "phoenix", "shadow", "vitality", "apex"].find(key => name.includes(key));
    if (suppliedLogo) return `<img class="team-logo team-logo-raster${suppliedLogo === "apex" ? " team-logo-raster-wide" : ""}" src="/assets/team-logos/${suppliedLogo}${suppliedLogo === "apex" ? ".jpg" : ".png"}" alt="${safe(team.name)} logo">`;
    return `<svg class="team-logo" viewBox="0 0 56 56" role="img" aria-label="${safe(team.name)} logo" style="--team-logo-color:${mark[1]}">${mark[2]}</svg>`;
  };
  fetch("/api/public").then(r => r.json()).then(data => {
    for (const key of ["teams", "players", "tournaments"]) { const el = document.querySelector(`[data-stat="${key}"]`); if (el) el.textContent = key === "teams" && data.stats[key] < 10 ? `0${data.stats[key]}` : data.stats[key]; }
    const teams = document.querySelector("#public-teams"); /* null once the landing page's old roster grid is gone */
    if (teams) teams.innerHTML = data.teams.map((team, i) => `<a class="team-card" href="/teams/${safe(team.id)}" aria-label="View ${safe(team.name)} team details"><div class="team-symbol ${safe(team.accent)}${String(team.name || "").toLowerCase().includes("apex") ? " team-symbol-tag" : ""}">${teamEmblem(team, i)}</div><div class="team-card-main"><span class="eyebrow">${safe(team.game)}</span><h3>${safe(team.name)}</h3><p>${safe(team.description || "Ready for the next challenge.")}</p><div class="team-card-foot"><span>${team.players_count || 0} Players</span></div></div></a>`).join("") || `<div class="empty-public">Our next roster is in the making. Check back soon.</div>`;
    const tournaments = document.querySelector("#public-tournaments");
    if (tournaments) tournaments.innerHTML = data.tournaments.map(t => {
      const date = new Date(t.date + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short" });
      const key = String(t.game || "").toLowerCase().replace(/[^a-z0-9]/g, "");
      const live = String(t.status || "").toLowerCase() === "ongoing";
      const where = String(t.location || "").trim();
      const meta = [live ? "Ongoing" : String(t.status || "Upcoming").trim(), where].filter(Boolean).join(" · ");
      return `<article class="tournament-mini tournament-mini--${key}">
        <figure class="tournament-figure">${live ? '<span class="tourney-live"><i></i>LIVE</span>' : ""}<span class="tourney-date">${safe(date)}</span></figure>
        <div class="tournament-body">
          <div class="tournament-content">
            <span class="tourney-game">${safe(t.game)}</span>
            <h3 class="tourney-name">${safe(t.name)}</h3>
            <p class="tourney-desc">${safe(meta)}</p>
          </div>
          <footer class="tournament-footer">
            <div class="tournament-detail"><span class="detail-label">Prize</span><p class="tourney-prize">${money(t.prize_pool)}</p></div>
            <div class="tournament-detail"><span class="detail-label">Date</span><p>${safe(date)}</p></div>
            <div class="tournament-detail"><span class="detail-label">Game</span><p>${safe(t.game)}</p></div>
          </footer>
        </div>
      </article>`;
    }).join("") || "<span>No tournaments announced yet.</span>";
  }).catch(() => { document.querySelectorAll("[data-stat]").forEach(el => el.textContent = "0"); const teams = document.querySelector("#public-teams"); if (teams) teams.innerHTML = `<div class="empty-public">Our team lineup will be here soon.</div>`; });
  const toggle = document.querySelector(".menu-toggle"), nav = document.querySelector("#public-nav");
  toggle?.addEventListener("click", () => { const open = toggle.getAttribute("aria-expanded") === "true"; toggle.setAttribute("aria-expanded", String(!open)); nav.classList.toggle("nav-open", !open); });
  nav?.querySelectorAll("a").forEach(a => a.addEventListener("click", () => { toggle.setAttribute("aria-expanded", "false"); nav.classList.remove("nav-open"); }));
})();
