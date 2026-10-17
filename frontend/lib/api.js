// Small fetch wrapper. All calls go to the same origin (Next.js proxies them to FastAPI),
// so the HttpOnly kavach_sid cookie is sent automatically.

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export async function api(path, opts = {}) {
  const res = await fetch(path, {
    method: opts.method ?? "GET",
    credentials: "include",
    cache: "no-store",
    headers: {
      ...(opts.body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...opts.headers,
    },
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  });
  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    const detail = data?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => (d.msg ? d.msg.replace(/^Value error,\s*/i, "") : "Invalid input")).join(". ")
          : `Request failed (${res.status})`;
    throw new ApiError(message, res.status);
  }
  return data;
}

/** Navigate to a URL returned by the backend: internal paths stay in the app, website URLs leave it. */
export function go(url, push) {
  if (/^https?:\/\//i.test(url)) window.location.href = url;
  else push(url);
}
