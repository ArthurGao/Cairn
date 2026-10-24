/** Marks text a model drafted, so a reader knows to check it (design §12.2). */
export function ModelBadge() {
  return (
    <span className="border border-accent px-1.5 py-0.5 text-[11px] uppercase tracking-wide text-accent">
      drafted by model
    </span>
  );
}
