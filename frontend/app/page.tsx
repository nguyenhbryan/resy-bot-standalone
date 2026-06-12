import { createHash } from "crypto";
import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

function getAccessToken() {
  const accessKey = process.env.ACCESS_KEY?.trim();

  if (!accessKey) {
    return null;
  }

  return createHash("sha256").update(accessKey).digest("hex");
}

async function verifyKey(formData: FormData) {
  "use server";

  const submittedKey = String(formData.get("key") ?? "").trim();
  const accessToken = getAccessToken();

  if (!accessToken || submittedKey !== process.env.ACCESS_KEY?.trim()) {
    redirect("/?error=1");
  }

  const cookieStore = await cookies();

  cookieStore.set("resy_access", accessToken, {
    httpOnly: true,
    maxAge: 60 * 60 * 8,
    path: "/",
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
  });

  redirect("/ssr");
}

export default async function Home({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const accessToken = getAccessToken();
  const cookieStore = await cookies();
  const userToken = cookieStore.get("resy_access")?.value;

  if (accessToken && userToken === accessToken) {
    redirect("/ssr");
  }

  const params = await searchParams;
  const hasError = params?.error === "1";

  return (
    <main className="flex min-h-screen items-center justify-center bg-neutral-950 px-6 text-neutral-50">
      <section className="w-full max-w-sm">
        <div className="mb-8">
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-emerald-300">
            Resy Bot
          </p>
          <h1 className="mt-3 text-3xl font-semibold tracking-normal">
            Enter access key
          </h1>
        </div>

        <form action={verifyKey} className="space-y-4">
          <div className="space-y-2">
            <label htmlFor="key" className="text-sm font-medium text-neutral-200">
              Key
            </label>
            <input
              id="key"
              name="key"
              type="password"
              autoComplete="current-password"
              required
              className="h-11 w-full rounded-md border border-neutral-700 bg-neutral-900 px-3 text-base text-neutral-50 outline-none transition focus:border-emerald-300 focus:ring-2 focus:ring-emerald-300/20"
            />
          </div>

          {hasError ? (
            <p className="text-sm font-medium text-red-300">
              That key did not match. Try again.
            </p>
          ) : null}

          <button
            type="submit"
            className="h-11 w-full rounded-md bg-emerald-300 px-4 text-sm font-semibold text-neutral-950 transition hover:bg-emerald-200 focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:ring-offset-2 focus:ring-offset-neutral-950"
          >
            Continue
          </button>

          <Link
            href="/demo"
            className="flex h-11 w-full items-center justify-center rounded-md border border-neutral-700 px-4 text-sm font-semibold text-neutral-100 transition hover:border-emerald-300 hover:text-emerald-200 focus:outline-none focus:ring-2 focus:ring-emerald-300 focus:ring-offset-2 focus:ring-offset-neutral-950"
          >
            View Demo
          </Link>
        </form>
      </section>
    </main>
  );
}
