// Thin fetch wrapper around the FastAPI backend.
async function request(path, options = {}) {
  const csrf = document.cookie
    .split("; ")
    .find((part) => part.startsWith("gradmatch_csrf="))
    ?.split("=")
    .slice(1)
    .join("=");
  const headers = new Headers(options.headers || {});
  if (csrf && !["GET", "HEAD", "OPTIONS"].includes((options.method || "GET").toUpperCase())) {
    headers.set("X-CSRF-Token", decodeURIComponent(csrf));
  }
  const res = await fetch(path, { ...options, headers, credentials: "include" });
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d) => d.msg).join("; ");
    } catch {
      /* non-JSON error body */
    }
    const error = new Error(message);
    error.status = res.status;
    throw error;
  }
  return res.status === 204 ? null : res.json();
}

const json = (method, body) => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  // auth
  authMe: () => request("/api/auth/me"),
  register: (email, password) => request("/api/auth/register", json("POST", { email, password })),
  login: (email, password) => request("/api/auth/login", json("POST", { email, password })),
  logout: () => request("/api/auth/logout", { method: "POST" }),
  forgotPassword: (email) => request("/api/auth/forgot-password", json("POST", { email })),
  resetPassword: (token, password) => request("/api/auth/reset-password", json("POST", { token, password })),

  // meta
  health: () => request("/api/health"),
  metaStats: () => request("/api/meta/stats"),
  integrations: () => request("/api/meta/integrations"),
  seedDemo: () => request("/api/meta/seed", { method: "POST" }),

  // catalogue
  countries: () => request("/api/countries"),
  universities: (codes = []) => {
    const qs = codes.map((c) => `country=${encodeURIComponent(c)}`).join("&");
    return request(`/api/universities${qs ? `?${qs}` : ""}`);
  },

  // student
  myStudent: () => request("/api/students/mine"),
  getStudent: (id) => request(`/api/students/${id}`),
  uploadResume: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/api/students", { method: "POST", body: form });
  },
  updateStudent: (id, data) => request(`/api/students/${id}`, json("PUT", data)),
  deleteStudent: (id) => request(`/api/students/${id}`, { method: "DELETE" }),

  // matching
  recommend: (id, data) => request(`/api/students/${id}/recommendations`, json("POST", data)),
  latestRecommendations: (id) => request(`/api/students/${id}/recommendations`),
  getRun: (id, runId) => request(`/api/students/${id}/recommendations/${runId}`),
  runs: (id) => request(`/api/students/${id}/runs`),
  overview: (id) => request(`/api/students/${id}/overview`),

  // professors
  emailLookup: (profId, pageUrl) =>
    request(`/api/professors/${profId}/email-lookup`, json("POST", { page_url: pageUrl })),
  confirmEmail: (profId, email, sourceUrl) =>
    request(`/api/professors/${profId}/email`, json("PUT", { email, source_url: sourceUrl })),
  clearEmail: (profId) => request(`/api/professors/${profId}/email`, { method: "DELETE" }),

  // outreach
  outreach: (studentId) => request(`/api/students/${studentId}/outreach`),
  outreachStats: (studentId) => request(`/api/students/${studentId}/outreach/stats`),
  updateOutreach: (id, data) => request(`/api/outreach/${id}`, json("PATCH", data)),
  outreachEvents: (id) => request(`/api/outreach/${id}/events`),
  outreachDraft: (id) => request(`/api/outreach/${id}/draft`),
  outreachDraftAi: (id) => request(`/api/outreach/${id}/draft`, { method: "POST" }),
};

export const STATUS_LABELS = {
  not_started: "Not started",
  draft_ready: "Draft ready",
  sent: "Email sent",
  replied: "Reply received",
  follow_up_needed: "Follow up",
  closed: "Closed",
};

export const STATUS_ORDER = [
  "not_started",
  "draft_ready",
  "sent",
  "follow_up_needed",
  "replied",
  "closed",
];

export const COUNTRY_META = {
  CA: { name: "Canada", flag: "🇨🇦" },
  US: { name: "United States", flag: "🇺🇸" },
  GB: { name: "United Kingdom", flag: "🇬🇧" },
  DE: { name: "Germany", flag: "🇩🇪" },
  NL: { name: "Netherlands", flag: "🇳🇱" },
  FR: { name: "France", flag: "🇫🇷" },
};
