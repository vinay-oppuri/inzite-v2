"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { authClient } from "../lib/auth-client";

type AuthMode = "sign-in" | "sign-up";

type AuthFormProps = {
  mode: AuthMode;
};

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  const isSignUp = mode === "sign-up";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setPending(true);

    try {
      const result = isSignUp
        ? await authClient.signUp.email({
            name,
            email,
            password,
            callbackURL: "/",
          })
        : await authClient.signIn.email({
            email,
            password,
            callbackURL: "/",
          });

      if (result.error) {
        setError(result.error.message ?? "Authentication failed.");
        return;
      }

      router.push("/");
      router.refresh();
    } catch {
      setError("Authentication failed. Please try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6 py-10">
      <section className="w-full max-w-sm rounded-lg border border-border bg-background p-6 shadow-sm">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold">
            {isSignUp ? "Create account" : "Sign in"}
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {isSignUp
              ? "Start saving startup research runs."
              : "Continue to your research dashboard."}
          </p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          {isSignUp ? (
            <label className="block text-sm font-medium">
              Name
              <input
                className="mt-2 w-full rounded-md border border-border bg-background px-3 py-2 outline-none focus:border-foreground"
                autoComplete="name"
                minLength={2}
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
              />
            </label>
          ) : null}

          <label className="block text-sm font-medium">
            Email
            <input
              className="mt-2 w-full rounded-md border border-border bg-background px-3 py-2 outline-none focus:border-foreground"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>

          <label className="block text-sm font-medium">
            Password
            <input
              className="mt-2 w-full rounded-md border border-border bg-background px-3 py-2 outline-none focus:border-foreground"
              type="password"
              autoComplete={isSignUp ? "new-password" : "current-password"}
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>

          {error ? <p className="text-sm text-red-500">{error}</p> : null}

          <button
            className="w-full rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background disabled:cursor-not-allowed disabled:opacity-60"
            disabled={pending}
            type="submit"
          >
            {pending ? "Working..." : isSignUp ? "Sign up" : "Sign in"}
          </button>
        </form>

        <p className="mt-5 text-center text-sm text-muted-foreground">
          {isSignUp ? "Already have an account?" : "Need an account?"}{" "}
          <Link
            className="font-medium text-foreground underline-offset-4 hover:underline"
            href={isSignUp ? "/sign-in" : "/sign-up"}
          >
            {isSignUp ? "Sign in" : "Sign up"}
          </Link>
        </p>
      </section>
    </main>
  );
}
