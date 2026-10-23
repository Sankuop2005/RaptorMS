(() => {
  const safe = value => String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const icons = {
    raptor: "/assets/team-logos/raptor.png",
    phoenix: "/assets/team-logos/phoenix.png",
    shadow: "/assets/team-logos/shadow.png",
    vitality: "/assets/team-logos/vitality.png",
    apex: "/assets/team-logos/apex.png"
  };
  const nameKey = name => String(name || "").toLowerCase();
  const initials = name => String(name || "Team").split(/\s+/).slice(0, 2).map(part => part[0] || "").join("").toUpperCase();
  const playerEmblem = (player, index) => {
    const key = nameKey(player.ign || player.name).replace(/[^a-z0-9]/g, "");
    const emblems = [
      ['sanku', '<path d="M8 18 24 7l-4 11 13-7-7 13 12-4-17 16-2-10-9 5 5-11z"/><path d="m17 29 8 3 8-5-8 10z" class="emblem-cut"/>'],
      ['shisui', '<path d="M4 24s8-12 20-12 20 12 20 12-8 12-20 12S4 24 4 24Z"/><circle cx="24" cy="24" r="8" class="emblem-core"/><circle cx="24" cy="24" r="3" class="emblem-cut"/><path d="M24 7v5m0 24v5M7 24h5m24 0h5" class="emblem-line"/>'],
      ['naruto', '<path d="M24 5 42 14v14c0 11-8 17-18 21C14 45 6 39 6 28V14z"/><path d="M24 13c-7 0-12 5-12 11 0 5 4 8 8 8 3 0 5-2 5-4s-2-4-4-3m3-12 4 8 9-2-6 7 5 7-9-3-5 8" class="emblem-cut"/><path d="M11 21 4 18m8 10-8 1m12 8-6 5" class="emblem-line"/>'],
      ['dazzler', '<path d="m24 3 5 14 14-7-7 14 14 5-14 5 7 14-14-7-5 14-5-14-14 7 7-14-14-5 14-5-7-14 14 7z"/><path d="m24 17 3 5 6 2-6 3-3 6-3-6-6-3 6-2z" class="emblem-cut"/>'],
      ['zero', '<path d="M24 4 43 15v18L24 44 5 33V15z"/><path d="M30 14c-8-4-17 2-17 10 0 7 5 12 12 12 4 0 7-2 9-5M20 19l12 11m-12 0 12-11" class="emblem-cut emblem-line"/><circle cx="24" cy="24" r="3" class="emblem-core"/>']
    ];
    const match = emblems.find(([name]) => key.includes(name));
    const selected = match || emblems[index % emblems.length];
    const cssKey = match ? match[0] : `alt-${index % emblems.length}`;
    return '<span class="player-avatar" role="img" aria-label="' + safe((player.ign || player.name) + ' emblem') + '"><svg class="player-emblem player-emblem-' + cssKey + '" viewBox="0 0 48 48" aria-hidden="true">' + selected[1] + '</svg></span>';
  };
  const id = window.location.pathname.match(/^\/teams\/(\d+)$/)?.[1];
  const profile = document.querySelector("#team-profile");
  const roster = document.querySelector("#team-roster");
  const count = document.querySelector("#roster-count");

  fetch("/api/public/teams/" + encodeURIComponent(id || ""))
    .then(response => { if (!response.ok) throw new Error("This team could not be found."); return response.json(); })
    .then(({ team, players }) => {
      const key = nameKey(team.name);
      const image = Object.entries(icons).find(([name]) => key.includes(name))?.[1];
      const imageClass = key.includes("apex") ? " team-detail-logo-wide" : "";
      const emblem = image ? '<img class="' + imageClass.trim() + '" src="' + image + '" alt="' + safe(team.name) + ' logo">' : '<span class="team-logo-fallback">' + safe(initials(team.name)) + '</span>';
      const statusClass = team.status === "Active" ? " is-active" : "";
      profile.innerHTML = '<div class="team-profile-logo">' + emblem + '</div><div class="team-profile-copy"><span class="eyebrow">' + safe(team.game) + ' · RAPTOR ESPORTS</span><h1>' + safe(team.name) + '</h1><p>' + safe(team.description || "Ready for the next challenge.") + '</p><div class="team-profile-meta"><span class="team-detail-chip' + statusClass + '">' + safe(team.status) + '</span><span class="team-detail-chip">' + players.length + (players.length === 1 ? " Player" : " Players") + '</span><span class="team-detail-chip">' + safe(team.game) + '</span></div></div>';
      document.title = team.name + " — Raptor Esports";
      count.textContent = players.length + (players.length === 1 ? " player" : " players");
      roster.innerHTML = players.map((player, index) => '<article class="roster-player">' + playerEmblem(player, index) + '<div class="roster-player-copy"><h3>' + safe(player.name) + '</h3><p>' + safe(player.ign || "Player") + ' · ' + safe(player.role || "Roster") + '</p></div><span class="roster-player-status">' + safe(player.status || "Active") + '</span></article>').join("") || '<div class="roster-empty">No players have been added to this roster yet.</div>';
    })
    .catch(error => {
      profile.innerHTML = '<div class="team-detail-error">' + safe(error.message) + ' <a class="text-link" href="/#teams">Back to all teams</a></div>';
      document.querySelector(".team-roster-section").hidden = true;
    });
})();
