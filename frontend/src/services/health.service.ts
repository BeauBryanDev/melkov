import { api } from "./api";

/**
 * A health probe must not inherit the shared 240s chat timeout.
 *
 * That timeout exists so a cold ZeroGPU turn is not aborted while it is still
 * working. Applied to /health it would do the opposite of what this endpoint
 * is for: with the backend down, the probe would hang for four minutes before
 * reporting it, and the status badge would sit on "checking" for the whole
 * time. /health is a dictionary lookup — if it has not answered in a few
 * seconds, it is not going to.
 */
const HEALTH_TIMEOUT_MS = 8_000;

/**
 * Ask the backend whether it is up.
 *
 * Never throws: a refused connection, a DNS failure, a timeout and a 5xx are
 * all simply "not online" to the caller. The distinction matters to a
 * developer reading the network tab, not to a visitor reading a badge.
 *
 * @param signal - Aborts the probe when the caller goes away, so an unmounted
 *   component does not leave a request in flight. An aborted probe resolves
 *   false and the caller is expected to ignore it.
 */
export async function getHealth(signal?: AbortSignal): Promise<boolean> {
  try {
    await api.get("/health", { timeout: HEALTH_TIMEOUT_MS, signal });
    return true;
  } catch {
    return false;
  }
}
