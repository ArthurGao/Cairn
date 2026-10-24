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
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
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
}
