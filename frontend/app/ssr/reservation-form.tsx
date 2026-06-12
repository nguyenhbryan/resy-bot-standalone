"use client";

import { FormEvent, useMemo, useRef, useState } from "react";

import { ResyRestaurant, resyRestaurants } from "./resy-restaurants";

type FormAction = (formData: FormData) => void | Promise<void>;

type ReservationFormProps = {
  apiOffline: boolean;
  error: string | null;
  checkSlotsAction: FormAction;
  createReservationAction: FormAction;
};

const timePattern = "^(1[0-2]|0?[1-9])(:[0-5][0-9])?\\s*([AaPp][Mm])$";
const weekdayLabels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function normalize(value: string) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function fillScheduledDefaults(form: HTMLFormElement, restaurant: ResyRestaurant) {
  const dateInput = form.elements.namedItem("ideal_date") as HTMLInputElement | null;
  const daysInput = form.elements.namedItem("days_in_advance") as HTMLInputElement | null;
  const dropTimeInput = form.elements.namedItem("expected_drop_time") as HTMLInputElement | null;

  if (dropTimeInput) {
    dropTimeInput.value = restaurant.dropTime;
  }

  if (restaurant.daysInAdvance) {
    if (daysInput) {
      daysInput.value = String(restaurant.daysInAdvance);
    }

    if (dateInput) {
      dateInput.value = "";
    }

    return;
  }

  if (daysInput) {
    daysInput.value = "";
  }

  if (dateInput) {
    dateInput.value = "";
  }
}

function toDateInputValue(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function parseDateInputValue(value: string) {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function addDays(date: Date, days: number) {
  const nextDate = new Date(date);
  nextDate.setDate(nextDate.getDate() + days);
  return nextDate;
}

function monthLabel(date: Date) {
  return date.toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

function datesBetween(start: string, end: string) {
  const startDate = parseDateInputValue(start);
  const endDate = parseDateInputValue(end);
  const direction = startDate <= endDate ? 1 : -1;
  const dates: string[] = [];
  let cursor = startDate;

  while (
    direction === 1
      ? cursor <= endDate
      : cursor >= endDate
  ) {
    dates.push(toDateInputValue(cursor));
    cursor = addDays(cursor, direction);
  }

  return direction === 1 ? dates : dates.reverse();
}

function calendarDays(month: Date) {
  const firstOfMonth = new Date(month.getFullYear(), month.getMonth(), 1);
  const start = addDays(firstOfMonth, -firstOfMonth.getDay());

  return Array.from({ length: 42 }, (_, index) => addDays(start, index));
}

export function ReservationForm({
  apiOffline,
  error,
  checkSlotsAction,
  createReservationAction,
}: ReservationFormProps) {
  const formRef = useRef<HTMLFormElement>(null);
  const [method, setMethod] = useState("scheduled");
  const [venueQuery, setVenueQuery] = useState("");
  const [selectedRestaurant, setSelectedRestaurant] = useState<ResyRestaurant | null>(null);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [calendarMode, setCalendarMode] = useState<"range" | "dates">("range");
  const [calendarMonth, setCalendarMonth] = useState(() => new Date());
  const [rangeStart, setRangeStart] = useState<string | null>(null);
  const [monitorDates, setMonitorDates] = useState<string[]>([]);

  const filteredRestaurants = useMemo(() => {
    const query = normalize(venueQuery.trim());

    if (!query) {
      return resyRestaurants.slice(0, 8);
    }

    return resyRestaurants
      .filter((restaurant) =>
        normalize(
          `${restaurant.name} ${restaurant.neighborhood} ${restaurant.cuisine}`
        ).includes(query)
      )
      .slice(0, 8);
  }, [venueQuery]);

  function selectRestaurant(restaurant: ResyRestaurant) {
    setSelectedRestaurant(restaurant);
    setVenueQuery(restaurant.name);
    setIsDropdownOpen(false);

    if (method === "scheduled" && formRef.current) {
      fillScheduledDefaults(formRef.current, restaurant);
    }
  }

  function handleMethodChange(nextMethod: string) {
    setMethod(nextMethod);

    if (nextMethod === "scheduled" && selectedRestaurant && formRef.current) {
      fillScheduledDefaults(formRef.current, selectedRestaurant);
    }

    if (nextMethod === "monitor" && formRef.current) {
      const dateInput = formRef.current.elements.namedItem("ideal_date") as HTMLInputElement | null;
      const daysInput = formRef.current.elements.namedItem("days_in_advance") as HTMLInputElement | null;

      if (dateInput) {
        dateInput.value = "";
      }

      if (daysInput) {
        daysInput.value = "";
      }
    }
  }

  function handleVenueChange(value: string) {
    setVenueQuery(value);
    setIsDropdownOpen(true);

    if (selectedRestaurant && value !== selectedRestaurant.name) {
      setSelectedRestaurant(null);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    if (method === "scheduled" && selectedRestaurant) {
      fillScheduledDefaults(event.currentTarget, selectedRestaurant);
    }
  }

  function toggleMonitorDate(value: string) {
    setMonitorDates((currentDates) => {
      if (currentDates.includes(value)) {
        return currentDates.filter((date) => date !== value);
      }

      return [...currentDates, value];
    });
  }

  function handleCalendarDateClick(value: string) {
    if (calendarMode === "dates") {
      toggleMonitorDate(value);
      return;
    }

    if (!rangeStart) {
      setRangeStart(value);
      setMonitorDates([value]);
      return;
    }

    setMonitorDates(datesBetween(rangeStart, value));
    setRangeStart(null);
  }

  const visibleCalendarDays = calendarDays(calendarMonth);

  return (
    <form
      ref={formRef}
      action={checkSlotsAction}
      onSubmit={handleSubmit}
      className={`reservation-form space-y-5 rounded-lg border border-neutral-200 bg-white p-5 shadow-sm ${
        apiOffline ? "opacity-60" : ""
      }`}
    >
      <fieldset disabled={apiOffline} className="space-y-5 disabled:cursor-not-allowed">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-2 text-sm font-medium">
            Method
            <select
              name="method"
              value={method}
              onChange={(event) => handleMethodChange(event.currentTarget.value)}
              className="h-10 w-full rounded-md border border-neutral-300 px-3"
            >
              <option value="scheduled">Scheduled</option>
              <option value="monitor">Monitor</option>
            </select>
          </label>

          <label className="space-y-2 text-sm font-medium">
            Venue ID
            <input
              name="venue_id"
              placeholder="Optional"
              className="h-10 w-full rounded-md border border-neutral-300 px-3"
            />
          </label>

          <div className="relative space-y-2 text-sm font-medium sm:col-span-2">
            <label htmlFor="venue_name">Venue Name</label>
            <input
              id="venue_name"
              name="venue_name"
              value={venueQuery}
              onChange={(event) => handleVenueChange(event.currentTarget.value)}
              onFocus={() => setIsDropdownOpen(true)}
              onBlur={() => window.setTimeout(() => setIsDropdownOpen(false), 120)}
              placeholder="Carbone"
              autoComplete="off"
              className="h-10 w-full rounded-md border border-neutral-300 px-3"
            />
            {isDropdownOpen && filteredRestaurants.length ? (
              <div className="absolute z-10 mt-1 max-h-72 w-full overflow-y-auto rounded-md border border-neutral-200 bg-white shadow-lg">
                {filteredRestaurants.map((restaurant) => (
                  <button
                    key={restaurant.name}
                    type="button"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => selectRestaurant(restaurant)}
                    className="block w-full border-b border-neutral-100 px-3 py-2 text-left last:border-b-0 hover:bg-neutral-50 focus:bg-neutral-50 focus:outline-none"
                  >
                    <span className="block text-sm font-semibold text-neutral-950">
                      {restaurant.name}
                    </span>
                    <span className="mt-1 block text-xs font-normal text-neutral-600">
                      {restaurant.neighborhood} · {restaurant.cuisine} ·{" "}
                      {restaurant.releaseRule} at {restaurant.dropTime}
                    </span>
                  </button>
                ))}
              </div>
            ) : null}
          </div>

          <label className="space-y-2 text-sm font-medium">
            City or Region
            <input
              name="venue_location"
              placeholder="New York"
              className="h-10 w-full rounded-md border border-neutral-300 px-3"
            />
          </label>
          <label className="space-y-2 text-sm font-medium">
            Party Size
            <input
              name="party_size"
              type="number"
              min="1"
              defaultValue="2"
              required
              className="h-10 w-full rounded-md border border-neutral-300 px-3"
            />
          </label>
          {method === "scheduled" ? (
            <>
              <label className="space-y-2 text-sm font-medium">
                Date
                <input
                  name="ideal_date"
                  type="date"
                  className="h-10 w-full rounded-md border border-neutral-300 px-3"
                />
              </label>
              <label className="space-y-2 text-sm font-medium">
                Days In Advance
                <input
                  name="days_in_advance"
                  type="number"
                  min="1"
                  className="h-10 w-full rounded-md border border-neutral-300 px-3"
                />
              </label>
            </>
          ) : (
            <div className="space-y-3 sm:col-span-2">
              {monitorDates.map((date) => (
                <input key={date} name="monitor_dates" type="hidden" value={date} />
              ))}
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm font-medium">Monitor Dates</p>
                <div className="inline-flex rounded-md border border-neutral-300 p-1">
                  <button
                    type="button"
                    onClick={() => setCalendarMode("range")}
                    className={`h-8 rounded px-3 text-sm font-medium ${
                      calendarMode === "range"
                        ? "bg-neutral-950 text-white"
                        : "text-neutral-700 hover:bg-neutral-100"
                    }`}
                  >
                    Range
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setCalendarMode("dates");
                      setRangeStart(null);
                    }}
                    className={`h-8 rounded px-3 text-sm font-medium ${
                      calendarMode === "dates"
                        ? "bg-neutral-950 text-white"
                        : "text-neutral-700 hover:bg-neutral-100"
                    }`}
                  >
                    Dates
                  </button>
                </div>
              </div>
              <div className="rounded-md border border-neutral-200 p-3">
                <div className="flex items-center justify-between">
                  <button
                    type="button"
                    onClick={() =>
                      setCalendarMonth(
                        new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() - 1, 1)
                      )
                    }
                    className="h-9 w-9 rounded-md border border-neutral-300 text-lg font-semibold hover:bg-neutral-50"
                    aria-label="Previous month"
                  >
                    ‹
                  </button>
                  <p className="text-sm font-semibold">{monthLabel(calendarMonth)}</p>
                  <button
                    type="button"
                    onClick={() =>
                      setCalendarMonth(
                        new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + 1, 1)
                      )
                    }
                    className="h-9 w-9 rounded-md border border-neutral-300 text-lg font-semibold hover:bg-neutral-50"
                    aria-label="Next month"
                  >
                    ›
                  </button>
                </div>
                <div className="mt-3 grid grid-cols-7 gap-1 text-center text-xs font-medium text-neutral-500">
                  {weekdayLabels.map((day) => (
                    <div key={day}>{day}</div>
                  ))}
                </div>
                <div className="mt-1 grid grid-cols-7 gap-1">
                  {visibleCalendarDays.map((date) => {
                    const value = toDateInputValue(date);
                    const isSelected = monitorDates.includes(value);
                    const isCurrentMonth = date.getMonth() === calendarMonth.getMonth();
                    const isRangeStart = rangeStart === value;

                    return (
                      <button
                        key={value}
                        type="button"
                        aria-label={value}
                        onClick={() => handleCalendarDateClick(value)}
                        className={`aspect-square rounded-md text-sm font-medium transition ${
                          isSelected
                            ? "bg-emerald-600 text-white"
                            : isCurrentMonth
                              ? "text-neutral-900 hover:bg-neutral-100"
                              : "text-neutral-400 hover:bg-neutral-50"
                        } ${isRangeStart ? "ring-2 ring-emerald-300" : ""}`}
                      >
                        {date.getDate()}
                      </button>
                    );
                  })}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {monitorDates.length ? (
                  monitorDates.map((date) => (
                    <button
                      key={date}
                      type="button"
                      onClick={() => toggleMonitorDate(date)}
                      className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-800"
                    >
                      {date}
                    </button>
                  ))
                ) : (
                  <p className="text-sm text-neutral-600">No monitor dates selected.</p>
                )}
                {monitorDates.length ? (
                  <button
                    type="button"
                    onClick={() => {
                      setMonitorDates([]);
                      setRangeStart(null);
                    }}
                    className="rounded-md border border-neutral-300 px-2 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-50"
                  >
                    Clear
                  </button>
                ) : null}
              </div>
            </div>
          )}
          <label className="space-y-2 text-sm font-medium">
            Ideal Time
            <input
              name="ideal_time"
              type="text"
              inputMode="text"
              pattern={timePattern}
              placeholder="7:30 PM"
              defaultValue="7:30 PM"
              required
              className="h-10 w-full rounded-md border border-neutral-300 px-3"
            />
          </label>
          <label className="space-y-2 text-sm font-medium">
            Window Hours
            <input
              name="window_hours"
              type="number"
              min="0"
              defaultValue="1"
              required
              className="h-10 w-full rounded-md border border-neutral-300 px-3"
            />
          </label>
          <label className="space-y-2 text-sm font-medium">
            Seating Type
            <input
              name="preferred_type"
              placeholder="Dining Room"
              className="h-10 w-full rounded-md border border-neutral-300 px-3"
            />
          </label>
          {method === "scheduled" ? (
            <label data-drop-time className="space-y-2 text-sm font-medium">
              Drop Time
              <input
                name="expected_drop_time"
                type="text"
                inputMode="text"
                pattern={timePattern}
                placeholder="10:00 AM"
                defaultValue="10:00 AM"
                required
                className="h-10 w-full rounded-md border border-neutral-300 px-3"
              />
            </label>
          ) : (
            <input name="expected_drop_time" type="hidden" value="10:00 AM" />
          )}
          <label className="flex items-center gap-2 self-end text-sm font-medium">
            <input name="prefer_early" type="checkbox" className="size-4 rounded border-neutral-300" />
            Prefer earlier slot
          </label>
        </div>

        {selectedRestaurant ? (
          <p className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800">
            {selectedRestaurant.name}: {selectedRestaurant.releaseRule} at{" "}
            {selectedRestaurant.dropTime}
          </p>
        ) : null}

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
          <button
            type="submit"
            className="h-11 rounded-md bg-neutral-950 px-4 text-sm font-semibold text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:bg-neutral-400"
          >
            Check Slots
          </button>
          <button
            formAction={createReservationAction}
            className="h-11 rounded-md bg-emerald-600 px-4 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-neutral-400"
          >
            Book Reservation
          </button>
        </div>
      </fieldset>
    </form>
  );
}
