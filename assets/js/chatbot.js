/* Raptor AI Assistant — floating widget for public and signed-in pages. */
(() => {
  "use strict";
  if (window.__raptorChatLoaded) return;
  window.__raptorChatLoaded = true;

  const STORE_KEY = "raptor.ai.chat.v1";
  const MAX_STORED_MESSAGES = 24;
  const MAX_CONTEXT_MESSAGES = 10;
  const state = {
    session: { authenticated: false, user: null, csrf: null, permissions: {} },
    modeKey: "public",
    messages: [],
    suggestions: [],
    greeting: "",
    mode: "ready",
    typing: false,
    busy: false,
  };

  const root = document.createElement("div");
  root.className = "raptor-chat";
  root.innerHTML = `
    <button type="button" class="raptor-chat-launcher" aria-expanded="false" aria-controls="raptor-chat-panel" aria-label="Open Raptor AI Assistant">
      <span class="raptor-chat-mark" aria-hidden="true">✦</span>
      <span class="raptor-chat-launcher-copy">Raptor AI<small>Assistant</small></span>
    </button>
    <section id="raptor-chat-panel" class="raptor-chat-panel" role="dialog" aria-modal="false" aria-labelledby="raptor-chat-title" aria-hidden="true" inert>
      <header class="raptor-chat-header">
        <span class="raptor-chat-mark" aria-hidden="true">✦</span>
        <div class="raptor-chat-heading">
          <h2 class="raptor-chat-title" id="raptor-chat-title">Raptor AI Assistant</h2>
          <div class="raptor-chat-subtitle"><span class="raptor-chat-dot" data-status-dot></span><span data-status>Connecting…</span></div>
        </div>
        <div class="raptor-chat-actions">
          <button type="button" class="raptor-chat-icon" data-reset title="Start a new chat" aria-label="Start a new chat">↺</button>
          <button type="button" class="raptor-chat-icon" data-close title="Close assistant" aria-label="Close Raptor AI Assistant">×</button>
        </div>
      </header>
      <div class="raptor-chat-scroll" data-scroll role="log" aria-live="polite" aria-relevant="additions" aria-label="Raptor AI conversation"></div>
      <div class="raptor-chat-suggestions" data-suggestions aria-label="Suggested questions"></div>
      <form class="raptor-chat-form" data-form>
        <label class="sr-only" for="raptor-chat-input">Ask Raptor AI Assistant a question</label>
        <textarea id="raptor-chat-input" class="raptor-chat-input" data-input rows="1" maxlength="2000" placeholder="Ask about teams, matches, performance…" aria-label="Message Raptor AI Assistant" disabled></textarea>
        <button type="submit" class="raptor-chat-send" data-send aria-label="Send message" disabled>➤</button>
      </form>
      <div class="raptor-chat-foot"><span>Raptor AI can make mistakes.</span><b data-mode-label>Role-aware</b></div>
    </section>`;
  document.body.append(root);

  const launcher = root.querySelector(".raptor-chat-launcher");
  const panel = root.querySelector(".raptor-chat-panel");
  const scroll = root.querySelector("[data-scroll]");
  const suggestions = root.querySelector("[data-suggestions]");
  const form = root.querySelector("[data-form]");
  const input = root.querySelector("[data-input]");
  const sendButton = root.querySelector("[data-send]");
  const statusText = root.querySelector("[data-status]");
  const statusDot = root.querySelector("[data-status-dot]");
  const modeLabel = root.querySelector("[data-mode-label]");

  function firstName(name) {
    return String(name || "").trim().split(/\s+/)[0] || "there";
  }

  function authSuggestions() {
    const role = state.session.user?.role;
    const permissions = state.session.permissions || {};
    if (role === "player") return ["My performance", "My team", "Upcoming matches"];
    if (role === "coach" || role === "analyst") return ["Team roster", "Performance summary", "Upcoming matches"];
    const items = ["Team overview", "Performance summary", "Upcoming matches"];
    if (permissions["financial.view"]) items.push("Expense summary");
    if (role === "admin" || role === "manager") items.push("Recent activity");
    return items.slice(0, 4);
  }

  const PUBLIC_SUGGESTIONS = ["Our teams", "Upcoming tournaments", "How do I join?"];

  function configureSession(session) {
    state.session = session;
    const authenticated = !!session.authenticated;
    state.modeKey = authenticated ? `auth:${session.user?.email || session.user?.role || "user"}` : "public";
    state.greeting = authenticated
      ? `Hi ${firstName(session.user?.name)}! I'm Raptor AI Assistant. Ask me about your teams, matches, performance, or anything in your workspace.`
      : "Hi! I'm Raptor AI Assistant. Ask me about Raptor's teams, tournaments, upcoming matches, or how to join.";
    state.suggestions = authenticated ? authSuggestions() : PUBLIC_SUGGESTIONS;
  }

  async function detectSession() {
    try {
      const response = await fetch("/api/chat/session", {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) return { authenticated: false };
      const data = await response.json();
      if (!data?.authenticated || !data?.user?.role) return { authenticated: false };
      return {
        authenticated: true,
        user: data.user,
        csrf: data.csrf || null,
        permissions: data.permissions || {},
      };
    } catch {
      return { authenticated: false };
    }
  }

  function readStored() {
    try {
      const raw = sessionStorage.getItem(STORE_KEY);
      if (!raw) return null;
      const saved = JSON.parse(raw);
      if (!saved || saved.modeKey !== state.modeKey || !Array.isArray(saved.messages)) return null;
      const messages = saved.messages
        .filter(message => message && (message.role === "user" || message.role === "assistant") && typeof message.content === "string")
        .slice(-MAX_STORED_MESSAGES)
        .map(message => ({
          role: message.role,
          content: message.content.slice(0, 8000),
          greeting: !!message.greeting,
          error: !!message.error,
          notice: typeof message.notice === "string" ? message.notice.slice(0, 500) : "",
        }));
      if (!messages.length) return null;
      return { messages, mode: ["openai", "local", "ready", "error"].includes(saved.mode) ? saved.mode : "ready" };
    } catch {
      return null;
    }
  }

  function persist() {
    try {
      sessionStorage.setItem(STORE_KEY, JSON.stringify({
        modeKey: state.modeKey,
        mode: state.mode,
        messages: state.messages.slice(-MAX_STORED_MESSAGES),
      }));
    } catch {
      /* Session storage can be unavailable in private modes. */
    }
  }

  function resetConversation() {
    state.typing = false;
    state.busy = false;
    state.mode = "ready";
    state.messages = [{ role: "assistant", content: state.greeting, greeting: true }];
    setMode("ready");
    persist();
    render();
    updateComposer();
    input.focus();
  }

  function setMode(mode) {
    state.mode = mode;
    const authenticated = state.session.authenticated;
    if (mode === "openai") {
      statusText.textContent = "Live AI";
      modeLabel.textContent = "Live AI";
      statusDot.className = "raptor-chat-dot";
    } else if (mode === "local") {
      statusText.textContent = "Local mode";
      modeLabel.textContent = "Local mode";
      statusDot.className = "raptor-chat-dot local";
    } else if (mode === "error") {
      statusText.textContent = "Offline";
      modeLabel.textContent = "Offline";
      statusDot.className = "raptor-chat-dot local";
    } else {
      statusText.textContent = authenticated ? "Role-aware" : "Public assistant";
      modeLabel.textContent = authenticated ? "Role-aware" : "Public";
      statusDot.className = "raptor-chat-dot";
    }
    statusDot.classList.toggle("thinking", state.typing);
  }

  const INLINE_MARKERS = ["**", "__", "~~", "`", "*"];

  function findInlineMarker(text, start) {
    let found = null;
    for (const marker of INLINE_MARKERS) {
      const index = text.indexOf(marker, start);
      if (index === -1) continue;
      if (!found || index < found.index || (index === found.index && marker.length > found.marker.length)) {
        found = { index, marker };
      }
    }
    return found;
  }

  function appendInline(parent, text, depth = 0) {
    let index = 0;
    while (index < text.length) {
      const next = findInlineMarker(text, index);
      if (!next) {
        parent.append(text.slice(index));
        return;
      }
      if (next.index > index) parent.append(text.slice(index, next.index));
      const marker = next.marker;
      if (marker === "*" && /[A-Za-z0-9]/.test(text[next.index - 1] || "")) {
        parent.append("*");
        index = next.index + 1;
        continue;
      }
      const close = text.indexOf(marker, next.index + marker.length);
      if (close === -1 || close === next.index + marker.length) {
        parent.append(marker);
        index = next.index + marker.length;
        continue;
      }
      if (marker === "*" && /[A-Za-z0-9]/.test(text[close + 1] || "")) {
        parent.append("*");
        index = next.index + 1;
        continue;
      }
      const inner = text.slice(next.index + marker.length, close);
      if (marker === "`") {
        const code = document.createElement("code");
        code.textContent = inner;
        parent.append(code);
      } else {
        const tag = marker === "**" || marker === "__" ? "strong" : marker === "~~" ? "del" : "em";
        const element = document.createElement(tag);
        if (depth < 8) appendInline(element, inner, depth + 1);
        else element.textContent = inner;
        parent.append(element);
      }
      index = close + marker.length;
    }
  }

  function renderMessageContent(container, content) {
    container.replaceChildren();
    const lines = String(content || "").replace(/\r\n?/g, "\n").split("\n");
    let paragraph = [];
    let list = null;
    let code = null;

    const flushParagraph = () => {
      if (!paragraph.length) return;
      const element = document.createElement("p");
      paragraph.forEach((line, index) => {
        if (index) element.append(document.createElement("br"));
        appendInline(element, line);
      });
      container.append(element);
      paragraph = [];
    };
    const closeList = () => {
      if (!list) return;
      container.append(list.element);
      list = null;
    };
    const flushCode = () => {
      if (!code) return;
      const pre = document.createElement("pre");
      const codeElement = document.createElement("code");
      if (code.language) codeElement.className = `language-${code.language}`;
      codeElement.textContent = code.lines.join("\n");
      pre.append(codeElement);
      container.append(pre);
      code = null;
    };
    const startList = (type, start) => {
      closeList();
      const element = document.createElement(type);
      if (type === "ol" && start && start !== 1) element.start = String(start);
      list = { type, element };
    };

    for (const rawLine of lines) {
      const line = rawLine.replace(/\s+$/, "");
      if (code) {
        if (/^\s*```\s*$/.test(line)) flushCode();
        else code.lines.push(rawLine);
        continue;
      }
      const fence = line.match(/^\s*```([\w-]*)\s*$/);
      if (fence) {
        flushParagraph();
        closeList();
        code = { language: fence[1] || "", lines: [] };
        continue;
      }
      if (!line.trim()) {
        flushParagraph();
        closeList();
        continue;
      }
      const heading = line.match(/^\s*#{1,6}\s+(.+?)\s*#*\s*$/);
      if (heading) {
        flushParagraph();
        closeList();
        const element = document.createElement("p");
        element.className = "raptor-chat-heading";
        appendInline(element, heading[1]);
        container.append(element);
        continue;
      }
      if (/^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
        flushParagraph();
        closeList();
        container.append(document.createElement("hr"));
        continue;
      }
      const bullet = line.match(/^\s*[-*+•]\s+(.*)$/);
      if (bullet) {
        flushParagraph();
        if (!list || list.type !== "ul") startList("ul");
        const item = document.createElement("li");
        appendInline(item, bullet[1]);
        list.element.append(item);
        continue;
      }
      const ordered = line.match(/^\s*(\d+)[.)]\s+(.*)$/);
      if (ordered) {
        flushParagraph();
        if (!list || list.type !== "ol") startList("ol", Number(ordered[1]));
        const item = document.createElement("li");
        appendInline(item, ordered[2]);
        list.element.append(item);
        continue;
      }
      flushParagraph();
      closeList();
      paragraph.push(line.trim());
    }
    flushCode();
    flushParagraph();
    closeList();
  }

  function makeRow(message) {
    const row = document.createElement("div");
    row.className = `raptor-chat-row ${message.role === "user" ? "user" : "assistant"}`;
    if (message.role !== "user") {
      const mark = document.createElement("span");
      mark.className = "raptor-chat-mark";
      mark.setAttribute("aria-hidden", "true");
      mark.textContent = "✦";
      row.append(mark);
    }
    const bubble = document.createElement("div");
    bubble.className = "raptor-chat-bubble";
    if (message.error) bubble.classList.add("error");
    if (message.role === "user") bubble.textContent = message.content;
    else renderMessageContent(bubble, message.content);
    row.append(bubble);
    return row;
  }

  function renderMessageList() {
    scroll.replaceChildren();
    state.messages.forEach(message => {
      scroll.append(makeRow(message));
      if (message.notice) {
        const notice = document.createElement("div");
        notice.className = "raptor-chat-notice";
        notice.textContent = message.notice;
        scroll.append(notice);
      }
    });
    if (state.typing) {
      const row = document.createElement("div");
      row.className = "raptor-chat-row assistant";
      const mark = document.createElement("span");
      mark.className = "raptor-chat-mark";
      mark.setAttribute("aria-hidden", "true");
      mark.textContent = "✦";
      const bubble = document.createElement("div");
      bubble.className = "raptor-chat-bubble";
      bubble.setAttribute("aria-label", "Raptor AI is typing");
      const dots = document.createElement("span");
      dots.className = "raptor-chat-typing";
      dots.innerHTML = "<span></span><span></span><span></span>";
      bubble.append(dots);
      row.append(mark, bubble);
      scroll.append(row);
    }
    scroll.scrollTop = scroll.scrollHeight;
  }

  function renderSuggestions() {
    suggestions.replaceChildren();
    const hasUserMessage = state.messages.some(message => message.role === "user");
    suggestions.hidden = hasUserMessage || state.busy || !state.suggestions.length;
    if (suggestions.hidden) return;
    state.suggestions.forEach(text => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "raptor-chat-suggest";
      button.textContent = text;
      button.addEventListener("click", () => send(text));
      suggestions.append(button);
    });
  }

  function render() {
    renderMessageList();
    renderSuggestions();
    statusDot.classList.toggle("thinking", state.typing);
    scroll.setAttribute("aria-busy", state.busy ? "true" : "false");
  }

  function updateComposer() {
    const empty = !input.value.trim();
    sendButton.disabled = state.busy || empty;
    input.disabled = state.busy;
    if (state.busy) statusDot.classList.add("thinking");
  }

  function resizeInput() {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 112)}px`;
  }

  function openPanel() {
    root.classList.add("is-open");
    panel.removeAttribute("inert");
    panel.setAttribute("aria-hidden", "false");
    launcher.setAttribute("aria-expanded", "true");
    launcher.setAttribute("aria-label", "Close Raptor AI Assistant");
    input.focus();
    renderMessageList();
  }

  function closePanel() {
    root.classList.remove("is-open");
    panel.setAttribute("aria-hidden", "true");
    panel.setAttribute("inert", "");
    launcher.setAttribute("aria-expanded", "false");
    launcher.setAttribute("aria-label", "Open Raptor AI Assistant");
    launcher.focus();
  }

  async function send(text) {
    const content = String(text || "").trim();
    if (!content || state.busy) return;
    state.busy = true;
    state.messages.push({ role: "user", content });
    state.messages = state.messages.slice(-MAX_STORED_MESSAGES);
    state.typing = true;
    input.value = "";
    statusText.textContent = "Thinking…";
    modeLabel.textContent = "Thinking…";
    resizeInput();
    updateComposer();
    render();
    persist();

    const history = state.messages
      .filter(message => !message.greeting && !message.error && !message.notice && message.content)
      .slice(-MAX_CONTEXT_MESSAGES)
      .map(message => ({ role: message.role, content: message.content }));

    try {
      const headers = { "Content-Type": "application/json", Accept: "application/json" };
      if (state.session.authenticated && state.session.csrf) headers["X-CSRF-Token"] = state.session.csrf;
      const response = await fetch("/api/chat", {
        method: "POST",
        credentials: "same-origin",
        headers,
        body: JSON.stringify({ messages: history }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || "Raptor AI is unavailable right now.");
      if (data.authenticated === false && state.session.authenticated) {
        state.session = { authenticated: false, user: null, csrf: null, permissions: {} };
        state.modeKey = "public";
        state.suggestions = PUBLIC_SUGGESTIONS;
      }
      const answer = typeof data.answer === "string" && data.answer.trim() ? data.answer.trim() : "I didn't receive an answer. Please try again.";
      state.messages.push({ role: "assistant", content: answer, notice: data.notice || "" });
      setMode(data.mode === "openai" ? "openai" : "local");
    } catch (error) {
      state.messages.push({
        role: "assistant",
        content: error.message || "I couldn't reach Raptor AI. Please try again.",
        error: true,
      });
      setMode("error");
    } finally {
      state.typing = false;
      state.busy = false;
      state.messages = state.messages.slice(-MAX_STORED_MESSAGES);
      updateComposer();
      render();
      persist();
      input.focus();
    }
  }

  launcher.addEventListener("click", () => {
    if (root.classList.contains("is-open")) closePanel();
    else openPanel();
  });
  root.querySelector("[data-close]").addEventListener("click", closePanel);
  root.querySelector("[data-reset]").addEventListener("click", resetConversation);
  form.addEventListener("submit", event => {
    event.preventDefault();
    send(input.value);
  });
  input.addEventListener("input", () => {
    resizeInput();
    updateComposer();
  });
  input.addEventListener("keydown", event => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && root.classList.contains("is-open")) closePanel();
  });

  (async function boot() {
    const session = await detectSession();
    configureSession(session);
    const stored = readStored();
    if (stored) {
      state.messages = stored.messages;
      state.mode = stored.mode;
    } else {
      state.messages = [{ role: "assistant", content: state.greeting, greeting: true }];
      state.mode = "ready";
    }
    setMode(state.mode);
    resizeInput();
    updateComposer();
    render();
    persist();
  })();
})();
