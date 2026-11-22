/**
 * The API stores naive UTC timestamps (datetime.utcnow) and serialises them
 * without a timezone suffix. Without the "Z", browsers would read them as local
 * time and every date would be 7 hours off in WIB.
 */
export function parseServerDate(value: string): Date {
  const hasZone = /([zZ]|[+-]\d{2}:?\d{2})$/.test(value);
  return new Date(hasZone ? value : `${value}Z`);
}

/** Old records stored a local path (e.g. "uploaded/x.jpg") instead of a URL. */
export const isDisplayableImage = (url: string | null | undefined): url is string => !!url && /^https?:\/\//.test(url);

export function formatDate(value: string): string {
  return parseServerDate(value).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" });
}

export function formatDateTime(value: string): string {
  return parseServerDate(value).toLocaleString("id-ID", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatRelativeDay(value: string): string {
  const date = parseServerDate(value);
  const startOf = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((startOf(new Date()) - startOf(date)) / 86_400_000);
  const time = date.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
  if (days === 0) return `Hari ini, ${time}`;
  if (days === 1) return `Kemarin, ${time}`;
  return date.toLocaleDateString("id-ID", { day: "numeric", month: "short", year: "numeric" });
}
