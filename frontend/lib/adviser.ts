import { readLocal, writeLocal } from "@/lib/storage";

/** The adviser's typed name, remembered per browser (v1 has no login; design §2). */
const KEY = "cairn.adviser";

export function loadAdviser(): string {
  return readLocal(KEY) ?? "";
}

export function saveAdviser(name: string): void {
  writeLocal(KEY, name);
}
