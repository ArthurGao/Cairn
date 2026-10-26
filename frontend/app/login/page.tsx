"use client";

import { useMutation } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { type FormEvent, Suspense, useState } from "react";

import { unwrap, errorMessage } from "@/lib/api/fetch";
import { rememberCredential } from "@/lib/auth/credential";
import { safeNext } from "@/lib/auth/session";

function LoginForm() {
  const next = safeNext(useSearchParams().get("next"));
  const [user, setUser] = useState("");
  const [password, setPassword] = useState("");
  const signIn = useMutation({
    mutationFn: async () => {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user, password }),
      });
      const body: unknown = await response.json().catch(() => undefined);
      return unwrap(response.ok ? { data: body, response } : { error: body, response });
    },
    onSuccess: () => {
      rememberCredential(user, password);
      // A document load, not router.replace: while signed out, the router cached the redirect to
      // /login for every link it prefetched here (the header's /cases), and would reuse it.
      window.location.replace(next);
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    signIn.mutate();
  }

  return (
    <form onSubmit={submit} className="grid gap-4" aria-label="Sign in">
      <label className="grid gap-1 text-sm">
        <span>Username</span>
        <input
          name="username"
          autoComplete="username"
          required
          value={user}
          onChange={(event) => setUser(event.target.value)}
          className="border border-rule px-2 py-1.5"
        />
      </label>
      <label className="grid gap-1 text-sm">
        <span>Password</span>
        <input
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          className="border border-rule px-2 py-1.5"
        />
      </label>
      {signIn.isError && (
        <p role="alert" data-testid="login-error" className="border-l-4 border-bad bg-bad-wash px-3 py-2 text-sm">
          {errorMessage(signIn.error)}
        </p>
      )}
      <button
        type="submit"
        disabled={signIn.isPending}
        className="justify-self-start bg-accent px-3 py-1.5 text-sm text-paper disabled:opacity-40"
      >
        {signIn.isPending ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}

export default function LoginPage() {
  return (
    <section className="grid grid-cols-12 gap-6">
      <div className="col-span-12 grid gap-6 md:col-span-5">
        <header className="border-b border-ink pb-4">
          <p className="text-xs uppercase tracking-wide text-muted">Demo access</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Sign in</h1>
          <p className="mt-2 text-sm text-muted">Use the username and password you were given for this demo.</p>
        </header>
        <Suspense>
          <LoginForm />
        </Suspense>
      </div>
    </section>
  );
}
