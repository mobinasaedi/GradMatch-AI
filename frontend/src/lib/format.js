export const FLAGS = {
  CA: "🇨🇦",
  US: "🇺🇸",
  GB: "🇬🇧",
  DE: "🇩🇪",
  NL: "🇳🇱",
  FR: "🇫🇷",
};

export function flag(code) {
  return FLAGS[(code || "").toUpperCase()] || "🌐";
}

export function initials(name = "") {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  const first = parts[0][0] || "";
  const last = parts.length > 1 ? parts[parts.length - 1][0] : "";
  return (first + last).toUpperCase();
}

export function shortDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
}

export function dateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function relative(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  const diff = Date.now() - date.getTime();
  const minutes = Math.round(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days} d ago`;
  return shortDate(value);
}

export function band(fit) {
  if (fit >= 85) return { key: "excellent", label: "Excellent match" };
  if (fit >= 70) return { key: "strong", label: "Strong match" };
  if (fit >= 55) return { key: "good", label: "Good match" };
  return { key: "exploratory", label: "Worth exploring" };
}

export function truncate(text, max = 120) {
  if (!text) return "";
  return text.length <= max ? text : `${text.slice(0, max - 1)}…`;
}
