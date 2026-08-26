/** Cliente HTTP API VigiEPP. */
export function createApi({ onUnauthorized } = {}) {
  return async function api(path, options = {}, timeoutMs = 20000) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const headers = { ...(options.headers || {}) };
      const token = sessionStorage.getItem("vigiepp.token");
      if (token && !headers["X-VigiEPP-Key"] && !headers.Authorization) {
        headers["X-VigiEPP-Key"] = token;
      }
      const res = await fetch(path, {
        ...options,
        headers,
        credentials: "include",
        signal: ctrl.signal,
      });
      if (res.status === 401 && !path.startsWith("/api/auth/") && onUnauthorized) {
        await onUnauthorized(path);
      }
      const data = await res.json().catch(() => ({}));
      if (res.status === 503 && data && (data.booting || data.error)) {
        return { ...data, ok: false, _http: 503 };
      }
      if (!res.ok && res.status !== 202) {
        if (res.status === 429) {
          return { ok: false, busy: true, error: data.error || "IA ocupada", _http: 429 };
        }
        if (res.status === 502 || res.status === 503) {
          if (/\/api\/detect|\/api\/identity\/identify/.test(path)) {
            return {
              ok: false,
              down: true,
              _http: res.status,
              error: "Servidor ocupado. Reintentando…",
            };
          }
          throw new Error(
            res.status === 502 ? "Servidor ocupado. Esperá 15 s." : data.error || "Servidor no listo"
          );
        }
        const detail = data.detail || data.error || `HTTP ${res.status}`;
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      return data;
    } catch (err) {
      if (err.name === "AbortError") {
        throw new Error("Tiempo agotado (servidor lento o IA cargando). Esperá 10 s y reintentá.");
      }
      throw err;
    } finally {
      clearTimeout(timer);
    }
  };
}
