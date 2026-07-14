/**
 * Single source of truth for backend API URL.
 * Set NEXT_PUBLIC_API_URL in .env.local for production.
 */
const API_BASE =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000")
    : (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000");

export const apiUrl = (path: string): string =>
  `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;