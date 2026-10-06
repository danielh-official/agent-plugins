# calslashd skill

Lets an AI with Apple Health access reproduce [CalSlashD](https://calslashd.app) stats deterministically. One skill folder: `skills/calslashd/`.

Needs a host with Apple Health access (Claude or ChatGPT on iOS). Desktop/web has no Health, so it only works there from a snapshot the iOS app saved to memory (unverified whether memory carries over; otherwise iOS only).

Install:
- **Claude Code:** `claude plugin marketplace add danielh-official/agent-plugins`, then `claude plugin install calslashd@danielh-official-plugins`.
- **claude.ai / Claude iOS:** zip `skills/calslashd/` and upload under Settings → Capabilities → Skills.
- **ChatGPT:** paste `SKILL.md` body into a Project/GPT instructions.

Test: `python3 skills/calslashd/scripts/selfcheck.py`
