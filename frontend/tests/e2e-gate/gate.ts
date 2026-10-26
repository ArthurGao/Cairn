// The sign-in gate suite's server (playwright.config.ts, project "gate"): its credential and the
// API origin its pages call, which the tests mock.
export const GATE = { user: "gate-user", password: "gate password 123", secret: "gate-secret-0123456789abcdef" };
export const GATE_API = "http://localhost:4799";
