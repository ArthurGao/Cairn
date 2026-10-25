"use client";

import { useId, useState } from "react";

/** Drag-and-drop area that also works with the keyboard through a normal file input. */
export function Upload({
  busy,
  onFiles,
  what = "PDF, PNG, JPEG, text or Markdown; synthetic documents only.",
  testId = "file-input",
}: {
  busy: boolean;
  onFiles: (files: File[]) => void;
  what?: string;
  testId?: string;
}) {
  const id = useId();
  const [over, setOver] = useState(false);
  return (
    <div
      onDragOver={(event) => {
        event.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(event) => {
        event.preventDefault();
        setOver(false);
        const files = Array.from(event.dataTransfer.files);
        if (files.length && !busy) onFiles(files);
      }}
      className={`border border-dashed px-4 py-5 text-sm ${over ? "border-accent bg-accent-wash" : "border-rule"}`}
    >
      <label htmlFor={id} className="cursor-pointer">
        <span className="font-medium text-accent underline">Choose files</span> or drop them here. {what}
      </label>
      <input
        id={id}
        type="file"
        multiple
        disabled={busy}
        accept=".pdf,.png,.jpg,.jpeg,.txt,.md"
        className="sr-only"
        data-testid={testId}
        onChange={(event) => {
          const files = Array.from(event.target.files ?? []);
          if (files.length) onFiles(files);
          event.target.value = "";
        }}
      />
      {busy && <p className="mt-2 text-muted">Uploading…</p>}
    </div>
  );
}
