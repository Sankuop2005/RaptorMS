/* Raptor scroll-scrubbed roster
   ------------------------------------------------------------------
   A pinned section under the hero: scroll progress drives
   video.currentTime of the Poseidon X-Suit transformation clip
   from 0 -> ~10s, forward and backward, and freezes on whatever
   frame the visitor stops at.

   Design notes
   - vanilla rAF scrubber (site CSP is script-src 'self', no CDN);
     raw scroll is smoothed into a gliding value, and the video seeks
     only when the target has moved past ~half a source frame
   - team details share the site's own data: identities come from
     GET /api/public (left stack: logo, game, name, tagline, count)
     and each team's player list from the public
     GET /api/public/teams/{id} — the right side is players-only,
     full-art cards fed by each player's artwork avatar from the DB,
     IGN in a red stencil face, role as a small chip
   - the two stacks crossfade on the video's actual morph beats —
     the cyan energy morph lands ~3.5s and the magenta ring burst
     ~6.6s (found by frame-stepping the rendered clip). Team 1 is on
     from the start, so the stage opens as THE ROSTER with the first
     squad's lineup already showing
   - seekability: the dev server answers byte-range requests; if the
     clip's seekable span ever reads broken (a host without range
     support), it is refetched as a Blob and played from an object
     URL — blobs are always fully seekable
   - iOS: a muted, never-played video will not paint seeked frames,
     so the element is primed (play -> pause) on the first user
     interaction and the poster stays up until a frame is painted
   - phones get the 720p -m.mp4 variant (small GOP = cheap seeks);
     a swap only happens while the stage is idle, so scrubbing is
     never reset mid-experience
   - prefers-reduced-motion: no pinning, no scrubbing, no video —
     CSS lays the three team panels out as a static column instead
   ------------------------------------------------------------------ */
(() => {
  const section = document.getElementById("roster-scrub");
  const pin = section && section.querySelector(".rs-pin");
  const video = section && section.querySelector(".rs-video");
  if (!section || !pin || !video) return;

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  const ids = Array.from(section.querySelectorAll(".rs-id")); /* left: team identity stack */
  const panels = Array.from(section.querySelectorAll(".rs-panel")); /* right: player-card stacks */
  const dots = Array.from(section.querySelectorAll(".rs-dot"));
  const railFill = section.querySelector(".rs-rail-fill");
  const heading = section.querySelector(".rs-heading");
  const cueEl = section.querySelector(".rs-cue");

  const CLIPS = {
    desktop: "/assets/video/poseidon-scrub.mp4",
    mobile: "/assets/video/poseidon-scrub-m.mp4",
  };
  const ACCENTS = ["#792ACF", "#AE48ED", "#EB84F9"];
  const FORM_BREAKS = [3.35, 6.15];

  /* reveal bands in video seconds — crossfades ride the real morphs:
     team 1 holds from the very start (the stage opens as the roster),
     team 2 lands with the cyan form, team 3 after the magenta ring
     burst; the CTA rides the final hold */
  const BANDS = [
    { in: [-0.35, -0.01], out: [3.15, 3.7] },
    { in: [3.5, 3.95],    out: [5.55, 6.1] },
    { in: [6.0, 6.5],     out: [1e9, 1e10] },
  ];
  const CTA_BAND = { in: [9.15, 9.6], out: [1e9, 1e10] };

  const clamp01 = v => v < 0 ? 0 : v > 1 ? 1 : v;
  const ramp = (v, a, b) => v <= a ? 0 : v >= b ? 1 : (v - a) / (b - a);
  const bandOpacity = (t, b) => ramp(t, b.in[0], b.in[1]) * (1 - ramp(t, b.out[0], b.out[1]));
  const esc = value => String(value).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  const state = { p: 0, smooth: 0 };

  /* boot state: the stage opens as the roster — the heading, team 1's
     identity block and team 1's player cards are live at rest; teams
     2/3 stay hidden until their bands arrive */
  section.classList.add("rs-open");
  ids.forEach((id, i) => {
    id.style.opacity = i === 0 ? "1" : "0";
    id.style.visibility = i === 0 ? "visible" : "hidden";
    id.style.transform = i === 0 ? "translateY(0)" : "translateY(18px)";
  });
  panels.forEach((panel, i) => {
    panel.style.opacity = i === 0 ? "1" : "0";
    panel.style.visibility = i === 0 ? "visible" : "hidden";
    panel.style.transform = i === 0 ? "translateX(0)" : "translateX(26px)";
    panel.classList.toggle("rs-on", i === 0);
  });

  /* ---------- roster data (existing sources, unchanged) ---------- */
  const rasterLogo = name => {
    const low = String(name || "").toLowerCase();
    const key = ["raptor", "phoenix", "shadow", "vitality", "apex"].find(k => low.includes(k));
    if (!key) return "/assets/raptor-eagle-mark.png";
    return `/assets/team-logos/${key}.${key === "apex" ? "jpg" : "png"}`; /* the apex mark is tracked as a jpg */
  };
  const initials = name => String(name || "?").trim().split(/\s+/).slice(0, 2).map(w => (w[0] || "").toUpperCase()).join("") || "?";
  /* right side: player cards — the DB's artwork avatar fills the card,
     the scrim carries the red stencil IGN; role rides as a small chip;
     when a player has no avatar yet an initials chip stands in */
  const renderCards = (wrap, players) => {
    if (!wrap || !players) return;
    wrap.innerHTML = players.slice(0, 5).map((p, i) => {
      const ign = String(p.ign || p.name || "Player").trim();
      const art = p.avatar ? `<img src="/assets/players/${encodeURIComponent(String(p.avatar))}" alt="">` : "";
      const chip = p.avatar ? "" : `<i class="rs-pav" aria-hidden="true">${esc(initials(ign))}</i>`;
      return `<figure class="rs-pcard" style="--ri:${i}">${art}<i class="rs-pscrim" aria-hidden="true"></i>${chip}<b class="rs-pname">${esc(ign)}</b><span class="rs-prole">${esc(String(p.role || "Roster").trim())}</span></figure>`;
    }).join("");
  };
  const loadPlayers = (panel, team) => {
    if (!panel || !team) return;
    fetch(`/api/public/teams/${encodeURIComponent(team.id)}`).then(r => r.json()).then(d => renderCards(panel.querySelector(".rs-players"), d.players || [])).catch(() => {});
  };
  const populate = (id, team, i) => {
    if (!id || !team) return;
    id.classList.remove("rs-empty");
    id.querySelector(".rs-team-logo").src = rasterLogo(team.name);
    id.querySelector(".rs-team-game").textContent = (team.game || "").trim() || "Squad";
    id.querySelector(".rs-team-name").textContent = String(team.name || "").trim() || "Locked in";
    id.querySelector(".rs-team-line").textContent = (team.description || "").trim() || "Ready for the next challenge.";
    id.querySelector(".rs-team-foot strong").textContent = team.players_count ?? 0;
    id.style.setProperty("--rs-kc", ACCENTS[i % ACCENTS.length]);
    if (dots[i]) dots[i].style.setProperty("--rs-kc", ACCENTS[i % ACCENTS.length]);
    loadPlayers(panels[i], team);
  };
  fetch("/api/public").then(r => r.json()).then(data => {
    const teams = data.teams || [];
    const games = ["bgmi", "free fire", "valorant"];
    ids.forEach((id, i) => {
      const targetGame = games[i] || "";
      const team = teams.find(t => String(t.game || "").trim().toLowerCase() === targetGame) || teams[i];
      if (team) populate(id, team, i);
    });
  }).catch(() => { /* server hiccup: placeholders stay; the page still works */ });

  /* ---------- clip plumbing ---------- */
  let duration = 10, durReady = false, lastT = -1;
  let primed = false, blobTried = false, useBlob = false;
  let currentClip = (video.currentSrc || video.src || "").includes("-m.mp4") ? "mobile" : "desktop";
  let blobUrl = "";

  const markLive = () => video.classList.add("rs-live");
  if (video.readyState >= 2) markLive();

  video.addEventListener("loadeddata", () => {
    duration = Number.isFinite(video.duration) && video.duration > 0 ? video.duration : 10;
    durReady = true;
    if (!useBlob) ensureSeekable();
    if (lastT > 0.05 && Math.abs(video.currentTime - lastT) > 0.05) {
      try { video.currentTime = lastT; } catch (_) { /* retry next tick */ }
    }
    markLive();
  });

  /* fallback: serve the clip as a blob when range requests fail so
     seeks stay possible no matter where this gets hosted someday */
  const toBlobSource = () => {
    if (blobTried || !video.currentSrc && !video.src) return;
    blobTried = true;
    const wanted = lastT > 0 ? lastT : 0;
    fetch(video.currentSrc || video.src).then(r => {
      if (!r.ok) throw Error("clip unreachable");
      return r.blob();
    }).then(blob => {
      useBlob = true;
      blobUrl = URL.createObjectURL(blob);
      video.src = blobUrl;
      video.load();
      video.addEventListener("loadeddata", () => {
        try { if (wanted > 0.05) video.currentTime = wanted; } catch (_) {}
      }, { once: true });
    }).catch(() => { /* leave the poster/scrub as-is */ });
  };
  const ensureSeekable = () => {
    if (blobTried || !durReady) return;
    try {
      const s = video.seekable;
      if (s && s.length && s.end(s.length - 1) > duration * 0.9) return;
    } catch (_) { /* fall through to blob */ }
    toBlobSource();
  };
  video.addEventListener("error", toBlobSource);

  /* iOS: a muted, never-played video skips painting seeked frames */
  const prime = () => {
    if (primed || reduced.matches || !durReady) return;
    primed = true;
    const attempt = video.play();
    if (attempt && typeof attempt.catch === "function") attempt.then(() => video.pause()).catch(() => {});
  };
  window.addEventListener("touchstart", prime, { passive: true, once: true });
  window.addEventListener("pointerdown", prime, { passive: true, once: true });
  window.addEventListener("scroll", prime, { passive: true, once: true });

  /* pick the phone variant once when the stage is completely idle */
  const pickClip = () => (window.matchMedia("(pointer: coarse)").matches || window.innerWidth < 861) ? "mobile" : "desktop";
  window.addEventListener("resize", () => {
    const want = pickClip();
    if (want === currentClip || state.smooth > 0.02) return;
    currentClip = want;
    durReady = false; lastT = -1; blobTried = false; useBlob = false;
    video.src = CLIPS[want];
    video.load();
  }, { passive: true });

  /* ---------- run the scrub ---------- */
  let rafId = 0, running = false, formIdx = -1;
  const gate = { io: true, hidden: false, reduced: reduced.matches };

  const io = new IntersectionObserver(entries => {
    gate.io = entries.some(e => e.isIntersecting);
    sync();
  }, { rootMargin: "45% 0px 45% 0px" });
  io.observe(section);
  document.addEventListener("visibilitychange", () => { gate.hidden = document.hidden; sync(); });
  if (typeof reduced.addEventListener === "function") {
    reduced.addEventListener("change", () => { gate.reduced = reduced.matches; sync(); });
  } else {
    reduced.addListener && reduced.addListener(() => { gate.reduced = reduced.matches; sync(); });
  }

  const sync = () => {
    const should = gate.io && !gate.hidden && !gate.reduced;
    if (should && !running) { running = true; rafId = requestAnimationFrame(tick); }
    else if (!should && running) {
      running = false;
      cancelAnimationFrame(rafId);
    }
  };

  const seekTo = t => {
    if (!durReady) return;
    if (lastT < 0 || Math.abs(t - lastT) > 0.021) {
      lastT = t;
      try { video.currentTime = Math.min(Math.max(t, 0), Math.max(duration - 0.02, 0)); } catch (_) { /* next tick */ }
    }
  };

  const setForm = idx => {
    if (idx === formIdx) return;
    formIdx = idx;
    for (let f = 0; f < 3; f++) section.classList.toggle(`rs-f${f}`, f === idx);
    dots.forEach((d, i) => d.classList.toggle("rs-hot", i <= idx));
  };

  const tick = () => {
    if (!running) return;
    const rect = section.getBoundingClientRect();
    const track = rect.height - pin.offsetHeight;
    state.p = track > 1 ? clamp01(-rect.top / track) : 0;

    /* glide: exponential smoothing toward the raw scroll target */
    state.smooth += (state.p - state.smooth) * 0.16;
    if (Math.abs(state.p - state.smooth) < 0.0012) state.smooth = state.p;

    const t = state.smooth * duration;
    seekTo(t);

    /* stage classes (CSS transitions shoulder the atmosphere) */
    section.classList.toggle("rs-open", true); /* the roster is the default state: heading is live at rest */
    heading.classList.toggle("rs-compacted", t > 1.28);
    setForm(t < FORM_BREAKS[0] ? 0 : t < FORM_BREAKS[1] ? 1 : 2);
    section.classList.toggle("rs-cta-in", bandOpacity(t, CTA_BAND) > 0.6);
    cueEl && cueEl.classList.toggle("rs-off", state.smooth > 0.035);

    /* team identity crossfades (left) — transform/opacity only */
    for (let i = 0; i < ids.length; i++) {
      const id = ids[i];
      const o = bandOpacity(t, BANDS[i]);
      if (o === 0 && id.style.opacity === "0" && id.style.visibility === "hidden") continue;
      const leaving = t > BANDS[i].out[0];
      id.style.opacity = o.toFixed(3);
      id.style.visibility = o > 0.02 ? "visible" : "hidden";
      id.style.transform = `translateY(${((leaving ? -1 : 1) * (1 - o) * 18).toFixed(1)}px)`;
    }

    /* player-card panel crossfades (right) — transform/opacity only */
    for (let i = 0; i < panels.length; i++) {
      const panel = panels[i];
      const o = bandOpacity(t, BANDS[i]);
      if (o === 0 && panel.style.opacity === "0" && panel.style.visibility === "hidden") continue;
      const leaving = t > BANDS[i].out[0];
      panel.style.opacity = o.toFixed(3);
      panel.style.visibility = o > 0.02 ? "visible" : "hidden";
      panel.style.transform = `translateX(${((leaving ? -1 : 1) * (1 - o) * 26).toFixed(1)}px)`;
      panel.classList.toggle("rs-on", o > 0.6); /* CSS staggers the player cards while the panel leads */
    }

    if (railFill) railFill.style.transform = `scaleY(${state.smooth.toFixed(4)})`;
    rafId = requestAnimationFrame(tick);
  };

  window.addEventListener("pagehide", () => {
    if (useBlob && blobUrl) URL.revokeObjectURL(blobUrl);
  });

  /* boot the scrub loop without waiting for the observer's first
     delivery, so the stage is live the moment the page first paints */
  sync();
})();
