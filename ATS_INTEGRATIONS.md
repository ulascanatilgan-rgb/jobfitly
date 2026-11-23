# JobFitly shared vacancy integrations

The default deployment needs **no new paid service**, database, or API keys.
All accepted employer feed data is stored in the existing Railway SQLite
database on its persistent /data volume, separate from users' uploaded CVs.

## Public employer sources (enabled)
- **Greenhouse:** GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
- **Lever:** GET https://api.lever.co/v0/postings/{slug}?mode=json (EU host when appropriate)
- **Ashby:** GET https://api.ashbyhq.com/posting-api/job-board/{slug}

These public endpoints publish vacancies for a particular company, not every
employer using that ATS. A carefully selected initial list is bundled in
shared_inventory.py. To add more known public employer boards, optionally
set the Railway environment variable ATS_BOARDS to a JSON object:

{"greenhouse":["exampleboard"],"lever":["exampleco"],"ashby":["exampleco"]}

Only known valid company-specific board slugs should be used. The program
validates slug syntax. Invalid, private, disabled or unavailable boards are
skipped without breaking the search.

## Data handling and speed
- No CV, name, email or work-style answers go to the public ATS GET endpoints.
- Global shared inventory uses SQLite; cached jobs are reused by every account.
- Refresh is lease-guarded (one active refresher), at most every 3 hours;
  stale listings disappear after 24 hours without a successful refresh.
- OpenAI web discovery remains optional fallback if there are too few
  credible CV-related positions. No extra AI model is used to extract Career DNA.
- A cache-backed preview appears while full matching is underway.
- The final list holds up to 12 verified/attributed candidates as reserves:
  a rejected role is replaced from reserves without a new live search.

## Adzuna (inactive by design)
The adapter is implemented, but Adzuna's terms limit commercial use without
a signed licence agreement after the evaluation period.
To enable it *only once licence rights and API credentials are obtained*,
set all three variables:

ADZUNA_APP_ID=<your own app id>
ADZUNA_APP_KEY=<your own app key>
ADZUNA_COMMERCIAL_LICENSE_CONFIRMED=1

**Do not enable Adzuna solely on a free evaluation key for ongoing use in a
revenue-generating application.** JobFitly does not automatically register,
purchase or transmit user PII to Adzuna. The integration sends only a
generic career-family query when specifically licensed and configured.

## Learning & user control
"Not for me" is an authenticated, user-specific feedback action.
It persists the rejected job and title in the existing SQLite database and
reduces ranking of closely similar titles on later searches. It never affects
other users. DELETE /api/jobs/{id}/not-for-me undoes a decision.

Career DNA is deterministic and evidence-based. Never interpret it as a
validated qualification, hiring probability or promise of placement.
