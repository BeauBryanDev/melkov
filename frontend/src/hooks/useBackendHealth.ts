import { useEffect, useState } from "react";
import { getHealth } from "../services/health.service";

/**
 * "checking" is the state before the first answer, not a third kind of
 * outcome. It exists so a page that has just loaded does not flash "Offline"
 * for the half second the first probe takes — the one moment the badge would
 * be both wrong and alarming.
 */
export type BackendHealth = "checking" | "online" | "offline";

/**
 * Poll intervals. Recovery is checked faster than failure: a visitor who
 * arrives while the box is down is waiting for it to come back, and 10s means
 * the badge turns green within a few seconds of the server starting. A
 * healthy backend needs no such urgency, and /health is not rate limited —
 * only /chat and /artwork/read are — but there is still no reason to ask 120
 * times an hour.
 */
const ONLINE_INTERVAL_MS = 30_000;
const OFFLINE_INTERVAL_MS = 10_000;

/**
 * Track whether the Melkov backend is answering.
 *
 * The frontend is a static bundle on Vercel and the backend is a separate box
 * that can be stopped — overnight, between demos, or by a failed deploy. Those
 * two facts together mean the site loads perfectly while Melkov is completely
 * unreachable, and without this the visitor only discovers that by typing a
 * question and waiting for it to fail.
 *
 * Polling stops while the tab is hidden and resumes with an immediate probe
 * when it comes back, so a page left open in a background tab overnight is not
 * quietly making a request every 30 seconds until morning. It also re-probes
 * at once when the browser reports the network returning, since the common
 * case for a false "offline" is the visitor's own connection, not the server.
 */
export function useBackendHealth(): BackendHealth {
  const [health, setHealth] = useState<BackendHealth>("checking");

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let controller: AbortController | undefined;

    const clearTimer = () => {
      if (timer !== undefined) {
        clearTimeout(timer);
        timer = undefined;
      }
    };

    const probe = async () => {
      if (cancelled || document.hidden) {
        return;
      }

      // One probe in flight at a time. Without this, a tab regaining focus
      // while a slow probe is still running would start a second one and the
      // two could resolve out of order, letting a stale result win.
      controller?.abort();
      controller = new AbortController();

      const ok = await getHealth(controller.signal);
      if (cancelled) {
        return;
      }

      setHealth(ok ? "online" : "offline");

      clearTimer();
      timer = setTimeout(probe, ok ? ONLINE_INTERVAL_MS : OFFLINE_INTERVAL_MS);
    };

    const handleVisibility = () => {
      if (document.hidden) {
        clearTimer();
        return;
      }
      void probe();
    };

    void probe();
    document.addEventListener("visibilitychange", handleVisibility);
    window.addEventListener("online", handleVisibility);

    return () => {
      cancelled = true;
      clearTimer();
      controller?.abort();
      document.removeEventListener("visibilitychange", handleVisibility);
      window.removeEventListener("online", handleVisibility);
    };
  }, []);

  return health;
}
