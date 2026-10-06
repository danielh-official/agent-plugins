# calslashd skill

Mirrors the calorie-budget calculations of the [CalSlashD](https://calslashd.app) iOS app for an AI with Apple Health access. Standalone: it never reads the CalSlashD app, only Apple Health (with your permission) and the settings you tell it. One skill folder: `skills/calslashd/`.

Needs a host with Apple Health access (Claude or ChatGPT on iOS). Desktop/web has no Health, so it only works there from a snapshot the Claude/ChatGPT iOS app saved to memory (unverified whether memory carries over; otherwise iOS only).

Install:
- **Claude Code:** `claude plugin marketplace add danielh-official/agent-plugins`, then `claude plugin install calslashd@danielh-official-plugins`.
- **claude.ai / Claude iOS:** zip `skills/calslashd/` and upload under Settings → Capabilities → Skills.
- **ChatGPT:** paste `SKILL.md` body into a Project/GPT instructions.

Test: `python3 skills/calslashd/scripts/selfcheck.py`
