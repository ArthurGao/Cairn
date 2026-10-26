"use client";

import { type ReactNode, useEffect, useRef, useSyncExternalStore } from "react";

import { readLocal, writeLocal } from "@/lib/storage";

// First-use hints: the next thing to click on a page pulses with a short label until it has been
// clicked once in this browser. Hints can be chained with `after`, so a page shows one at a time,
// and when several enabled elements share an id (a list), only the first on the page carries it.

const KEY = (id: string) => `cairn.guide.${id}`;

// One store for every hint on the page: which ids are done (read from storage once), which
// elements are enabled per id, and a version that changes once per batch of changes.
const done = new Map<string, boolean>();
const registered = new Map<string, Set<HTMLElement>>();
const listeners = new Set<() => void>();
let version = 0;
let pending = false;

function notify(): void {
  if (pending) return;
  pending = true;
  queueMicrotask(() => {
    pending = false;
    version += 1;
    for (const listener of listeners) listener();
  });
}

function isDone(id: string): boolean {
  if (!done.has(id)) done.set(id, readLocal(KEY(id)) === "done");
  return done.get(id)!;
}

function markDone(id: string): void {
  done.set(id, true);
  writeLocal(KEY(id), "done");
  notify();
}

function isFirst(id: string, element: HTMLElement): boolean {
  for (const other of registered.get(id) ?? []) {
    if (other !== element && other.compareDocumentPosition(element) & Node.DOCUMENT_POSITION_FOLLOWING) return false;
  }
  return true;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function Guide({
  id,
  hint,
  after,
  block = false,
  enabled = true,
  className = "",
  children,
}: {
  id: string;
  hint: string;
  after?: string;
  block?: boolean;
  /** False keeps the element out of the hint (e.g. a finding already reviewed). */
  enabled?: boolean;
  className?: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLElement | null>(null);
  // The server snapshot is -1 so nothing is active before mount: only the browser knows what
  // was clicked, and the page order is only known in the DOM.
  const mounted = useSyncExternalStore(subscribe, () => version, () => -1) >= 0;

  useEffect(() => {
    const element = ref.current;
    if (!enabled || !element) return;
    const set = registered.get(id) ?? new Set();
    registered.set(id, set.add(element));
    notify();
    return () => {
      set.delete(element);
      notify();
    };
  }, [id, enabled]);

  const element = ref.current;
  const active =
    mounted && enabled && element !== null && !isDone(id) && (!after || isDone(after)) && isFirst(id, element);
  return (
    <span
      ref={ref}
      data-guide={id}
      onClickCapture={() => active && markDone(id)}
      className={`${block ? "guide-block" : "guide-inline"} ${active ? "guide-on" : ""} ${className}`}
    >
      {children}
      {active && (
        <span className="guide-tag" data-testid="guide-hint">
          {hint}
        </span>
      )}
    </span>
  );
}
