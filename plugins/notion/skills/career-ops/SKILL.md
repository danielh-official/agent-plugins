---
name: career-ops
description: "This skill should be used when the user asks to \"track a job application\", \"show my active jobs\", \"what's due\", \"where am I with this role\", \"is this job a fit\", or mentions a job, interview, recruiter, follow-up, or referral that belongs in the Notion Career Ops tracker."
---

# Notion career-ops

## Connection preflight

Confirm that the current client has an authenticated Notion tool or app
connection with access to the user's **Career Ops** page. Search for that page
and its named children before handling the request. If the connection is
missing, access is denied, or the expected structure cannot be found, stop
before reading or writing data and explain which connection or page access is
required.

Notion is the tracker. Everything lives under the **Career Ops** page. Find
pages and databases by the exact names below. If more than one item has the
same name, ask the user which one to use. Never persist workspace identifiers
in plugin files.

| Database | Location | One row per |
|---|---|---|
| Jobs | Under **Career Ops** | job posting (lead or application) |
| Events | Under **Career Ops** | something that happened, on a date |
| Contacts | Under **Career Ops** | person |

The **Profile** page under **Career Ops** is the user's master profile,
targeting, skills by evidence level, and how to judge fit. Free text not tied
to one job goes under the **Notes** page. Job-specific prep, debriefs and
resume drafts go in that job's page body.

## Jobs fields

- **Company** (title), **Role**, **URL**, **Req ID**, **Via** (agency), **Location**, **Comp**, **Score** (0–5), **Closes** (deadline), **Notes** (one short line; history goes in Events).
- Stage dates: `evaluated_at`, `applied_at`, `responded_at`, `interview_at`, `offer_at`, `hired_at`, `rejected_at`, `discarded_at`, `skipped_at` (evaluated, decided not to apply).
- **Status** and **Active** are formulas. The connector cannot read them, so derive them yourself (below).

## Deriving status (always do this yourself)

1. If `hired_at` is set → Hired. Else `rejected_at` → Rejected. Else `discarded_at` → Discarded. Else `skipped_at` → Skipped.
2. Otherwise the furthest stage with a date: Offer > Interview > Responded > Applied > Evaluated.
3. No dates at all → New (a lead).
4. Active = none of hired/rejected/discarded/skipped is set.

## Fit questions

Before judging fit ("is this a fit?", "which roles at X fit me best?"), read the **Profile** page in full and follow its "How to judge fit" and "Never claim" sections. Fetch the posting if a link is given. A requirement that is not on the Profile is a gap; never infer it. Label every score from a quick read as an estimate. If the user wants it tracked, add or update the Jobs row (Score + "score is an estimate" in Notes).

## Writing rules

1. **Before adding a job, look for an existing row.** Match on URL, then Req ID, then Company + Role. Same company and similar title but a *different* Req ID = a different job. If unsure, ask.
2. **Moving a job forward:** set that stage's date (today unless the user gives one) and add an Event. Never clear an earlier stage date.
3. **Clearing a date is only for a mistake** (e.g. a rejection sent in error). Clear it and add a `Status change` Event saying what was reversed and why.
4. **Every interaction is an Event:** Summary (short), Date, Type (Call, Interview, Email, Text, Follow-up, Assessment, Status change, Note), Job relation, Contacts relation, Notes. One Event can link several jobs (e.g. one referral email covering three postings).
5. **Unknown employer:** Company is `? (undisclosed employer)`, never another spelling, so searches find them all.
6. **People go in Contacts**, not in free text. Check for an existing contact by name + company first. Type: Recruiter, Hiring manager, Interviewer, Peer, Referral. Link them to the job.
7. **Score:** a quick fit estimate goes in Score with "score is an estimate" in Notes, until a full evaluation replaces it.
8. **Never invent facts.** Only write what the user said or what a source (email, posting) says. Unknown stays blank.
9. **Dates:** ISO `YYYY-MM-DD`. Times only when known, with the user's timezone (America/New_York).
10. **Follow-ups and to-dos are not stored here.** They live in the user's task app (2Do). This tracker records what happened.

## After every write

Read the row back and state the result in one line: company, role, derived status, what changed. If a write failed or a field didn't stick, say so plainly.

After changing several jobs at once, check that every job whose stage date changed has an Event for that change. If any are missing, add one (one Event may link several jobs) before reporting done.

## Common requests

- **"What's active?"** Query Jobs, derive status, list Active rows grouped by status, newest stage date first.
- **"What closes soon?"** Jobs with `Closes` in the next 14 days that are still New or Evaluated.
- **"Where am I with X?"** The row, its derived status, and its last 3 Events.
- **"Just got off a call with Y."** Find the job and contact, add an Event, set `interview_at` if this was the first interview, then offer to write a debrief into the job's page body.
