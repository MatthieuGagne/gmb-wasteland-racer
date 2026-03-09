---
name: prd
description: Use when creating a new PRD for a feature — creates the doc file and GitHub issue together and links them.
---

Create a new PRD and its linked GitHub issue.

## Steps

1. **Create the PRD file** at `docs/prd/YYYY-MM-DD-<feature-slug>-prd.md`.
   - Copy structure from `docs/prd/TEMPLATE.md`.
   - Fill in Goal, Requirements, and Acceptance Criteria from the user's description.
   - Leave `**Issue:**` blank for now.
   - Slug: lowercase, hyphens only, short (e.g. `enemy-spawning`, `hud-health-bar`).

2. **Create a GitHub issue** with the full PRD content as the body:
   ```sh
   gh issue create --title "feat: <feature name>" --body "$(cat docs/prd/YYYY-MM-DD-<feature-slug>-prd.md)"
   ```
   Capture the issue number from the URL in the output.

3. **Update the PRD** — set `**Issue:** #N` with the captured number. Then edit the issue to include the updated issue number:
   ```sh
   gh issue edit N --body "$(cat docs/prd/YYYY-MM-DD-<feature-slug>-prd.md)"
   ```

4. Report the PRD path and issue URL to the user.
