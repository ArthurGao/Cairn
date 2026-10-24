# Fact categories

Code reads the category ids below (the backticked first column) to build the extraction schema's
enum. Add a row to add a category; the `normalised` column says what form the value must take.

| Category | Subject | Normalised | What counts |
| --- | --- | --- | --- |
| `identity.name` | person | text | full name as written, including order and spelling |
| `identity.date_of_birth` | person | date | |
| `identity.passport_number` | person | text | |
| `identity.nationality` | person | text | |
| `address.period` | person | period + text | an address with the dates the person lived there |
| `employment.period` | person + employer | period | start and end of a job; open end = current |
| `employment.role` | person + employer | text | job title |
| `family.member` | person | text | partner, child or parent, with their date of birth if given |
| `travel.period` | person | period + text | a trip: dates and country |
| `prior_application` | person | text | an earlier visa application, its type, date and outcome |

Dates are ISO 8601 at the precision written: `2022`, `2022-03` or `2022-03-14`. A period is
`<start>/<end>`, with `..` for an open end (`2022-06/..`).
