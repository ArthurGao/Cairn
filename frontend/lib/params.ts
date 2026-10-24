"use client";

import { useParams } from "next/navigation";

/** Dynamic route segments, decoded once. `useParams` returns them URL-encoded and the API
 * client encodes path params again, so an id with `:` (cleanup ids carry a timestamp) would
 * otherwise reach the API double-encoded. */
export function useRouteParams<K extends string>(): Record<K, string> {
  const params = useParams<Record<K, string>>();
  return Object.fromEntries(
    Object.entries(params).map(([key, value]) => [key, decodeURIComponent(String(value))]),
  ) as Record<K, string>;
}
