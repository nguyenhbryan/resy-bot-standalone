"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

type DemoStage = "ready" | "slots" | "booking";

const demoSlots = [
  {
    time: "6:45 PM",
    type: "Dining Room",
    score: "Best match",
  },
  {
    time: "7:15 PM",
    type: "Dining Room",
    score: "Within window",
  },
  {
    time: "8:00 PM",
    type: "Bar",
    score: "Backup",
  },
];

const bookingSteps = [
  "Request queued",
  "Waiting for release window",
  "Matching preferred seating",
  "Reservation held",
];

export default function DemoPage() {
  const [stage, setStage] = useState<DemoStage>("ready");
  const [selectedSlot, setSelectedSlot] = useState(demoSlots[0]);

  const timeline = useMemo(() => {
    if (stage === "ready") {
      return bookingSteps.slice(0, 1);
    }

    if (stage === "slots") {
      return bookingSteps.slice(0, 3);
    }

    return bookingSteps;
  }, [stage]);

  return (
    <main className="min-h-screen bg-neutral-50 px-5 py-6 text-neutral-950 sm:px-8">
      <section className="mx-auto grid w-full max-w-6xl gap-6 lg:grid-cols-[minmax(0,1.08fr)_minmax(320px,0.92fr)]">
        <div>
          <div className="mb-6 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.2em] text-emerald-700">
                Resy Bot Demo
              </p>
              <h1 className="mt-2 text-3xl font-semibold tracking-normal">
                Reservation Simulation
              </h1>
            </div>
            <Link
              href="/"
              className="flex h-10 w-fit items-center rounded-md border border-neutral-300 px-4 text-sm font-semibold transition hover:bg-white"
            >
              Back to Key
            </Link>
          </div>

          <section className="rounded-lg border border-neutral-200 bg-white p-5 shadow-sm">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="space-y-2 text-sm font-medium">
                Venue Name
                <input
                  readOnly
                  value="Carbone"
                  className="h-10 w-full rounded-md border border-neutral-300 px-3"
                />
              </label>
              <label className="space-y-2 text-sm font-medium">
                City or Region
                <input
                  readOnly
                  value="New York"
                  className="h-10 w-full rounded-md border border-neutral-300 px-3"
                />
              </label>
              <label className="space-y-2 text-sm font-medium">
                Party Size
                <input
                  readOnly
                  value="2"
                  className="h-10 w-full rounded-md border border-neutral-300 px-3"
                />
              </label>
              <label className="space-y-2 text-sm font-medium">
                Date
                <input
                  readOnly
                  value="June 20, 2026"
                  className="h-10 w-full rounded-md border border-neutral-300 px-3"
                />
              </label>
              <label className="space-y-2 text-sm font-medium">
                Ideal Time
                <input
                  readOnly
                  value="7:00 PM"
                  className="h-10 w-full rounded-md border border-neutral-300 px-3"
                />
              </label>
              <label className="space-y-2 text-sm font-medium">
                Seating Type
                <input
                  readOnly
                  value="Dining Room"
                  className="h-10 w-full rounded-md border border-neutral-300 px-3"
                />
              </label>
            </div>

            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                onClick={() => setStage("slots")}
                className="h-11 rounded-md bg-neutral-950 px-4 text-sm font-semibold text-white transition hover:bg-neutral-800"
              >
                Simulate Slot Check
              </button>
              <button
                type="button"
                onClick={() => setStage("booking")}
                className="h-11 rounded-md bg-emerald-600 px-4 text-sm font-semibold text-white transition hover:bg-emerald-700"
              >
                Simulate Booking
              </button>
              <button
                type="button"
                onClick={() => {
                  setStage("ready");
                  setSelectedSlot(demoSlots[0]);
                }}
                className="h-11 rounded-md border border-neutral-300 px-4 text-sm font-semibold transition hover:bg-neutral-50"
              >
                Reset
              </button>
            </div>
          </section>
        </div>

        <aside className="space-y-4">
          <section className="rounded-lg border border-neutral-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">Simulation Status</h2>
              <span className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-1 text-sm font-medium text-emerald-800">
                Demo mode
              </span>
            </div>

            <div className="mt-4 space-y-3">
              {timeline.map((step, index) => {
                const isComplete = stage === "booking" || index < timeline.length - 1;

                return (
                  <div
                    key={step}
                    className="flex items-center gap-3 rounded-md border border-neutral-200 p-3 text-sm"
                  >
                    <span
                      className={`flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                        isComplete
                          ? "bg-emerald-600 text-white"
                          : "bg-neutral-200 text-neutral-700"
                      }`}
                    >
                      {index + 1}
                    </span>
                    <p className="font-medium">{step}</p>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="rounded-lg border border-neutral-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Available Slots</h2>
            <p className="mt-1 text-sm font-medium text-neutral-700">
              Carbone, New York
            </p>
            <div className="mt-3 space-y-3">
              {stage === "ready" ? (
                <p className="text-sm text-neutral-600">Run the slot check to load demo availability.</p>
              ) : (
                demoSlots.map((slot) => (
                  <button
                    key={`${slot.time}-${slot.type}`}
                    type="button"
                    onClick={() => setSelectedSlot(slot)}
                    className={`w-full rounded-md border p-3 text-left text-sm transition ${
                      selectedSlot.time === slot.time
                        ? "border-emerald-500 bg-emerald-50"
                        : "border-neutral-200 hover:bg-neutral-50"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium">{slot.time}</p>
                      <p className="text-xs font-medium text-emerald-700">{slot.score}</p>
                    </div>
                    <p className="mt-1 text-neutral-600">{slot.type}</p>
                  </button>
                ))
              )}
            </div>
          </section>

          <section className="rounded-lg border border-neutral-200 bg-white p-5 shadow-sm">
            <h2 className="text-lg font-semibold">Demo Result</h2>
            {stage === "booking" ? (
              <div className="mt-3 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm">
                <p className="font-semibold text-emerald-900">Reservation held</p>
                <p className="mt-1 text-emerald-800">
                  Party of 2 at {selectedSlot.time} in the {selectedSlot.type}.
                </p>
              </div>
            ) : (
              <p className="mt-3 text-sm text-neutral-600">
                Select a slot, then simulate booking to preview the confirmation state.
              </p>
            )}
          </section>
        </aside>
      </section>
    </main>
  );
}
