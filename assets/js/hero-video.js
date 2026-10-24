/* Raptor hero background video
   ------------------------------------------------------------------
   Tiny boot for the hero's looping background clip. No scrubbing, no
   scroll listeners driving playback — the clip just plays.

   What it adds beyond the markup:
   - fades the video in on the first *painted* frame (loadeddata),
     so there is no black flash before the decoder is ready
   - retries play() — some browsers reject the first muted-autoplay
     attempt until a user gesture or a second call
   - pauses when the hero scrolls out of view or the tab is hidden,
     and resumes on return (keeps the clip from burning CPU/decoder
     time nobody is watching)
   - yields entirely under prefers-reduced-motion, where CSS already
     hides the video and the still image carries the hero
   ------------------------------------------------------------------ */
(() => {
  const video = document.querySelector(".hero-video");
  if (!video) return;

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  let inView = true;

  const markLive = () => video.classList.add("video-live");

  const sync = () => {
    if (reduced.matches || !inView || document.hidden) {
      if (!video.paused) video.pause();
      return;
    }
    const attempt = video.play();
    if (attempt && typeof attempt.catch === "function") {
      // autoplay refused: leave the still image in place, no error
      attempt.catch(() => {});
    }
  };

  // first painted frame -> fade in over the still
  if (video.readyState >= 2) markLive();
  video.addEventListener("loadeddata", markLive, { once: true });

  // pause off-screen / off-tab
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(entries => {
      inView = entries.some(entry => entry.isIntersecting);
      sync();
    }, { threshold: 0.05 }).observe(video);
  }
  document.addEventListener("visibilitychange", sync);

  // honour a live change of the OS motion setting
  if (typeof reduced.addEventListener === "function") {
    reduced.addEventListener("change", () => {
      if (!reduced.matches) markLive();
      sync();
    });
  }

  sync();
})();
