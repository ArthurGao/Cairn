"use client";

import { type QueryKey, useMutation, useQueryClient } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { api } from "@/lib/api/client";
import { errorMessage, unwrap } from "@/lib/api/fetch";
import { memoryKeys } from "@/lib/api/queries";

/** Confirm, then undo a change log entry (its whole group); refreshes every memory view. */
export function UndoDialog({
  changeId,
  onClose,
  refresh = [],
  children,
}: {
  changeId: string | null;
  onClose: () => void;
  refresh?: QueryKey[];
  children: ReactNode;
}) {
  const queryClient = useQueryClient();
  const undo = useMutation({
    mutationFn: async (id: string) =>
      unwrap(await api.POST("/api/memory/changelog/{change_id}/undo", { params: { path: { change_id: id } } })),
    onSuccess: async () => {
      onClose();
      await Promise.all([...memoryKeys, ...refresh].map((queryKey) => queryClient.invalidateQueries({ queryKey })));
    },
  });
  return (
    <ConfirmDialog
      open={changeId !== null}
      title="Undo this change"
      confirmLabel="Undo"
      busy={undo.isPending}
      error={undo.isError ? errorMessage(undo.error) : null}
      onCancel={() => {
        onClose();
        undo.reset();
      }}
      onConfirm={() => changeId && undo.mutate(changeId)}
    >
      {children}
    </ConfirmDialog>
  );
}
