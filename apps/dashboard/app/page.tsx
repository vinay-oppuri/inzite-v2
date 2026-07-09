import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { auth } from "../lib/auth";
import SignOutButton from "../components/sign-out-button";

export default async function Home() {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session) {
    redirect("/sign-in");
  }

  return (
    <main className="min-h-screen px-6 py-8">
      <header className="mx-auto flex w-full max-w-5xl items-center justify-between border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-semibold">Inzite Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Signed in as {session.user.email}
          </p>
        </div>
        <SignOutButton />
      </header>

      <section className="mx-auto mt-8 w-full max-w-5xl">
        <h2 className="text-lg font-semibold">Research workspace</h2>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Your saved startup research runs will appear here.
        </p>
      </section>
    </main>
  );
}
