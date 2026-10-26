import createClient from "openapi-fetch";

import { credentialMiddleware } from "@/lib/auth/credential";

import type { components, paths } from "./schema";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4700";

export const api = createClient<paths>({ baseUrl: API_URL });
api.use(credentialMiddleware());

export type Schemas = components["schemas"];
