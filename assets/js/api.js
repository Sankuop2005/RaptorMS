window.RaptorAPI = (() => {
  let csrf = null;
  async function request(path, options = {}) {
    const method = (options.method || "GET").toUpperCase();
    const headers = new Headers(options.headers || {});
    if (options.body && typeof options.body !== "string") { headers.set("Content-Type", "application/json"); options.body = JSON.stringify(options.body); }
    if (!["GET", "HEAD", "OPTIONS"].includes(method) && csrf && path !== "/api/login") headers.set("X-CSRF-Token", csrf);
    const response = await fetch(path, { ...options, method, headers, credentials: "same-origin" });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) { const error = new Error(data.error || "Something went wrong."); error.status = response.status; throw error; }
    if (data.csrf) csrf = data.csrf;
    return data;
  }
  async function me() { const data = await request("/api/me"); csrf = data.csrf; return { ...data.user, permissions: data.permissions || {} }; }
  async function login(identity, password) { const data = await request("/api/login", { method: "POST", body: { identity, password } }); csrf = data.csrf; return data.user; }
  async function logout() { return request("/api/logout", { method: "POST", body: {} }); }
  return { request, me, login, logout, setCsrf: value => { csrf = value; } };
})();
