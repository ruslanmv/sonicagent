/** Delay before the next resume attempt. The token stays the same; the sequence restarts at 0. */

export function nextDelayMs(attempt: number, baseMs = 200, capMs = 4000): number {
  const safe = Math.max(0, Math.floor(attempt));
  return Math.min(capMs, baseMs * 2 ** safe);
}
