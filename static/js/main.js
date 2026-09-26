// ===== Theme toggle =====
(function () {
  const html = document.documentElement;
  const saved = localStorage.getItem("theme") || "light";
  html.setAttribute("data-bs-theme", saved);

  document.addEventListener("click", (e) => {
    if (e.target.closest("#themeToggle")) {
      const cur = html.getAttribute("data-bs-theme");
      const next = cur === "dark" ? "light" : "dark";
      html.setAttribute("data-bs-theme", next);
      localStorage.setItem("theme", next);
      const icon = document.querySelector("#themeToggle i");
      if (icon) icon.className = next === "dark" ? "bi bi-sun" : "bi bi-moon-stars";
    }
  });
})();

// ===== Mobile sidebar toggle =====
document.addEventListener("click", (e) => {
  if (e.target.closest("#sidebarToggle")) {
    document.getElementById("sidebar").classList.toggle("show");
  }
});

// ===== CSRF helper =====
function csrf() {
  const el = document.querySelector('input[name="csrf_token"]');
  return el ? el.value : "";
}

// ===== Like button =====
document.addEventListener("click", async (e) => {
  const btn = e.target.closest(".like-btn");
  if (!btn) return;
  const id = btn.dataset.video;
  const res = await fetch(`/video/${id}/like`, {
    method: "POST",
    headers: { "X-CSRFToken": csrf() },
  });
  if (res.status === 401) { location.href = "/login"; return; }
  const data = await res.json();
  document.getElementById("likeCount").textContent = data.count;
  btn.classList.toggle("active", data.state === "liked");
});

// ===== Watch later =====
document.addEventListener("click", async (e) => {
  const btn = e.target.closest(".wl-btn");
  if (!btn) return;
  const id = btn.dataset.video;
  const res = await fetch(`/watch-later/toggle/${id}`, {
    method: "POST",
    headers: { "X-CSRFToken": csrf() },
  });
  if (res.status === 401) { location.href = "/login"; return; }
  const data = await res.json();
  const icon = btn.querySelector("i");
  icon.className = data.state === "added" ? "bi bi-bookmark-fill" : "bi bi-bookmark";
});

// ===== Subscribe =====
document.addEventListener("click", async (e) => {
  const btn = e.target.closest(".subscribe-btn");
  if (!btn) return;
  const username = btn.dataset.username;
  const res = await fetch(`/channel/${username}/subscribe`, {
    method: "POST",
    headers: { "X-CSRFToken": csrf() },
  });
  if (res.status === 401) { location.href = "/login"; return; }
  const data = await res.json();
  if (data.state === "subscribed") {
    btn.textContent = "Subscribed";
    btn.classList.remove("btn-danger");
    btn.classList.add("btn-outline-secondary");
  } else {
    btn.textContent = "Subscribe";
    btn.classList.add("btn-danger");
    btn.classList.remove("btn-outline-secondary");
  }
});