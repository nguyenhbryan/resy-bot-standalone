# Features

Infer booking date time (TODO) - A venue returns a calendar which has a `last_calendar_day`, which is the latest available date to book. Using this, we won't have to manually configure days in advance.

## API MVP (TODO)

- I current have a website that is way too complex.

- The best plan for me now is to create a straightforward API and have all the logic here.

The API should have some parameters.

1. Venue id

- We can compile a list of venues and their corresponding ids, I have code for that somwhere.

2. Party size

3. Window hours. Range in case specific time is booked.

4. Drop time (HH, MM)

Resy API config. It can default to mine, but also give users an option to specify their own.
