/* sections.js — behaviour for the upgraded landing sections:
   - solid-state glass header (is-scrolled)
   - both below-fold background videos: lazy source loading + a play
     controller that never lets two clips run simultaneously
   - right-to-left tournament card rail (duplicated track, hover /
     focus / touch pause, native horizontal scroll under reduced motion)
   - entrance reveals for the NEXT UP head + cards and the CTA block
   - footer copyright year

   Geometry ticks (rAF-throttled scroll/resize) drive every load /
   play / reveal decision: cheaper than observers for two elements and
   immune to silent IntersectionObserver environments. public.js fills
   #public-tournaments after its /api/public fetch — the marquee
   builds on whatever it renders (or leaves the loading text alone if
   the API is down). No new libraries.                                */
(() => {
  document.documentElement.classList.add("sec-js"); /* gates every entrance-hidden CSS state */
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const majorEvents = ["scroll", "resize"];

  /* ---- glass header: scroll state (rAF-throttled) ----------------- */
  const header = document.querySelector(".site-header");
  if (header) {
    let queued = false;
    const paint = () => { queued = false; header.classList.toggle("is-scrolled", (window.scrollY || 0) > 10); };
    window.addEventListener("scroll", () => { if (!queued) { queued = true; requestAnimationFrame(paint); } }, { passive: true });
    paint();
  }

  /* ---- the two section clips: load near, play when visible -------- */
  const videos = Array.from(document.querySelectorAll("[data-bg-video]"));
  let refreshVideos = () => { };
  if (videos.length && !reduceMotion) {
    const clip = rect => {
      const h = rect.height || 1;
      const top = rect.top, bottom = rect.bottom;
      const overlap = Math.min(bottom, innerHeight) - Math.max(top, 0);
      return Math.max(0, Math.min(1, overlap / h)); /* how much of the clip's section is on screen */
    };
    refreshVideos = () => {
      let best = null, bestRatio = 0;
      for (const v of videos) {
        if (v.classList.contains("is-failed")) continue;
        const r = clip(v.getBoundingClientRect());
        const near = r > 0 || (v.getBoundingClientRect().top < innerHeight * 1.55 && v.getBoundingClientRect().bottom > -innerHeight);
        if (near && !v.dataset.loaded) { v.dataset.loaded = "1"; v.src = v.dataset.src; } /* faststart remux: frames arrive early */
        if (v.dataset.loaded && r > bestRatio) { best = v; bestRatio = r; }
      }
      const run = best && bestRatio > .07 && !document.hidden;
      for (const v of videos) {
        if (v.classList.contains("is-failed") || v.dataset.loaded !== "1") continue;
        if (v === best && run) {
          if (v.paused) { const p = v.play(); if (p && p.catch) p.catch(() => { }); }
          v.classList.add("is-live");
        } else if (!v.paused) {
          v.pause();
          if (v !== best) v.classList.remove("is-live");
        }
      }
    };
    document.addEventListener("visibilitychange", () => { if (document.hidden) { for (const v of videos) if (!v.paused) v.pause(); } else refreshVideos(); });
    window.addEventListener("pagehide", () => { for (const v of videos) if (!v.paused) v.pause(); });
    for (const v of videos) {
      v.addEventListener("canplay", () => { v.classList.add("is-live"); refreshVideos(); });
      v.addEventListener("error", () => { v.classList.add("is-failed"); refreshVideos(); });
    }
  }

  /* ---- entrance reveals + section clip driving share one tick ----- */
  const tournaments = document.querySelector(".tournament-banner");
  const about = document.getElementById("about");
  let tickQueued = false;
  const tick = () => {
    tickQueued = false;
    if (tournaments && !tournaments.classList.contains("tn-in")) {
      const r = tournaments.getBoundingClientRect();
      if (r.top < innerHeight * .85 && r.bottom > innerHeight * .15) {
        tournaments.classList.add("tn-in");
        if (!reduceMotion) setTimeout(() => {
          tournaments.classList.add("tn-run");
          refreshVideos(); /* marquee settled — start/end the clip with the entrance */
        }, 750);
      }
    }
    if (about && !about.classList.contains("community-in")) {
      const r = about.getBoundingClientRect();
      if (r.top < innerHeight * .8 && r.bottom > innerHeight * .2) about.classList.add("community-in");
    }
    refreshVideos();
  };
  const scheduleTick = () => { if (!tickQueued) { tickQueued = true; setTimeout(tick, 0); } };
  majorEvents.forEach(ev => window.addEventListener(ev, scheduleTick, { passive: true }));
  document.addEventListener("visibilitychange", scheduleTick);
  /* belt and braces: a slow geometry poll drives environments that
     never deliver scroll events (automation tabs, some embedded
     webviews) — a handful of rect reads per beat costs ~nothing */
  setInterval(scheduleTick, 300);
  tick();

  /* ---- the card rail: duplicate the group, run, pause surfaces ----- */
  const rail = document.querySelector("#public-tournaments[data-marquee]");
  if (rail) {
    const build = () => {
      const cards = Array.from(rail.children).filter(c => c.matches(".tournament-mini"));
      if (!cards.length) return;
      const track = document.createElement("div");
      track.className = "tn-track";
      const group = document.createElement("div");
      group.className = "tn-group";
      group.append(...cards);
      track.append(group);
      if (!reduceMotion) {
        const clone = group.cloneNode(true);
        clone.classList.add("tn-clone");
        clone.setAttribute("aria-hidden", "true");
        track.append(clone);
      }
      rail.append(track);
      const loading = rail.querySelector(":scope > span");
      if (loading) loading.remove();
      if (!reduceMotion) {
        const hold = () => rail.classList.add("tn-touch");
        const release = () => setTimeout(() => rail.classList.remove("tn-touch"), 700);
        rail.addEventListener("touchstart", hold, { passive: true });
        rail.addEventListener("touchend", release, { passive: true });
        rail.addEventListener("touchcancel", release, { passive: true });
      }
    };
    if (rail.querySelector(".tournament-mini")) build();
    else new MutationObserver((entries, obs) => {
      if (rail.querySelector(".tournament-mini")) { obs.disconnect(); build(); }
    }).observe(rail, { childList: true });
  }

  /* ---- CTA reveal for environments where scrolling is impossible --- */
  if (about && reduceMotion) about.classList.add("community-in");
  if (tournaments && reduceMotion) tournaments.classList.add("tn-in");

  /* ---- footer year -------------------------------------------------- */
  const year = document.querySelector(".foot-year");
  if (year) year.textContent = String(new Date().getFullYear());
})();
