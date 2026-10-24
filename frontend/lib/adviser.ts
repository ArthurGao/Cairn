/** The adviser's typed name, remembered per browser (v1 has no login; design §2). */
const KEY = "cairn.adviser";

export function loadAdviser(): string {
  try {
    return window.localStorage.getItem(KEY) ?? "";
  } catch {
    return "";
  }
}

export function saveAdviser(name: string): void {
  try {
    window.localStorage.setItem(KEY, name);
  } catch {
    // Storage blocked (private window): the name is simply not remembered.
  }
}
