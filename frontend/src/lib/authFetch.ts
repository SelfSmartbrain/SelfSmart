import { apiUrl } from "@/lib/api";

/**
 * Authenticated fetch wrapper.
 *
 * Reads the JWT token from localStorage, attaches it as an
 * `Authorization: Bearer` header, and auto-logs the user out on 401.
 *
 * For endpoints that don't require auth (e.g. /status), use plain `fetch`.
 */
export async function authFetch(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;

  const headers = new Headers(options.headers);

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  // Default Content-Type for requests with a body (unless already set)
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(apiUrl(path), { ...options, headers });

  // If the backend rejects us, force a re-login
  if (response.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
      window.dispatchEvent(new Event("logout-trigger"));
    }
  }

  return response;
}
