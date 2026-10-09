---
name: topic-grouper
description: Pull issues from Linear and cluster them into related topic groups, flagging duplicates and overlapping tasks, then optionally write the grouping back to Linear as topic labels or parent issues. Use this whenever the user wants to organize, group, cluster, triage, theme, or make sense of Linear issues or a backlog, including when they paste a Linear view, label, project, or team URL, or say things like "group my Linear tasks", "what themes are in my backlog", "organize these issues by topic", "find duplicates in Linear", or "tidy up my Linear project", even if they don't say "group".
---

# Linear Topic Grouper

Fetch Linear issues, group them by what they are actually about, show the groups in chat, flag duplicates and overlaps, and offer to write the structure back to Linear.

Existing labels like `Feature` or `Bug` describe the *type* of work, not the *topic*, so they are rarely useful for grouping. Cluster on each issue's title and description instead.

## Step 1: Settle the scope before calling the API

The default scope is all of the user's Linear issues, but a whole workspace is noisy and slow. So before fetching anything, check whether the request already pins down a scope:

- **Scope given** (a view/label/project/team URL or name, or "my issues in X"): use it. Skip the scoping question.
- **No scope given**: ask one short question with `ask_user_input_v0` offering to narrow by view, label, project, team, or status, plus an "Everything" option. Wait for the answer before calling Linear.

Also settle whether to include completed and canceled issues. Default to open issues only (exclude `completed` and `canceled` status types) unless the user asks otherwise, and say so in one line.

## Step 2: Fetch the issues

Load the Linear tools with `tool_search` ("Linear list issues") if they aren't loaded yet. Then call `list_issues`:

- **View URL or name**: pass it as `customView`. It accepts the full URL; query parameters after `?` are display settings and can be dropped.
- **Label / project / team**: pass as `label`, `project`, or `team`.
- Request `fields`: `id`, `title`, `description`, `status`, `statusType`, `priority`, `labels`, `project`, `parentId`, `url`.
- Use `limit: 250` and follow `cursor` while `hasNextPage` is true.
- `query` cannot be combined with `customView`.

If a view name is ambiguous, look it up with `list_custom_views` first. If the result is empty, say what filter was used and ask whether to widen it.

## Step 3: Group by topic

Read every title and description, then form groups around the part of the product or area of work each issue touches (for example "Notifications & scheduling", "Import & integrations", "Monetization"). Good groups:

- Are named by topic, in plain words, 2 to 5 words long.
- Hold roughly 2 to 7 issues. Split a group that grows past ~8; fold singletons into the nearest reasonable group, or collect true loners under "Other".
- Put each issue in exactly one group. When an issue fits two, pick the group where someone would look for it first.
- Aim for about one group per 3 to 5 issues overall; 30 issues usually lands at 6 to 9 groups.

If issues already have parents (`parentId`), keep children with their parent's topic.

## Step 4: Flag duplicates and overlaps

While grouping, watch for:

- **Duplicates**: two issues describing the same work (identical or near-identical titles, same intent in different words).
- **Overlaps**: issues that are distinct but would likely be built together or partly supersede each other (e.g. "clear the filter" and "filter pill context menu with a clear option").

Only flag them. Do not merge, close, or edit issues for this step.

## Step 5: Present in chat

Use this layout:

```
**<N> issues from <scope>**, grouped into <M> topics.

### <Topic name> (<count>)
- `ID` Title
- `ID` Title

### <Topic name> (<count>)
...

### Duplicates & overlaps
- **Duplicate:** `P-7` and `P-38` (same title)
- **Overlap:** `P-13`, `P-31`, `P-32` all touch context-pill filtering
```

Keep issue titles as written in Linear. Link IDs to their `url` when the interface renders links. Skip the duplicates section if there are none.

End with one line offering write-back, e.g. "Want me to apply these as topic labels or create parent issues in Linear?"

## Step 6: Write back to Linear (only on request)

Nothing gets written without an explicit yes. Before writing, show exactly what will change (label names to create, which issues get which label, or which parent issues will be created and which issues move under them) and ask for confirmation. The user can rename or reshuffle groups first; apply their edits.

Load the needed tools with `tool_search` (`save_issue`, `save_issue_label`, `list_issue_labels`).

### Option A: Topic labels

1. Check `list_issue_labels` (with `includeGroups: true`) so you reuse existing labels instead of creating near-duplicates.
2. Offer to put new labels under a label group such as `Topic` so they stay separate from type labels like `Feature`.
3. Create missing labels with `save_issue_label`.
4. Add the label to each issue with `save_issue`. Linear replaces the label set, so always send the issue's **existing labels plus the new one**; never drop labels the issue already had.

### Option B: Parent issues

1. Create one parent issue per group with `save_issue`, titled with the topic name, in the same team (and project, if the children share one). A short description listing the child IDs is helpful.
2. Set each child's `parentId` to its group's parent.
3. If a child already has a different parent, skip it and list it at the end rather than silently re-parenting it.

After writing, report what changed in a short list with links, plus anything skipped and why. If a call fails partway, say which issues were updated and which were not.
