---
name: set-source
description: "This skill should be used when the user asks to \"set up Career Ops\", \"set my career data source\", \"where should my job tracker live\", \"switch my job tracker to Notion\", or otherwise wants to choose or check where their Career Ops job-search data is kept."
---

# Career Ops data source

Choose where the user's Career Ops job-search data lives, check that it is
reachable, and save the choice to memory so job-tracking requests use it.

## Supported sources

| Source | Status |
|---|---|
| Notion | Supported |

Notion is the only supported source. If the user asks for another (a
spreadsheet, Airtable, a local file), say it is not supported yet and offer
Notion. Never save an unsupported source.

## Steps

1. **Read memory.** If a Career Ops data source is saved, tell the user which
   one and ask whether to keep it or change it.
2. **Pick the source.** With one supported source, confirm Notion with the user
   rather than asking an open question.
3. **Check the connection.** Confirm that the current client has an
   authenticated Notion tool or app connection with access to the user's
   **Career Ops** page. Search for that page and its named children: the
   **Profile** and **Notes** pages and the **Jobs**, **Events** and
   **Contacts** databases. If the connection is missing, access is denied, or
   any item cannot be found, explain which connection or page access is
   required and stop without saving. If more than one item has the same name,
   ask the user which one to use.
4. **Save.** Save `Career Ops data source: Notion` to memory, replacing any
   earlier value. Never save workspace identifiers, page IDs or URLs.
5. **Confirm.** State in one line the saved source and that the Career Ops
   page and its five children were found.

This skill only chooses and checks the source. It does not read or write jobs,
events or contacts.
