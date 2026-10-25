# Raptor Esports Portal — Design System Specification

**Document Version:** 1.0.0  
**Target Release:** Raptor Esports Portal 2026 (Production)  
**Classification:** Frontend Design System, Tokens, Typography & Component Standards  
**Asset Root Directory:** `/assets/`  

---

## 1. Design Philosophy: Cyberpunk Esports Aesthetic

The visual and interactive language of the Raptor Esports Portal is crafted around a high-contrast dark cyberpunk esports motif:

1. **Atmospheric Dark Ink Canvas:** Deep space navy and black backgrounds (`#080a13`, `#0d1020`, `#0f111a`) provide an immersive stage where high-chroma accent colors vibrate with optical intensity.
2. **Liquid Glass & Translucency:** Floating glassmorphism cards and navigation bars employ `backdrop-filter: blur(16px)`, translucent fills (`rgba(13, 16, 32, 0.75)`), and hair-thin border sheens (`rgba(255, 255, 255, 0.08)`) to generate depth without heavy drop shadows.
3. **High-Chroma Energy Signatures:** Electric violet (`#6738ef`, `#8655ff`, `#792ACF`), cyber red (`#E0181B`), and luminous gold (`#FFD84D`) act as focal anchors for tournament statuses, player highlights, and telemetry badges.
4. **Zero-Dependency Vanilla Performance:** Implemented strictly in standard CSS3 and vanilla ES6 JavaScript with zero external frameworks (no Tailwind, Bootstrap, Sass, or React). Animation loops run on `requestAnimationFrame` with hardware-accelerated transforms and opacity transitions.

---

## 2. CSS Architecture & Modular Organization

The frontend styling is partitioned into 11 specialized stylesheets under `assets/css/`. Below is the architectural breakdown mapping physical files to logical modular subsystems:

```
assets/css/
├── styles.css            ──► [main.css / responsive.css] Global tokens, CSS reset, base typography & responsive grid
├── sections.css          ──► [header.css] Liquid glass header, tournament card marquee rail & 4-column footer
├── hero-video.css        ──► [hero-media.css] Autoplay looping background video, watermark feathering & view pausing
├── hero-type.css         ──► [fonts.css] Poster headline typography for Anton and Oswald display lockups
├── roster-scrub.css      ──► [roster-scrub.css] Pinned 10s interactive video scrubbing stage & player card reveals
├── roster-background.css ──► [roster-scrub.css] Full-bleed section background video and graphics positioning
├── admin-theme.css       ──► [admin.css / admin-table.css / admin-modal.css / admin-dark.css] Admin console shell, tables & dialogs
├── chatbot.css           ──► [chatbot.css] Floating AI assistant widget, chat drawer, launcher pill & markdown
├── team-detail.css       ──► Dedicated single-team profile views, hero banners & roster grid
├── team-logos.css        ──► Vector team emblems, color mixing filters & badge styling
└── social-links.css      ──► SVG alignment, hover glowing states & social icon bars
```

### Detailed Breakdown of the 11 Stylesheets

| Stylesheet File | Byte Size | Lines | Functional Role & Architecture Mapping |
|---|---|---|---|
| `assets/css/styles.css` | 27,999 | 44 | **Main & Responsive Base (`main.css`, `responsive.css`):** Global CSS custom property definitions, base resets, primary button styling, responsive grids (`@media (max-width: 1000px)`, `@media (max-width: 700px)`), and accessibility fallbacks. |
| `assets/css/sections.css` | 20,500 | 551 | **Header & Sections (`header.css`):** Sticky liquid glass navigation header (`.site-header`), NEXT UP tournament card marquee track, community engagement grid, and 4-column dark footer. |
| `assets/css/hero-video.css` | 2,487 | 65 | **Hero Media (`hero-media.css`):** Full-bleed video positioning, `.video-live` opacity fade-in transition (0.6s), and `.hero-wm` radial blur mask for video watermark neutralization. |
| `assets/css/hero-type.css` | 3,046 | 44 | **Display Typography (`fonts.css`):** High-impact poster typography scoped to `#home.hero` featuring stacked Anton headings and tracked Oswald uppercase mantra straps. |
| `assets/css/roster-scrub.css`| 21,761 | 637 | **Roster Scrub Engine (`roster-scrub.css`):** Sticky timeline stage pinned over 5.6 viewport heights, canvas transformation morphs, scrub progress rail, and animated player art cards. |
| `assets/css/roster-background.css` | 1,251 | 7 | **Background Overlays:** Bleed positioning and atmospheric layering behind the interactive roster scrub stage. |
| `assets/css/admin-theme.css` | 40,883 | 1,733 | **Admin Console Suite (`admin.css`, `admin-table.css`, `admin-modal.css`, `admin-dark.css`):** Full administrative workspace styling, off-canvas mobile drawer, RBAC visibility toggling, native `<dialog>` modals, and data tables. |
| `assets/css/chatbot.css` | 11,444 | 402 | **AI Chat Widget (`chatbot.css`):** Floating pill launcher with glowing pulse animation (`rc-glow`), expandable drawer, markdown formatting, model status indicators, and mobile bottom sheet. |
| `assets/css/team-detail.css` | 4,631 | 47 | **Team Profiles:** Specialized layouts for `/teams/<id>` pages, responsive roster card grid, and match stats. |
| `assets/css/team-logos.css` | 820 | 8 | **Vector Graphics:** Color-burn and drop-shadow styling for SVG esports team crests. |
| `assets/css/social-links.css` | 617 | 6 | **Social Navigation:** Header and footer social icon alignments with purple hover sheen. |

---

## 3. Color Palette & Design Tokens

### 3.1 Global Public Palette (`assets/css/styles.css`)
```css
:root {
  /* Canvas & Panel Inks */
  --ink: #080a13;         /* Deep canvas black */
  --navy: #0d1020;        /* Secondary navy background */
  --panel: #111522;       /* Raised card surfaces */
  --line: #e8eaf1;        /* Subtle hairline divider */
  --white: #ffffff;       /* Pure white */

  /* High-Chroma Brand Accents */
  --purple: #6738ef;      /* Primary electric purple */
  --purple2: #8655ff;     /* Vivid secondary violet hover */
  --lav: #f1edff;         /* Lavender highlight tint */

  /* Content & Telemetry */
  --text: #171927;        /* High-contrast content dark */
  --muted: #6e7486;       /* Subdued secondary captions */
  --green: #20a877;       /* Live match / Success emerald */
  --shadow: 0 18px 50px rgba(5, 7, 20, 0.18);
}
```

---

### 3.2 Admin Console Palette (`assets/css/admin-theme.css`)
```css
.admin-body {
  /* Surfaces & Canvas */
  --adm-bg: #0f111a;              /* Admin deep canvas */
  --adm-surface: #171a26;         /* Primary container surface */
  --adm-surface-alt: #202434;     /* Elevated input / row hover */
  --adm-border: #282d3e;          /* Standard structural border */
  --adm-border-strong: #383f56;   /* Focus and active border */

  /* Typography */
  --adm-text: #f0f0f0;            /* Primary light body */
  --adm-secondary: #a0a0a0;       /* Secondary metadata */
  --adm-muted: #707070;           /* De-emphasized timestamps */

  /* Interactive Indigo Accents */
  --adm-primary: #6366f1;         /* Primary action button */
  --adm-primary-strong: #7c6cff;  /* Active / hover state */
  --adm-primary-hover: #6358e8;   /* Pressed state */
  --adm-primary-soft: rgba(99, 102, 241, 0.12);

  /* Status Tokens */
  --adm-success: #10b981;
  --adm-success-text: #34d399;
  --adm-success-soft: rgba(16, 185, 129, 0.12);
  --adm-warning: #f59e0b;
  --adm-warning-text: #fbbf24;
  --adm-warning-soft: rgba(245, 158, 11, 0.12);
  --adm-error: #ef4444;
  --adm-error-text: #f87171;
  --adm-error-soft: rgba(239, 68, 68, 0.1);
  --adm-info-text: #60a5fa;
  --adm-info-soft: rgba(59, 130, 246, 0.12);
  --adm-yellow: #FFD84D;

  /* Sidebar Tokens */
  --adm-sidebar-bg: #0d1020;
  --adm-sidebar-bg-deep: #090b14;
  --adm-sidebar-text: #f4f2ff;
  --adm-sidebar-muted: #a6aac1;
  --adm-sidebar-line: rgba(255, 255, 255, 0.08);
  --adm-sidebar-accent: #8c5dff;
}
```

---

### 3.3 Roster Scrub Stage Palette (`assets/css/roster-scrub.css`)
```css
#roster-scrub {
  /* Scroll Geometry */
  --rs-scroll: 5.6; /* Pinned scrub distance in viewport heights */
  --rs-bezel: max(clamp(22px, 6vw, 76px), calc((100% - 1228px) / 2));

  /* Electric Violet Gradient Stops */
  --rs-accent-1: #792ACF; /* Deep violet */
  --rs-accent-2: #AE48ED; /* Mid violet */
  --rs-accent-3: #EB84F9; /* High lavender */
  --rs-ink: #FDDAFE;      /* Soft glow foreground */

  /* High-Contrast Identity Colors */
  --rs-red: #E0181B;      /* Reference red — team display name */
  --rs-yellow: #FFD84D;   /* Bright gold — player names on art cards */
}
```

Atmospheric background radial gradients incorporate depth stops:
`#030010` $\to$ `#090227` $\to$ `#14053E` $\to$ `#240A59` $\to$ `#5419A2` $\to$ `#6F012D`.

---

### 3.4 AI Chatbot Tokens (`assets/css/chatbot.css`)
```css
.raptor-chat {
  --rc-bg: #0a0d18;                    /* Drawer background */
  --rc-panel: #101424;                 /* Input bar & bubble surface */
  --rc-line: rgba(255, 255, 255, 0.09);/* Hairline divider */
  --rc-purple: #7442f2;                /* User bubble & launcher glow */
  --rc-purple-2: #a071ff;              /* Gradient hover state */
}
```

---

### 3.5 Status Badges & Alert Tokens

| State | Primary Border & Fill | Text Token | Typical Portal Usage |
|---|---|---|---|
| **Active / Success** | `#10b981` / `rgba(16, 185, 129, 0.12)` | `#34d399` | Team "Active", Player "Active", Match "Completed" |
| **Warning / Trial** | `#f59e0b` / `rgba(245, 158, 11, 0.12)` | `#fbbf24` | Player "Trial", Team "Recruiting", Tournament "Upcoming" |
| **Danger / Inactive**| `#ef4444` / `rgba(239, 68, 68, 0.1)` | `#f87171` | Player "Inactive", Team "Inactive", Delete Actions |
| **Info / Live Pulse**| `#3b82f6` / `rgba(59, 130, 246, 0.12)` | `#60a5fa` | Match "Live", Tournament "Ongoing", Live AI Dot |

---

## 4. Typography Hierarchy & Local Font Assets

To conform to a strict Content Security Policy (`font-src 'self'`) and ensure zero CDN latency, all 11 font files reside locally in `assets/fonts/`:

```
assets/fonts/
├── Valorant Font.ttf          ──► "Raptor Valorant" / "Team Vitality"
├── saira-stencil-one-400.woff2──► "Sayonara" / "Raptor Stencil"
├── anton-400.woff2            ──► "Anton"
├── oswald-600.woff2           ──► "Oswald" (Semi-Bold)
├── oswald-700.woff2           ──► "Oswald" (Bold)
├── general-sans-400.woff2     ──► "General Sans" (Regular)
├── general-sans-500.woff2     ──► "General Sans" (Medium)
├── general-sans-600.woff2     ──► "General Sans" (Semi-Bold)
├── general-sans-700.woff2     ──► "General Sans" (Bold)
├── dm-sans.woff2              ──► "DM Sans"
└── jetbrains-mono.woff2       ──► "JetBrains Mono"
```

### 4.1 Typography Specifications Table

| Font Alias | Local Source File | Format | Weights | Fallback Stack | Component Role & Usage |
|---|---|---|---|---|---|
| **"Raptor Valorant"** | `Valorant Font.ttf` | TrueType | 400–900 | `"Anton", Impact, "Arial Narrow", sans-serif` | Hero headline (`#home.hero h1`), roster scrub title (`.rs-title`), tournament marquee headlines (`.tourney-name`), section headers (`#about h2`). |
| **"Sayonara"** / **"Raptor Stencil"** | `saira-stencil-one-400.woff2` | WOFF2 | 400 | `"Anton", Impact, "Arial Narrow", sans-serif` | Team branding in scrub stage (`.rs-team-name` in red `#E0181B`), player card names (`.rs-pname` in gold `#FFD84D`), competition metrics. |
| **"Anton"** | `anton-400.woff2` | WOFF2 | 400 | `Impact, "Arial Narrow", system-ui, sans-serif` | Poster typography, organization statistics counters (`.stats-strip strong`, `.rs-team-foot strong`). |
| **"Oswald"** | `oswald-600.woff2`, `oswald-700.woff2` | WOFF2 | 600, 700 | `Impact, "Arial Narrow", system-ui, sans-serif` | Tracked uppercase labels (`.eyebrow`, `letter-spacing: 0.12em`), mantra straps (`.hero-mantra`), button labels, game pills, player roles (`.rs-prole`). |
| **"General Sans"** | `general-sans-400.woff2` through `700.woff2` | WOFF2 | 400, 500, 600, 700 | `ui-sans-serif, system-ui, -apple-system, sans-serif` | Admin console headings (`h1`, `h2`, `h3`), admin brand wordmark, dialog headers, summary card statistics (`.stat-card strong`). |
| **"DM Sans"** | `dm-sans.woff2` | WOFF2 | 400, 500, 700 | `ui-sans-serif, system-ui, -apple-system, sans-serif` | Admin body copy (`.admin-body`), tabular cell text, input controls, sidebar links, settings descriptions. |
| **"JetBrains Mono"** | `jetbrains-mono.woff2` | WOFF2 | 400 | `Consolas, Menlo, Monaco, monospace` | Monospaced technical identifiers, database status notes, code snippets in chat assistant. |
| **Inter** | System Font | System | 400, 500, 600 | `ui-sans-serif, system-ui, -apple-system, sans-serif` | Public portal narrative paragraphs, floating chat message bubbles (`.raptor-chat`), footer links. |

---

### 4.2 Hierarchy Guidelines

```
1. HERO DISPLAY HEADLINE
   Font: "Raptor Valorant", 700
   Size: clamp(46px, 10vw, 96px) | Line Height: 0.95 | Transform: uppercase

2. SECTION DISPLAY HEADER
   Font: "Raptor Valorant", 700
   Size: clamp(32px, 5vw, 48px)  | Line Height: 1.1  | Transform: uppercase

3. SUBHEADINGS & CARD LABELS
   Font: "Oswald", 600
   Size: clamp(14px, 1.8vw, 18px)| Letter Spacing: 0.12em | Transform: uppercase

4. ADMIN CONSOLE HEADINGS
   Font: "General Sans", 600
   Size: 22px to 28px            | Line Height: 1.25

5. BODY & DATA TABLE TEXT
   Font: "DM Sans" (Admin) / Inter (Public), 400
   Size: 14px to 15px            | Line Height: 1.55
```

---

## 5. UI Component Specifications

### 5.1 Liquid Glass Navigation Header (`sections.css`)
Floating sticky header pinned to the top of the viewport:
- **Backdrop Sheen:** `backdrop-filter: blur(16px); background: rgba(8, 10, 19, 0.78); border-bottom: 1px solid rgba(255, 255, 255, 0.08);`.
- **Navigation Tabs:** Flex container with 32px gap. Links render in Oswald 600 with uppercase tracking (`letter-spacing: 0.08em`).
- **Hover Glow:** Hovering on links produces a soft underglow using `text-shadow: 0 0 12px var(--purple2); color: var(--lav);`.
- **Mobile Toggle:** On viewports $\le 700\text{px}$, navigations collapse into an off-canvas liquid glass dropdown triggered by the `.menu-toggle` button.

---

### 5.2 Looping Hero Video Component (`hero-video.js` & `hero-video.css`)
Cinematic background video layer embedded inside `<section id="home" class="hero">`:
- **HTML Markup:**
  ```html
  <video class="hero-video" src="/Hero-video.mp4" poster="/assets/home-background.png"
         autoplay loop muted playsinline preload="auto" disablepictureinpicture></video>
  <div class="hero-wm" aria-hidden="true"></div>
  ```
- **Zero-Flicker Fade-In:** Video starts with CSS `opacity: 0;`. The JavaScript controller waits for the `loadeddata` or `readyState >= 2` event, then attaches the `.video-live` class, triggering a smooth 0.6-second ease-in transition.
- **Resource Management (IntersectionObserver):** Automatically executes `video.pause()` when scrolled out of view (`threshold: 0.05`) and halts decoder activity upon browser tab `visibilitychange` to conserve CPU/GPU cycles.
- **Corner Watermark Feathering (`.hero-wm`):** A dedicated curved feathering layer pinned to the corner with:
  ```css
  .hero-wm {
    position: absolute;
    bottom: 0;
    right: 0;
    width: 220px;
    height: 90px;
    backdrop-filter: blur(18px) saturate(1.05);
    background: radial-gradient(130% 130% at 100% 100%, rgba(8, 10, 19, 0.95) 20%, rgba(8, 10, 19, 0) 75%);
    mask-image: radial-gradient(130% 130% at 100% 100%, #000 30%, transparent 68%);
  }
  ```

---

### 5.3 10-Second Roster Scrub Stage (`roster-scrub.js` & `roster-scrub.css`)
Interactive storytelling stage synchronizing scroll progression with video scrubbing:
- **Pinned Timeline:** Container `.rs-pin` locked at `top: 0` across a total scroll height factor of `5.6` viewport-heights (`--rs-scroll: 5.6` on desktop; `4.8` on mobile).
- **Smooth Playhead Interpolation:** JavaScript loop executed on `requestAnimationFrame` using linear interpolation damping:
  $$\text{smooth} \leftarrow \text{smooth} + (\text{target} - \text{smooth}) \times 0.16$$
  Maps playhead smoothly from 0.0s to 10.0s of `/assets/video/poseidon-scrub.mp4`.
- **Morph Synchronization Beats:**
  - **Band 0 (BGMI Lineup):** Active from 0.0s to 3.15s; crossfades out as suit energy morph begins (3.15s–3.70s).
  - **Band 1 (Free Fire Lineup):** Fades in at 3.35s–3.95s on cyan energy bloom, holds until 5.55s, fades out by 6.15s.
  - **Band 2 (Valorant Lineup):** Fades in at 6.15s on magenta ring burst and holds until end of stage.
  - **CTA Reveal:** "Manage Team" action button glides upward at 9.15s–9.60s.
- **Art Cards Stack:** Right-hand panel displaying 5 player cards populated from `/api/public/teams/<id>`, rendering yellow stencil IGNs (`--rs-yellow: #FFD84D`), roles, and player avatars (`assets/players/01-hood.png` ... `08-phoenix.png`).

---

### 5.4 Admin Console UI (`admin-theme.css` & `admin.js`)
Editorial dark theme for management operations:
- **Responsive Off-Canvas Layout:** Fixed sidebar column transitions to an off-canvas drawer (`left: -245px`) on viewports $\le 860\text{px}$. Toggled via `#sidebar-toggle` with backdrop dismiss overlay (`#sidebar-backdrop`).
- **RBAC Visibility Engine:** Elements tagged with `data-permission="<key>"` are evaluated against user permissions on login and automatically hidden if unauthorized.
- **Native Modal Dialogs (`<dialog>`):** Native HTML5 dialogs with frosted glass backdrops (`::backdrop { background: rgba(5, 7, 15, 0.7); backdrop-filter: blur(8px); }`), form validation, and CSRF token binding.
- **Tabular Data Grids:** Data tables styled with `--adm-surface`, hover row brightening (`--adm-surface-alt`), and role/status badge pills.

---

### 5.5 AI Chat Widget (`chatbot.css` & `chatbot.js`)
Floating assistant widget available on all views:
- **Pill Launcher:** Floating pill with eagle mark and animated pulse glow ring (`rc-glow` keyframe).
- **Status Indicator Dot:** Real-time visual feedback:
  - **Green (`#10b981`):** Live AI connected (OpenAI / NaraRouter).
  - **Cyan (`#00e5ff`):** Local deterministic fallback mode.
  - **Red (`#ef4444`):** Network offline or error.
- **Custom Markdown Parser:** Zero-dependency client-side parser converting `#` headings, `**bold**`, `*italic*`, `~~del~~`, `` `code` ``, fenced code blocks (````pre/code````), unordered/ordered lists, and horizontal rules into clean HTML.
- **Mobile Sheet:** On viewports $\le 520\text{px}$, transforms into a full-width bottom drawer with touch-friendly controls.

---

## 6. Responsive Breakpoints & Media Adaptations

The design system incorporates structured media queries handling fluid layout transformations from widescreen desktops down to compact mobile phones:

### 6.1 Breakpoint Reference Matrix

```
       1200px               992px / 860px             700px / 620px            480px
─────────┬────────────────────────┬─────────────────────────┬────────────────────┬────────►
         │                        │                         │                    │
    Widescreen                 Tablet                     Mobile              Compact
  Desktop Layout            Grid Collapse              Sheet Drawers          Mobile
```

| Breakpoint | Target Media Query | Layout Adaptations |
|---|---|---|
| **Widescreen / Desktop** | `@media (max-width: 1200px)` | Dashboard metric cards wrap; modal dialog widths clamp to `min(90vw, 840px)`. |
| **Medium Desktop** | `@media (max-width: 1060px)` | Roster scrub side panel narrows to `min(310px, 30vw)`; identity panel adjusts to `min(460px, 46vw)`. |
| **Tablet Collapse** | `@media (max-width: 1000px)` | Public navigation gap reduces to 18px; team card grid collapses from 4 columns to 2 columns; admin metric grid stacks vertically. |
| **Mobile Drawer** | `@media (max-width: 860px)` | **Admin Console:** Sidebar converts into off-canvas drawer (`left: -245px`) with backdrop overlay. **Roster Scrub:** Scrub scroll factor decreases to `4.8`; player art cards transform into a 2-column bottom sheet. |
| **Mobile Bar** | `@media (max-width: 700px)` | Header shrinks to 64px mobile bar; public navigation collapses into liquid glass dropdown; hero headline scales via `clamp(46px, 13vw, 64px)`; hero video centers at `62% center`. |
| **Dialog Collapse** | `@media (max-width: 620px)` | Admin modal forms collapse into single-column inputs; action buttons expand to full touch targets. |
| **Full Mobile Sheet**| `@media (max-width: 520px)` | AI Chatbot drawer transforms into full-width mobile sheet (`left: 12px; right: 12px; bottom: 76px; width: auto;`). |
| **Compact Mobile** | `@media (max-width: 480px)` | Roster scrub subtitle description hides; footer grid collapses to single column. |

---

### 6.2 Reduced Motion Accessibility (`prefers-reduced-motion: reduce`)
To comply with WCAG 2.1 Level AAA motion accessibility standards, when the user's OS has reduced motion enabled:
1. **Video Decoders Suppressed:** Video elements (`.hero-video`, `.rs-video`, `.tn-video`, `.ab-video`) are set to `display: none;`, revealing high-resolution static poster art (`poseidon-poster.jpg`, `tournaments-poster.jpg`, `about-poster.jpg`).
2. **Infinite Marquee Stopped:** Continuous CSS translation animations on tournament card rails are disabled and converted into native horizontal touch scrolling (`overflow-x: auto; -webkit-overflow-scrolling: touch`).
3. **Timeline Scrub Pinning Disabled:** Pinned sticky scroll stages (`#roster-scrub`) unpin and display as static vertical component stacks.
4. **Instant Transitions:** Keyframe animations and transitions are neutralized:
   ```css
   @media (prefers-reduced-motion: reduce) {
     *, *::before, *::after {
       animation-duration: 0.01ms !important;
       animation-iteration-count: 1 !important;
       transition-duration: 0.01ms !important;
     }
   }
   ```
