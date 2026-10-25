import { api, type Schemas } from "./client";
import { unwrap } from "./fetch";

/** Query keys and fetchers shared by pages, so invalidation cannot drift. */
export const keys = {
  cases: ["cases"] as const,
  case: (caseId: string) => ["case", caseId] as const,
  check: (caseId: string, checkId: string) => ["check", caseId, checkId] as const,
  checklists: ["checklists"] as const,
  page: (caseId: string, docId: string, n: number) => ["page", caseId, docId, n] as const,
  runs: ["runs"] as const,
  run: (runId: string) => ["run", runId] as const,
  memory: ["memory"] as const,
  memoryDetail: (slug: string) => ["memory", slug] as const,
  context: ["context"] as const,
  skills: ["skills"] as const,
  cleanups: ["cleanups"] as const,
  cleanup: (workflowId: string) => ["cleanup", workflowId] as const,
};

/** Every query a memory write can change (undo, write-back); `memory` prefixes each detail. */
export const memoryKeys = [keys.memory, keys.context] as const;

export async function getCase(caseId: string): Promise<Schemas["CaseDetail"]> {
  return unwrap(await api.GET("/api/cases/{case_id}", { params: { path: { case_id: caseId } } }));
}

export type CheckKind = Schemas["StartCheck"]["kind"];
export type DocSource = Schemas["Document"]["source"];
export type ReviewAction = Schemas["ReviewIn"]["action"];
