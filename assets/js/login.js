(() => {
  const form = document.querySelector("#login-form"), err = document.querySelector("#login-error"), submit = document.querySelector("#login-submit"), pass = document.querySelector("#password"), toggle = document.querySelector("#password-toggle");
  window.RaptorAPI.me().then(user => { location.href = user.role === "admin" ? "/admin" : "/dashboard"; }).catch(() => {});
  toggle.addEventListener("click", () => { const showing = pass.type === "text"; pass.type = showing ? "password" : "text"; toggle.setAttribute("aria-label", showing ? "Show password" : "Hide password"); });
  form.addEventListener("submit", async event => {
    event.preventDefault(); err.textContent = "";
    if (!form.reportValidity()) return;
    submit.disabled = true; submit.textContent = "Signing in…";
    try { const user = await window.RaptorAPI.login(form.identity.value.trim(), form.password.value); location.href = user.role === "admin" ? "/admin" : "/dashboard"; }
    catch (error) { err.textContent = error.message; submit.disabled = false; submit.textContent = "Login"; }
  });
})();
