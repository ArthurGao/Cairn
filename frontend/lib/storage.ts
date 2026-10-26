/** Per-browser settings in localStorage. Blocked storage (private window) reads as unset. */

export function readLocal(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function writeLocal(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Storage blocked: the value is simply not remembered.
  }
}
