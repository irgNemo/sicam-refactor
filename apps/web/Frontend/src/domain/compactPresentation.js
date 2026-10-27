// Display only: never use these strings as identifiers in requests/state.
export function compactIdentifier(value, peers = []) {
  const text = String(value ?? '');
  if (text.length <= 18) return text;
  let suffix = 6;
  const others = peers.map(v => String(v ?? '')).filter(v => v !== text);
  while (suffix < text.length && others.some(v => v.endsWith(text.slice(-suffix)))) suffix++;
  return suffix >= text.length - 1 ? text : `…${text.slice(-suffix)}`;
}

export function compactFilename(value) {
  const text = String(value ?? '');
  return text.length <= 26 ? text : `${text.slice(0, 8)}…${text.slice(-10)}`;
}

export const countLabel = (count, singular, plural) => `${count} ${count === 1 ? singular : plural}`;
