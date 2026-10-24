"use client";

import { type ReactNode, useEffect, useId, useRef, useState } from "react";

/** The app's confirmation dialog; never window.confirm (frontend/AGENTS.md). */
export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel,
  noteLabel,
  noteRequired = false,
  busy = false,
  error,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  children?: ReactNode;
  confirmLabel: string;
  noteLabel?: string;
  noteRequired?: boolean;
  busy?: boolean;
  error?: string | null;
  onConfirm: (note: string) => void;
  onCancel: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const noteId = useId();
  const [note, setNote] = useState("");

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      setNote("");
      dialog.showModal();
    }
    if (!open && dialog.open) dialog.close();
  }, [open]);

  const blocked = busy || (noteRequired && note.trim() === "");
  return (
    <dialog
      ref={ref}
      onCancel={(event) => {
        event.preventDefault();
        onCancel();
      }}
      aria-labelledby={`${noteId}-title`}
      className="m-auto w-full max-w-lg border border-ink p-0 backdrop:bg-ink/30"
    >
      <form
        method="dialog"
        className="grid gap-4 p-6"
        onSubmit={(event) => {
          event.preventDefault();
          if (!blocked) onConfirm(note.trim());
        }}
      >
        <h2 id={`${noteId}-title`} className="text-base font-semibold">
          {title}
        </h2>
        {children && <div className="text-sm">{children}</div>}
        {noteLabel && (
          <label htmlFor={noteId} className="grid gap-1 text-sm">
            <span>
              {noteLabel}
              {noteRequired ? " (required)" : " (optional)"}
            </span>
            <textarea
              id={noteId}
              value={note}
              onChange={(event) => setNote(event.target.value)}
              rows={3}
              className="border border-rule p-2 font-sans"
            />
          </label>
        )}
        {error && (
          <p role="alert" className="border-l-4 border-bad bg-bad-wash px-3 py-2 text-sm">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-3">
          <button type="button" onClick={onCancel} className="border border-rule px-3 py-1.5 text-sm">
            Cancel
          </button>
          <button
            type="submit"
            disabled={blocked}
            className="bg-accent px-3 py-1.5 text-sm text-paper disabled:opacity-40"
          >
            {busy ? "Saving…" : confirmLabel}
          </button>
        </div>
      </form>
    </dialog>
  );
}
