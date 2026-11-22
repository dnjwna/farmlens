// Mirrors app/core/phone.py: stored format is +62..., any common input is accepted.

/** "0812-3456 7890" | "+62 812..." | "62812..." -> "6281234567890", or null if invalid. */
function phoneDigits(raw: string): string | null {
  let digits = raw.replace(/\D/g, "");
  if (digits.startsWith("0")) digits = "62" + digits.slice(1);
  return /^628\d{7,11}$/.test(digits) ? digits : null;
}

export const isValidPhone = (raw: string) => phoneDigits(raw) !== null;

/** Canonical form sent to the API: "+6281234567890". Invalid input is returned trimmed. */
export const normalizePhone = (raw: string) => {
  const digits = phoneDigits(raw);
  return digits ? `+${digits}` : raw.trim();
};

/** Familiar local display: "+6281234567890" -> "0812-3456-7890". */
export const formatPhone = (raw: string) => {
  const digits = phoneDigits(raw);
  if (!digits) return raw;
  const local = "0" + digits.slice(2);
  return [local.slice(0, 4), local.slice(4, 8), local.slice(8)].filter(Boolean).join("-");
};
