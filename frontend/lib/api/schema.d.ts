export interface paths {
    "/api/cases": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Cases */
        get: operations["listCases"];
        put?: never;
        /** Create Case */
        post: operations["createCase"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/cases/{case_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Case */
        get: operations["getCase"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/cases/{case_id}/checks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Start Check */
        post: operations["startCheck"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/cases/{case_id}/checks/{check_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Check */
        get: operations["getCheck"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/cases/{case_id}/checks/{check_id}/findings/{finding_id}/review": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Review Finding */
        post: operations["reviewFinding"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/cases/{case_id}/checks/{check_id}/signoff": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Sign Off */
        post: operations["signOff"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/cases/{case_id}/documents": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Upload Documents */
        post: operations["uploadDocuments"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/cases/{case_id}/documents/{doc_id}/original": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Original */
        get: operations["getOriginal"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/cases/{case_id}/documents/{doc_id}/pages/{n}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Page */
        get: operations["getPage"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/cases/{case_id}/documents/{doc_id}/pages/{n}/render": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Render Page
         * @description A server-side PNG of the page; the browser never opens the original PDF (§13).
         */
        get: operations["renderPage"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/checklists": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Checklists */
        get: operations["listChecklists"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/cleanup": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Cleanups */
        get: operations["listCleanups"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/cleanup/run": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Run Cleanup */
        post: operations["runCleanup"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/cleanup/{workflow_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Cleanup */
        get: operations["getCleanup"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/cleanup/{workflow_id}/review": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Review Cleanup */
        post: operations["reviewCleanup"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/context/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Preview Context */
        get: operations["previewContext"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["getHealth"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/memory": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Memory */
        get: operations["listMemory"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/memory/changelog": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Changelog */
        get: operations["listChangelog"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/memory/changelog/{change_id}/undo": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Undo Change */
        post: operations["undoChange"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/memory/{slug}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Memory */
        get: operations["getMemory"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/runs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Runs */
        get: operations["listRuns"];
        put?: never;
        /** Start Run */
        post: operations["startRun"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/runs/{run_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Run */
        get: operations["getRun"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/skills": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Skills */
        get: operations["listSkills"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/skills/{name}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Skill */
        get: operations["getSkill"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** Accepted */
        Accepted: {
            /**
             * Status
             * @default accepted
             * @constant
             */
            status: "accepted";
        };
        /** AppliedOp */
        AppliedOp: {
            /** After */
            after: string | null;
            /** Before */
            before: string | null;
            /** Change Id */
            change_id: string;
            /** Op */
            op: string;
            /** Slug */
            slug: string;
            /**
             * Undone
             * @default false
             */
            undone: boolean;
        };
        /** AuditEntry */
        AuditEntry: {
            /** Action */
            action: ("confirmed" | "dismissed" | "resolved" | "reopened") | "signed_off";
            /** Adviser */
            adviser: string;
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Check Id */
            check_id: string;
            /** Finding Id */
            finding_id: string | null;
            /** Note */
            note: string | null;
        };
        /** Body_uploadDocuments */
        Body_uploadDocuments: {
            /** Files */
            files: string[];
        };
        /** CallRecord */
        CallRecord: {
            /** Model */
            model: string;
            /**
             * Prompt Version
             * @default
             */
            prompt_version: string;
            /** Role */
            role: string;
            /** Tokens In */
            tokens_in: number;
            /** Tokens Out */
            tokens_out: number;
            /** Vendor */
            vendor: string;
        };
        /** CaseCreate */
        CaseCreate: {
            /** Label */
            label: string;
        };
        /** CaseCreated */
        CaseCreated: {
            /** Case Id */
            case_id: string;
        };
        /** CaseDetail */
        CaseDetail: {
            /** Checks */
            checks: components["schemas"]["CheckBrief"][];
            manifest: components["schemas"]["Manifest"];
        };
        /** CaseSummary */
        CaseSummary: {
            /** Case Id */
            case_id: string;
            /** Checks */
            checks: components["schemas"]["CheckBrief"][];
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /**
             * Data Class
             * @enum {string}
             */
            data_class: "synthetic" | "client";
            /** Documents */
            documents: number;
            /** Label */
            label: string;
        };
        /** ChangeEntry */
        ChangeEntry: {
            /** Actor */
            actor: string;
            /** After */
            after: string | null;
            /**
             * At
             * Format: date-time
             */
            at: string;
            /** Base Hash */
            base_hash: string | null;
            /** Before */
            before: string | null;
            /** Group Id */
            group_id: string;
            /** Id */
            id: string;
            /** Op */
            op: ("create" | "update" | "archive" | "restore") | "index_sync";
            /** Op Id */
            op_id: string;
            /** Reason */
            reason: string;
            /** Slug */
            slug: string;
            /** Undo Of */
            undo_of?: string | null;
        };
        /** CheckBrief */
        CheckBrief: {
            /** Check Id */
            check_id: string;
            /** Checklist Skill */
            checklist_skill: string | null;
            counts: components["schemas"]["CheckCounts"] | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "consistency" | "presubmission";
            signed_off: components["schemas"]["SignOff"] | null;
            /**
             * Started
             * Format: date-time
             */
            started: string;
            /**
             * Status
             * @enum {string}
             */
            status: "running" | "completed" | "failed";
        };
        /** CheckCounts */
        CheckCounts: {
            /**
             * Checked
             * @default 0
             */
            checked: number;
            /**
             * Clean
             * @default false
             */
            clean: boolean;
            /**
             * Conflicts
             * @default 0
             */
            conflicts: number;
            /**
             * Gaps
             * @default 0
             */
            gaps: number;
            /**
             * Pending
             * @default 0
             */
            pending: number;
            /**
             * Unable
             * @default 0
             */
            unable: number;
        };
        /** CheckResult */
        CheckResult: {
            /** Calls */
            calls: components["schemas"]["CallRecord"][];
            /** Case Id */
            case_id: string;
            /** Check Id */
            check_id: string;
            checklist: components["schemas"]["ChecklistRef"] | null;
            /** Conflicts */
            conflicts: components["schemas"]["Conflict"][];
            coverage: components["schemas"]["Coverage"];
            /** Dropped */
            dropped: components["schemas"]["Dropped"][];
            /** Error */
            error: string | null;
            /** Facts */
            facts: components["schemas"]["Fact"][];
            /**
             * Finished
             * Format: date-time
             */
            finished: string;
            /** Gaps */
            gaps: components["schemas"]["Gap"][];
            /** Items */
            items: components["schemas"]["ItemResult"][];
            /**
             * Kind
             * @enum {string}
             */
            kind: "consistency" | "presubmission";
            /**
             * Started
             * Format: date-time
             */
            started: string;
            /**
             * Status
             * @enum {string}
             */
            status: "completed" | "failed";
            /**
             * Wording Replacements
             * @default 0
             */
            wording_replacements: number;
        };
        /** CheckStarted */
        CheckStarted: {
            /** Check Id */
            check_id: string;
        };
        /**
         * CheckState
         * @description `get_state` query result: progress while the check runs.
         */
        CheckState: {
            /** Case Id */
            case_id: string;
            /** Check Id */
            check_id: string;
            /**
             * Documents Done
             * @default 0
             */
            documents_done: number;
            /**
             * Documents Total
             * @default 0
             */
            documents_total: number;
            /** Error */
            error: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "consistency" | "presubmission";
            /**
             * Step
             * @default starting
             * @enum {string}
             */
            step: "starting" | "ingesting" | "extracting" | "comparing" | "checking" | "writing" | "done" | "failed";
            /**
             * Units Done
             * @default 0
             */
            units_done: number;
            /**
             * Units Total
             * @default 0
             */
            units_total: number;
        };
        /** CheckView */
        CheckView: {
            /** Blockers */
            blockers: string[];
            /** Case Id */
            case_id: string;
            /** Check Id */
            check_id: string;
            /** Error */
            error: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "consistency" | "presubmission";
            /** Notes */
            notes: {
                [key: string]: string;
            };
            result: components["schemas"]["CheckResult"] | null;
            /** Review */
            review: {
                [key: string]: "confirmed" | "dismissed" | "resolved" | "reopened";
            };
            signed_off: components["schemas"]["SignOff"] | null;
            state: components["schemas"]["CheckState"] | null;
            /**
             * Status
             * @enum {string}
             */
            status: "running" | "completed" | "failed";
        };
        /** ChecklistRef */
        ChecklistRef: {
            /** Skill */
            skill: string;
            /** Version */
            version: string;
        };
        /** ChecklistView */
        ChecklistView: {
            /** Error */
            error: string | null;
            /** Items */
            items: components["schemas"]["SpecItem"][];
            /** Owner */
            owner: string | null;
            /** Skill */
            skill: string;
            /** Version */
            version: string | null;
            /** Visa */
            visa: string | null;
        };
        /** Citation */
        Citation: {
            /** Doc Id */
            doc_id: string;
            /** Page */
            page: number;
            /** Quote */
            quote: string;
        };
        /** CleanupBrief */
        CleanupBrief: {
            /** Changes */
            changes: number;
            /** Expires */
            expires: string | null;
            /** Started */
            started: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "linting" | "drafting" | "awaiting_review" | "applying" | "applied" | "rejected" | "expired" | "no_changes" | "failed";
            /** Workflow Id */
            workflow_id: string;
        };
        /** CleanupOutcome */
        CleanupOutcome: {
            /** Applied */
            applied: string[];
            /** Rejected */
            rejected: components["schemas"]["RejectedChange"][];
        };
        /**
         * CleanupState
         * @description The `get_state` query result and the API's cleanup view.
         */
        CleanupState: {
            decision: components["schemas"]["ReviewDecision-Output"] | null;
            /** Error */
            error: string | null;
            /** Expires */
            expires: string | null;
            outcome: components["schemas"]["CleanupOutcome"] | null;
            proposal: components["schemas"]["Proposal"] | null;
            /** Started */
            started: string | null;
            /**
             * Status
             * @default linting
             * @enum {string}
             */
            status: "linting" | "drafting" | "awaiting_review" | "applying" | "applied" | "rejected" | "expired" | "no_changes" | "failed";
            /** Workflow Id */
            workflow_id: string;
        };
        /** Conflict */
        Conflict: {
            /**
             * Drafted By
             * @enum {string}
             */
            drafted_by: "model" | "template";
            /** Fact Ids */
            fact_ids: string[];
            /** Finding Id */
            finding_id: string;
            /** Origin */
            origin: ("rule" | "model")[];
            /** Question */
            question: string;
            /** Summary */
            summary: string;
        };
        /** ContextBreakdown */
        ContextBreakdown: {
            /** Agents Md */
            agents_md: number;
            /** Baseline All */
            baseline_all: number;
            /** L0 Total */
            l0_total: number;
            /** Memory Index */
            memory_index: number;
            /** Omitted Index Lines */
            omitted_index_lines: number;
            /** Skill Index */
            skill_index: number;
        };
        /** ContextPreview */
        ContextPreview: {
            breakdown: components["schemas"]["ContextBreakdown"];
            /** Prompt */
            prompt: string;
        };
        /** Coverage */
        Coverage: {
            /** Documents */
            documents: number;
            /** Documents Failed */
            documents_failed: number;
            /**
             * Facts Accepted
             * @default 0
             */
            facts_accepted: number;
            /**
             * Facts Dropped
             * @default 0
             */
            facts_dropped: number;
            /** Pages */
            pages: number;
            /** Pages Transcribed */
            pages_transcribed: number;
            /** Pages Unreadable */
            pages_unreadable: number;
        };
        /** Document */
        Document: {
            /** Bytes */
            bytes: number;
            /** Doc Id */
            doc_id: string;
            /** Error */
            error: string | null;
            /** Filename */
            filename: string;
            /** Media Type */
            media_type: string;
            /** Pages */
            pages: components["schemas"]["PageRef"][];
            /** Sha256 */
            sha256: string;
            /**
             * Status
             * @default pending
             * @enum {string}
             */
            status: "pending" | "ingested" | "failed";
            /** Stored Name */
            stored_name: string;
            /**
             * Uploaded
             * Format: date-time
             */
            uploaded: string;
        };
        /** Dropped */
        Dropped: {
            /** Detail */
            detail: string;
            /** Reason */
            reason: string;
        };
        /** ErrorBody */
        ErrorBody: {
            /** Code */
            code: string;
            /** Message */
            message: string;
        };
        /** ErrorResponse */
        ErrorResponse: {
            error: components["schemas"]["ErrorBody"];
        };
        /**
         * Fact
         * @description A RawFact that passed validation, with its id and document.
         */
        Fact: {
            /** Category */
            category: string;
            /** Doc Id */
            doc_id: string;
            /** Fact Id */
            fact_id: string;
            /** Normalised */
            normalised: string;
            /** Page */
            page: number;
            /** Qualifier */
            qualifier: string | null;
            /** Quote */
            quote: string;
            /** Subject */
            subject: string;
            /** Value */
            value: string;
        };
        /** FileChange */
        FileChange: {
            /** After */
            after: string | null;
            /** Before */
            before: string | null;
            /** Slug */
            slug: string;
        };
        /** Finding */
        Finding: {
            /** Base Hashes */
            base_hashes?: {
                [key: string]: string;
            };
            /** Check */
            check: string;
            /** Message */
            message: string;
            /** Proposed */
            proposed?: ("index_sync" | "archive" | "merge") | null;
            /**
             * Severity
             * @enum {string}
             */
            severity: "error" | "warn" | "info";
            /** Slugs */
            slugs: string[];
        };
        /**
         * Gap
         * @description A document or pages that could not be checked; reviewed like any other finding.
         */
        Gap: {
            /** Doc Id */
            doc_id: string;
            /** Finding Id */
            finding_id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "unreadable" | "failed";
            /** Pages */
            pages: number[];
            /** Reason */
            reason: string;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** HealthOk */
        HealthOk: {
            /** Cases */
            cases: string;
            /**
             * Data Class
             * @enum {string}
             */
            data_class: "synthetic" | "client";
            /** Home */
            home: string;
            /**
             * Status
             * @constant
             */
            status: "ok";
            /**
             * Temporal
             * @constant
             */
            temporal: "ok";
        };
        /** IndexBudget */
        IndexBudget: {
            /** Budget */
            budget: number;
            /** Over */
            over: boolean;
            /** Tokens */
            tokens: number;
        };
        /** ItemResult */
        ItemResult: {
            /** Citations */
            citations: components["schemas"]["Citation"][];
            /** Downgraded */
            downgraded: ("missing" | "no_valid_citation" | "call_failed") | null;
            /** Finding */
            finding: string;
            /** Finding Id */
            finding_id: string;
            /** Item Id */
            item_id: string;
            /**
             * Status
             * @enum {string}
             */
            status: "checked" | "pending" | "unable";
        };
        /** Manifest */
        Manifest: {
            /** Case Id */
            case_id: string;
            /**
             * Created
             * Format: date-time
             */
            created: string;
            /**
             * Data Class
             * @enum {string}
             */
            data_class: "synthetic" | "client";
            /** Documents */
            documents: components["schemas"]["Document"][];
            /** Label */
            label: string;
        };
        /** MemoryDetail */
        MemoryDetail: {
            /** Body */
            body: string;
            /** Changelog */
            changelog: components["schemas"]["ChangeEntry"][];
            /** Slug */
            slug: string;
            /** Text */
            text: string;
        };
        /** MemoryEntry */
        MemoryEntry: {
            /** Created */
            created: string | null;
            /** Description */
            description: string;
            /** Slug */
            slug: string;
            /** Title */
            title: string;
            /** Type */
            type: string;
            usage: components["schemas"]["UsageEntry"];
        };
        /** MemoryList */
        MemoryList: {
            /** Broken */
            broken: string[];
            budget: components["schemas"]["IndexBudget"];
            /** Entries */
            entries: components["schemas"]["MemoryEntry"][];
        };
        /** Page */
        Page: {
            /** Doc Id */
            doc_id: string;
            /**
             * Method
             * @enum {string}
             */
            method: "text" | "transcribed" | "unreadable";
            /** Model */
            model: string | null;
            /** Page */
            page: number;
            /** Reason */
            reason: string | null;
            /** Source Sha256 */
            source_sha256: string;
            /**
             * Text
             * @default
             */
            text: string;
        };
        /** PageRef */
        PageRef: {
            /**
             * Method
             * @enum {string}
             */
            method: "text" | "transcribed" | "unreadable";
            /** N */
            n: number;
        };
        /** Proposal */
        Proposal: {
            /** Changes */
            changes: components["schemas"]["ProposedChange"][];
            /** Findings */
            findings: components["schemas"]["Finding"][];
            /** Mechanical */
            mechanical: string[];
        };
        /**
         * ProposedChange
         * @description One checkbox in the review: an archive, or a whole merge (one op group, §7.3).
         */
        ProposedChange: {
            /** Base Hashes */
            base_hashes: {
                [key: string]: string;
            };
            /** Changes */
            changes: components["schemas"]["FileChange"][];
            /**
             * Kind
             * @enum {string}
             */
            kind: "archive" | "merge";
            /** Op Id */
            op_id: string;
            /** Reason */
            reason: string;
        };
        /** RejectedChange */
        RejectedChange: {
            /** Op Id */
            op_id: string;
            /** Reason */
            reason: string;
        };
        /** RejectedOp */
        RejectedOp: {
            /**
             * Code
             * @enum {string}
             */
            code: "run_limit" | "schema" | "evidence_missing" | "secret" | "personal_data" | "duplicate" | "not_found" | "conflict";
            /** Index */
            index: number;
            /** Reason */
            reason: string;
            /** Slug */
            slug: string;
        };
        /** ReviewDecision */
        "ReviewDecision-Input": {
            /** Approved Op Ids */
            approved_op_ids: string[];
            /**
             * Reviewer
             * @default
             */
            reviewer: string;
            /**
             * Reviewer Note
             * @default
             */
            reviewer_note: string;
        };
        /** ReviewDecision */
        "ReviewDecision-Output": {
            /** Approved Op Ids */
            approved_op_ids: string[];
            /**
             * Reviewer
             * @default
             */
            reviewer: string;
            /**
             * Reviewer Note
             * @default
             */
            reviewer_note: string;
        };
        /** ReviewIn */
        ReviewIn: {
            /**
             * Action
             * @enum {string}
             */
            action: "confirmed" | "dismissed" | "resolved" | "reopened";
            /** Adviser */
            adviser: string;
            /** Note */
            note?: string | null;
        };
        /** RunBrief */
        RunBrief: {
            /** Run Id */
            run_id: string;
            /** Started */
            started: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "running" | "extracting" | "writing" | "completed" | "failed";
            /** Task */
            task: string;
        };
        /** RunStarted */
        RunStarted: {
            /** Run Id */
            run_id: string;
        };
        /**
         * RunState
         * @description The `get_state` query result and the API's run view (design §6.2).
         */
        RunState: {
            /** Answer */
            answer: string | null;
            context: components["schemas"]["ContextBreakdown"] | null;
            /** Error */
            error: string | null;
            /** Loaded */
            loaded: string[];
            /**
             * Loaded Tokens
             * @default 0
             */
            loaded_tokens: number;
            /** Run Id */
            run_id: string;
            /** Started */
            started: string | null;
            /**
             * Status
             * @default running
             * @enum {string}
             */
            status: "running" | "extracting" | "writing" | "completed" | "failed";
            /** Steps */
            steps: components["schemas"]["Step"][];
            /** Task */
            task: string;
            writeback: components["schemas"]["WritebackResult"] | null;
        };
        /** SignOff */
        SignOff: {
            /** Adviser */
            adviser: string;
            /**
             * At
             * Format: date-time
             */
            at: string;
        };
        /** SignOffIn */
        SignOffIn: {
            /** Adviser */
            adviser: string;
        };
        /** SkillDetail */
        SkillDetail: {
            /** Body */
            body: string;
            /** Body Chars */
            body_chars: number;
            /** Description */
            description: string;
            /** Name */
            name: string;
            /** Read Only */
            read_only: boolean;
            /** References */
            references: components["schemas"]["SkillReference"][];
            /** Source */
            source: string;
        };
        /** SkillEntry */
        SkillEntry: {
            /** Body Chars */
            body_chars: number;
            /** Description */
            description: string;
            /** Name */
            name: string;
            /** Read Only */
            read_only: boolean;
            /** References */
            references: components["schemas"]["SkillReference"][];
            /** Source */
            source: string;
        };
        /** SkillReference */
        SkillReference: {
            /** Chars */
            chars: number;
            /** Path */
            path: string;
        };
        /** SpecItem */
        SpecItem: {
            /** Id */
            id: string;
            /** Requirement */
            requirement: string;
            /** Verify */
            verify: string;
        };
        /** StartCheck */
        StartCheck: {
            /** Checklist Skill */
            checklist_skill?: string | null;
            /**
             * Kind
             * @enum {string}
             */
            kind: "consistency" | "presubmission";
        };
        /** StartRun */
        StartRun: {
            /** Max Steps */
            max_steps?: number | null;
            /** Task */
            task: string;
        };
        /** Step */
        Step: {
            /** Arg */
            arg: string | null;
            /**
             * At
             * Format: date-time
             */
            at: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "llm" | "tool";
            /** Model */
            model: string | null;
            /** N */
            n: number;
            /** Result Chars */
            result_chars: number | null;
            /** Role */
            role: string | null;
            /** Tokens */
            tokens: number | null;
            /** Tokens In */
            tokens_in: number | null;
            /** Tokens Out */
            tokens_out: number | null;
            /** Tool */
            tool: string | null;
            /** Truncated */
            truncated: boolean | null;
        };
        /** UsageEntry */
        UsageEntry: {
            /** Last Read */
            last_read: string | null;
            /**
             * Reads
             * @default 0
             */
            reads: number;
            /**
             * Written By Runs
             * @default 0
             */
            written_by_runs: number;
        };
        /** ValidationError */
        ValidationError: {
            /** Context */
            ctx?: Record<string, never>;
            /** Input */
            input?: unknown;
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
        };
        /** WritebackResult */
        WritebackResult: {
            /** Applied */
            applied: components["schemas"]["AppliedOp"][];
            /** Error */
            error: string | null;
            /** Rejected */
            rejected: components["schemas"]["RejectedOp"][];
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    listCases: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CaseSummary"][];
                };
            };
        };
    };
    createCase: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CaseCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CaseCreated"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    getCase: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                case_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CaseDetail"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    startCheck: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                case_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StartCheck"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CheckStarted"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    getCheck: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                case_id: string;
                check_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CheckView"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    reviewFinding: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                case_id: string;
                check_id: string;
                finding_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReviewIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuditEntry"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    signOff: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                case_id: string;
                check_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SignOffIn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuditEntry"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    uploadDocuments: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                case_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_uploadDocuments"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Document"][];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    getOriginal: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                case_id: string;
                doc_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    getPage: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                case_id: string;
                doc_id: string;
                n: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Page"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    renderPage: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                case_id: string;
                doc_id: string;
                n: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "image/png": unknown;
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Request Entity Too Large */
            413: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unsupported Media Type */
            415: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    listChecklists: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ChecklistView"][];
                };
            };
        };
    };
    listCleanups: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CleanupBrief"][];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    runCleanup: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Accepted"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    getCleanup: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                workflow_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CleanupState"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    reviewCleanup: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                workflow_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReviewDecision-Input"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Accepted"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    previewContext: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ContextPreview"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    getHealth: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthOk"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    listMemory: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemoryList"];
                };
            };
        };
    };
    listChangelog: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ChangeEntry"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    undoChange: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                change_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ChangeEntry"][];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    getMemory: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                slug: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MemoryDetail"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    listRuns: {
        parameters: {
            query?: {
                limit?: number;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RunBrief"][];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    startRun: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["StartRun"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RunStarted"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    getRun: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RunState"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
    listSkills: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SkillEntry"][];
                };
            };
        };
    };
    getSkill: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                name: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SkillDetail"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Conflict */
            409: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Unprocessable Entity */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorResponse"];
                };
            };
        };
    };
}
