import { createHash } from "crypto";
import { Buffer } from "buffer";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ReservationForm } from "./reservation-form";

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

type ApiVenue = {
  venue_id: string;
  name: string;
  locality?: string | null;
  region?: string | null;
};

type SlotCheckResult = {
  venue?: ApiVenue | null;
  slots: ApiSlot[];
};

type JobStatus =
  | "pending"
  | "running"
  | "cancelling"
  | "cancelled"
  | "succeeded"
  | "failed";

type ReservationDetails = {
  restaurant_name?: string | null;
  venue_id?: string | null;
  venue_location?: string | null;
  party_size?: number | null;
  ideal_date?: string | null;
  days_in_advance?: number | null;
  ideal_time?: string | null;
  window_hours?: number | null;
  prefer_early?: boolean | null;
  preferred_type?: string | null;
  method?: string | null;
  expected_drop_time?: string | null;
};

type ReservationJob = {
  id: string;
  status: JobStatus;
  created_at?: string;
  updated_at?: string;
  reservation?: ReservationDetails | null;
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

function getTimeParts(formData: FormData, key: string) {
  const value = getText(formData, key);
  const match = value.match(/^(\d{1,2})(?::([0-5]\d))?\s*([ap]m)$/i);

  if (!match) {
    throw new Error("Enter times like 7:30 PM.");
  }

  const hour12 = Number(match[1]);
  const minute = match[2] ? Number(match[2]) : 0;
  const period = match[3].toLowerCase();

  if (hour12 < 1 || hour12 > 12) {
    throw new Error("Use a 12-hour time between 1:00 AM and 12:59 PM.");
  }

  return {
    hour: period === "pm" ? (hour12 % 12) + 12 : hour12 % 12,
    minute,
  };
}

function buildReservationRequest(formData: FormData) {
  const preferredType = getText(formData, "preferred_type");
  const idealDate = getText(formData, "ideal_date");
  const daysInAdvance = getText(formData, "days_in_advance");
  const idealTime = getTimeParts(formData, "ideal_time");

  if (!idealDate && !daysInAdvance) {
    throw new Error("Choose either a reservation date or days in advance.");
  }

  if (idealDate && daysInAdvance) {
    throw new Error("Use either reservation date or days in advance, not both.");
  }

  return {
    venue_id: getText(formData, "venue_id") || null,
    venue_name: getText(formData, "venue_name") || null,
    venue_location: getText(formData, "venue_location") || null,
    party_size: getNumber(formData, "party_size"),
    ideal_hour: idealTime.hour,
    ideal_minute: idealTime.minute,
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

function decodeSlotResult(value?: string | string[]): SlotCheckResult {
  if (!value || Array.isArray(value)) {
    return { venue: null, slots: [] };
  }

  try {
    const decoded = JSON.parse(
      Buffer.from(value, "base64url").toString("utf8")
    ) as ApiSlot[] | SlotCheckResult;

    if (Array.isArray(decoded)) {
      return { venue: null, slots: decoded };
    }

    return { venue: decoded.venue ?? null, slots: decoded.slots ?? [] };
  } catch {
    return { venue: null, slots: [] };
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
    const response = await apiRequest<SlotCheckResult>("/slots", {
      method: "POST",
      body: JSON.stringify(body),
    });

    nextPath = `/ssr?slots=${encodeState(response)}`;
  } catch (error) {
    nextPath = `/ssr?error=${encodeURIComponent((error as Error).message)}`;
  }

  redirect(nextPath);
}

async function createReservation(formData: FormData) {
  "use server";

  let nextPath = "/ssr";

  try {
    const dropTime = getTimeParts(formData, "expected_drop_time");
    const body = {
      reservation_request: buildReservationRequest(formData),
      expected_drop_hour: dropTime.hour,
      expected_drop_minute: dropTime.minute,
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
  let nextPath = "/ssr";

  try {
    await apiRequest<ReservationJob>(`/jobs/${jobId}/cancel`, {
      method: "POST",
    });
  } catch (error) {
    nextPath = `/ssr?error=${encodeURIComponent((error as Error).message)}`;
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

async function getJobs() {
  try {
    return apiRequest<ReservationJob[]>("/jobs");
  } catch {
    return [];
  }
}

function canCancelJob(job: ReservationJob) {
  return (
    job.status === "pending" ||
    job.status === "running" ||
    job.status === "cancelling"
  );
}

function formatDateTime(value?: string) {
  if (!value) {
    return null;
  }

  return new Date(value).toLocaleString();
}

function formatDate(value?: string | null) {
  if (!value) {
    return null;
  }

  const parts = value.split("-").map(Number);

  if (parts.length !== 3 || parts.some(Number.isNaN)) {
    return value;
  }

  return new Date(parts[0], parts[1] - 1, parts[2]).toLocaleDateString();
}

function reservationTitle(reservation?: ReservationDetails | null) {
  if (!reservation) {
    return "Reservation";
  }

  return (
    reservation.restaurant_name ||
    (reservation.venue_id ? `Venue ${reservation.venue_id}` : "Reservation")
  );
}

function reservationDate(reservation?: ReservationDetails | null) {
  if (!reservation) {
    return null;
  }

  if (reservation.ideal_date) {
    return formatDate(reservation.ideal_date);
  }

  if (reservation.days_in_advance) {
    return `${reservation.days_in_advance} days out`;
  }

  return null;
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
  const slotResult = decodeSlotResult(params?.slots);
  const slots = slotResult.slots;
  const [selectedJob, jobs] = await Promise.all([getJob(params?.job), getJobs()]);
  const health = await getHealth();
  const error = typeof params?.error === "string" ? params.error : null;
  const apiOffline = health === "offline";
  const visibleJobs =
    selectedJob && !jobs.some((job) => job.id === selectedJob.id)
      ? [selectedJob, ...jobs]
      : jobs;

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

          <ReservationForm
            apiOffline={apiOffline}
            error={error}
            checkSlotsAction={checkSlots}
            createReservationAction={createReservation}
          />
        </div>

        <aside className="space-y-4">
          <section className="rounded-lg border border-neutral-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Jobs</h2>
            {visibleJobs.length ? (
              <div className="mt-3 max-h-[36.75rem] space-y-3 overflow-y-auto pr-1">
                {visibleJobs.map((job) => (
                  <div key={job.id} className="rounded-md border border-neutral-200 p-3 text-sm">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium capitalize">{job.status}</p>
                      {formatDateTime(job.created_at) ? (
                        <p className="text-xs text-neutral-500">{formatDateTime(job.created_at)}</p>
                      ) : null}
                    </div>
                    <p className="mt-2 break-all text-xs text-neutral-600">
                      {job.id}
                    </p>
                    {job.reservation ? (
                      <div className="mt-3 space-y-2 rounded-md bg-neutral-50 p-3">
                        <div>
                          <p className="font-medium">{reservationTitle(job.reservation)}</p>
                          {job.reservation.venue_location ? (
                            <p className="text-xs text-neutral-500">
                              {job.reservation.venue_location}
                            </p>
                          ) : null}
                        </div>
                        <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
                          {job.reservation.party_size ? (
                            <>
                              <dt className="text-neutral-500">Party</dt>
                              <dd className="font-medium">{job.reservation.party_size}</dd>
                            </>
                          ) : null}
                          {reservationDate(job.reservation) ? (
                            <>
                              <dt className="text-neutral-500">Date</dt>
                              <dd className="font-medium">
                                {reservationDate(job.reservation)}
                              </dd>
                            </>
                          ) : null}
                          {job.reservation.ideal_time ? (
                            <>
                              <dt className="text-neutral-500">Time</dt>
                              <dd className="font-medium">{job.reservation.ideal_time}</dd>
                            </>
                          ) : null}
                          {job.reservation.expected_drop_time ? (
                            <>
                              <dt className="text-neutral-500">Drop</dt>
                              <dd className="font-medium">
                                {job.reservation.expected_drop_time}
                              </dd>
                            </>
                          ) : null}
                          {job.reservation.preferred_type ? (
                            <>
                              <dt className="text-neutral-500">Seating</dt>
                              <dd className="font-medium">
                                {job.reservation.preferred_type}
                              </dd>
                            </>
                          ) : null}
                          {job.reservation.method ? (
                            <>
                              <dt className="text-neutral-500">Method</dt>
                              <dd className="font-medium capitalize">
                                {job.reservation.method}
                              </dd>
                            </>
                          ) : null}
                        </dl>
                      </div>
                    ) : null}
                    {job.reservation_token ? (
                      <p className="mt-2 break-all">
                        <span className="font-medium">Token:</span> {job.reservation_token}
                      </p>
                    ) : null}
                    {job.error ? <p className="mt-2 text-red-700">{job.error}</p> : null}
                    {canCancelJob(job) ? (
                      <form action={cancelJob}>
                        <input type="hidden" name="job_id" value={job.id} />
                        <button
                          type="submit"
                          disabled={job.status === "cancelling"}
                          className="mt-3 h-10 rounded-md border border-red-300 px-4 text-sm font-semibold text-red-700 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          Cancel Job
                        </button>
                      </form>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm text-neutral-600">No jobs yet.</p>
            )}
          </section>

          <section className="rounded-lg border border-neutral-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Available Slots</h2>
            {slotResult.venue ? (
              <p className="mt-1 text-sm font-medium text-neutral-700">
                {slotResult.venue.name}
                {[slotResult.venue.locality, slotResult.venue.region].filter(Boolean).length
                  ? `, ${[slotResult.venue.locality, slotResult.venue.region]
                      .filter(Boolean)
                      .join(", ")}`
                  : ""}
              </p>
            ) : null}
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
