/** Rendering a plan's goal — a preset race distance or a free km value. */

export const CUSTOM_GOAL = "custom";
export const MARATHON_KM = 42.2;
export const MIN_CUSTOM_DISTANCE_KM = 1;
export const MAX_CUSTOM_DISTANCE_KM = 100;

/** 18.5 → "18,5" in nl, "18.5" in en; 25 → "25" in both. */
export function formatDistance(km: number, locale: string): string {
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(km);
}

/**
 * Label for a plan's goal. Preset goals come from the `goals` message
 * namespace; a custom goal renders as its distance, which has no translation.
 */
export function goalLabel(
  t: (key: string) => string,
  goal: string | null | undefined,
  customDistanceKm: number | null | undefined,
  locale: string,
): string {
  if (!goal) return "—";
  if (goal === CUSTOM_GOAL) {
    return customDistanceKm != null
      ? `${formatDistance(customDistanceKm, locale)} km`
      : t(CUSTOM_GOAL);
  }
  return t(goal);
}

/** "58:40" or "2:12:40" -> seconds; anything else -> undefined. */
export function clockToSeconds(text: string): number | undefined {
  const parts = text.trim().split(":").map(Number);
  if (parts.length < 2 || parts.length > 3 || parts.some((n) => isNaN(n))) return undefined;
  return parts.reduce((total, n) => total * 60 + n, 0);
}

export function isUltra(km: number | null | undefined): boolean {
  return km != null && km > MARATHON_KM;
}
