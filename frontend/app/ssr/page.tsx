import { createHash } from "crypto";
import { Buffer } from "buffer";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

type ApiSlot = {
  config: {
    id: string;
    type: string;
    token: string;
  };
  date: {
    start: string;
    end: string;
  };
};

type JobStatus =
  | "pending"
  | "running"
  | "cancelling"
  | "cancelled"
  | "succeeded"
  | "failed";

type ReservationJob = {
  id: string;
  status: JobStatus;
  reservation_token?: string | null;
  error?: string | null;
};

const apiBaseUrl = process.env.FASTAPI_URL ?? "http://127.0.0.1:8000";

function getAccessToken() {
  const accessKey = process.env.ACCESS_KEY?.trim();

  if (!accessKey) {
    return null;
  }

  return createHash("sha256").update(accessKey).digest("hex");
}

function getText(formData: FormData, key: string) {
  return String(formData.get(key) ?? "").trim();
}

function getNumber(formData: FormData, key: string) {
  return Number(getText(formData, key));
}

function buildReservationRequest(formData: FormData) {
  const preferredType = getText(formData, "preferred_type");
  const idealDate = getText(formData, "ideal_date");
  const daysInAdvance = getText(formData, "days_in_advance");

  if (!idealDate && !daysInAdvance) {
    throw new Error("Choose either a reservation date or days in advance.");
  }

  if (idealDate && daysInAdvance) {
    throw new Error("Use either reservation date or days in advance, not both.");
  }

  return {
    venue_id: getText(formData, "venue_id"),
    party_size: getNumber(formData, "party_size"),
    ideal_hour: getNumber(formData, "ideal_hour"),
    ideal_minute: getNumber(formData, "ideal_minute"),
    window_hours: getNumber(formData, "window_hours"),
    prefer_early: formData.get("prefer_early") === "on",
    preferred_type: preferredType || null,
    ideal_date: idealDate || null,
    days_in_advance: idealDate || !daysInAdvance ? null : Number(daysInAdvance),
    method: getText(formData, "method"),
  };
}

function encodeState(value: unknown) {
  return Buffer.from(JSON.stringify(value), "utf8").toString("base64url");
}

function decodeSlots(value?: string | string[]) {
  if (!value || Array.isArray(value)) {
    return [];
  }

  try {
    return JSON.parse(Buffer.from(value, "base64url").toString("utf8")) as ApiSlot[];
  } catch {
    return [];
  }
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let message = `FastAPI returned ${response.status}`;

    try {
      const body = (await response.json()) as { detail?: unknown };
      message = formatApiDetail(body.detail) ?? message;
    } catch {}

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

function formatApiDetail(detail: unknown) {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String(item.msg);
        }

        return String(item);
      })
      .join(" ");
  }

  return null;
}

async function checkSlots(formData: FormData) {
  "use server";

  let nextPath = "/ssr";

  try {
    const body = buildReservationRequest(formData);
    const response = await apiRequest<{ slots: ApiSlot[] }>("/slots", {
      method: "POST",
      body: JSON.stringify(body),
    });

    nextPath = `/ssr?slots=${encodeState(response.slots)}`;
  } catch (error) {
    nextPath = `/ssr?error=${encodeURIComponent((error as Error).message)}`;
  }

  redirect(nextPath);
}

async function createReservation(formData: FormData) {
  "use server";

  let nextPath = "/ssr";

  try {
    const body = {
      reservation_request: buildReservationRequest(formData),
      expected_drop_hour: getNumber(formData, "expected_drop_hour"),
      expected_drop_minute: getNumber(formData, "expected_drop_minute"),
    };
    const response = await apiRequest<{ job_id: string }>("/reserve", {
      method: "POST",
      body: JSON.stringify(body),
    });

    nextPath = `/ssr?job=${response.job_id}`;
  } catch (error) {
    nextPath = `/ssr?error=${encodeURIComponent((error as Error).message)}`;
  }

  redirect(nextPath);
}

async function cancelJob(formData: FormData) {
  "use server";

  const jobId = getText(formData, "job_id");
  let nextPath = `/ssr?job=${encodeURIComponent(jobId)}`;

  try {
    await apiRequest<ReservationJob>(`/jobs/${jobId}/cancel`, {
      method: "POST",
    });
  } catch (error) {
    nextPath = `/ssr?job=${encodeURIComponent(jobId)}&error=${encodeURIComponent(
      (error as Error).message,
    )}`;
  }

  redirect(nextPath);
}

async function getHealth() {
  try {
    await apiRequest<{ status: string }>("/health");
    return "online";
  } catch {
    return "offline";
  }
}

async function getJob(jobId?: string | string[]) {
  if (!jobId || Array.isArray(jobId)) {
    return null;
  }

  try {
    return apiRequest<ReservationJob>(`/jobs/${jobId}`);
  } catch {
    return null;
  }
}

export default async function SsrPage({
  searchParams,
}: {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}) {
  const accessToken = getAccessToken();
  const cookieStore = await cookies();
  const userToken = cookieStore.get("resy_access")?.value;

  if (!accessToken || userToken !== accessToken) {
    redirect("/");
  }

  const params = await searchParams;
  const slots = decodeSlots(params?.slots);
  const job = await getJob(params?.job);
  const health = await getHealth();
  const error = typeof params?.error === "string" ? params.error : null;
  const apiOffline = health === "offline";
  const canCancel =
    job?.status === "pending" ||
    job?.status === "running" ||
    job?.status === "cancelling";

  return (
    <main className="min-h-screen bg-neutral-50 px-5 py-6 text-neutral-950 sm:px-8">
      <section className="mx-auto grid w-full max-w-6xl gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
        <div>
          <div className="mb-6 flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.2em] text-emerald-700">
                Resy Bot
              </p>
              <h1 className="mt-2 text-3xl font-semibold tracking-normal">
                Reservation Console
              </h1>
            </div>
            <span className="rounded-md border border-neutral-300 px-3 py-1 text-sm font-medium capitalize">
              API {health}
            </span>
          </div>

          <form
            action={checkSlots}
            className={`space-y-5 rounded-lg border border-neutral-200 bg-white p-5 shadow-sm ${
              apiOffline ? "opacity-60" : ""
            }`}
          >
            <fieldset disabled={apiOffline} className="space-y-5 disabled:cursor-not-allowed">
              <div className="grid gap-4 sm:grid-cols-2">
              <label className="space-y-2 text-sm font-medium">
                Venue ID
                <input name="venue_id" required className="h-10 w-full rounded-md border border-neutral-300 px-3" />
              </label>
              <label className="space-y-2 text-sm font-medium">
                Party Size
                <input name="party_size" type="number" min="1" defaultValue="2" required className="h-10 w-full rounded-md border border-neutral-300 px-3" />
              </label>
              <label className="space-y-2 text-sm font-medium">
                Date
                <input name="ideal_date" type="date" className="h-10 w-full rounded-md border border-neutral-300 px-3" />
              </label>
              <label className="space-y-2 text-sm font-medium">
                Days In Advance
                <input name="days_in_advance" type="number" min="1" className="h-10 w-full rounded-md border border-neutral-300 px-3" />
              </label>
              <label className="space-y-2 text-sm font-medium">
                Ideal Hour
                <input name="ideal_hour" type="number" min="0" max="23" defaultValue="19" required className="h-10 w-full rounded-md border border-neutral-300 px-3" />
              </label>
              <label className="space-y-2 text-sm font-medium">
                Ideal Minute
                <input name="ideal_minute" type="number" min="0" max="59" defaultValue="30" required className="h-10 w-full rounded-md border border-neutral-300 px-3" />
              </label>
              <label className="space-y-2 text-sm font-medium">
                Window Hours
                <input name="window_hours" type="number" min="0" defaultValue="1" required className="h-10 w-full rounded-md border border-neutral-300 px-3" />
              </label>
              <label className="space-y-2 text-sm font-medium">
                Seating Type
                <input name="preferred_type" placeholder="Dining Room" className="h-10 w-full rounded-md border border-neutral-300 px-3" />
              </label>
              <label className="space-y-2 text-sm font-medium">
                Method
                <select name="method" defaultValue="scheduled" className="h-10 w-full rounded-md border border-neutral-300 px-3">
                  <option value="scheduled">Scheduled</option>
                  <option value="monitor">Monitor</option>
                </select>
              </label>
              <label className="space-y-2 text-sm font-medium">
                Drop Hour
                <input name="expected_drop_hour" type="number" min="0" max="23" defaultValue="10" required className="h-10 w-full rounded-md border border-neutral-300 px-3" />
              </label>
              <label className="space-y-2 text-sm font-medium">
                Drop Minute
                <input name="expected_drop_minute" type="number" min="0" max="59" defaultValue="0" required className="h-10 w-full rounded-md border border-neutral-300 px-3" />
              </label>
              <label className="flex items-center gap-2 self-end text-sm font-medium">
                <input name="prefer_early" type="checkbox" className="size-4 rounded border-neutral-300" />
                Prefer earlier slot
              </label>
              </div>

              {apiOffline ? (
                <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm font-medium text-amber-800">
                  FastAPI is offline. Start the backend before checking slots or booking.
                </p>
              ) : null}

              {error ? (
                <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
                  {error}
                </p>
              ) : null}

              <div className="flex flex-col gap-3 sm:flex-row">
                <button type="submit" className="h-11 rounded-md bg-neutral-950 px-4 text-sm font-semibold text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-400">
                  Check Slots
                </button>
                <button formAction={createReservation} className="h-11 rounded-md bg-emerald-600 px-4 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-neutral-400">
                  Book Reservation
                </button>
              </div>
            </fieldset>
          </form>
        </div>

        <aside className="space-y-4">
          <section className="rounded-lg border border-neutral-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Job Status</h2>
            {job ? (
              <div className="mt-3 space-y-2 text-sm">
                <p>
                  <span className="font-medium">ID:</span> {job.id}
                </p>
                <p className="capitalize">
                  <span className="font-medium">Status:</span> {job.status}
                </p>
                {job.reservation_token ? (
                  <p className="break-all">
                    <span className="font-medium">Token:</span> {job.reservation_token}
                  </p>
                ) : null}
                {job.error ? <p className="text-red-700">{job.error}</p> : null}
                {canCancel ? (
                  <form action={cancelJob}>
                    <input type="hidden" name="job_id" value={job.id} />
                    <button
                      type="submit"
                      disabled={job.status === "cancelling"}
                      className="mt-2 h-10 rounded-md border border-red-300 px-4 text-sm font-semibold text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      Cancel Job
                    </button>
                  </form>
                ) : null}
              </div>
            ) : (
              <p className="mt-3 text-sm text-neutral-600">No active job.</p>
            )}
          </section>

          <section className="rounded-lg border border-neutral-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Available Slots</h2>
            <div className="mt-3 space-y-3">
              {slots.length ? (
                slots.map((slot) => (
                  <div key={slot.config.token} className="rounded-md border border-neutral-200 p-3 text-sm">
                    <p className="font-medium">{new Date(slot.date.start).toLocaleString()}</p>
                    <p className="mt-1 text-neutral-600">{slot.config.type}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-neutral-600">No slots loaded.</p>
              )}
            </div>
          </section>
        </aside>
      </section>
    </main>
  );
}
