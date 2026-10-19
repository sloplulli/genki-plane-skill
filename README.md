# Plane-Skill (GenKI Lab)

Werkzeuge, damit Agents (pi, Claude Code …) und Menschen sauber mit unserem Plane arbeiten:
https://plane.udk.digital/genki/

- `SKILL.md` – Skill für Agents: Einrichtung, Befehle, wie wir in Plane arbeiten, was auf Plane 1.4.2 (Community) geht und was nicht
- `plane.py` – CLI: Aufgaben lesen, anlegen, ändern, Unteraufgaben, Links, Relationen, Kommentare, Änderungen der Woche

Nur Python-Standardbibliothek, keine Installation nötig.

## Einrichten

1. In Plane: Profil → Settings → API Tokens → eigenen Token anlegen
2. `~/.config/plane.json` (chmod 600):
   ```json
   {"PLANE_API_KEY": "plane_api_…", "PLANE_WORKSPACE_SLUG": "genki", "PLANE_BASE_URL": "https://plane.udk.digital"}
   ```
3. `python3 plane.py projects`

**Als Skill:** Ordner nach `~/.pi/agent/skills/plane/` (pi) oder `~/.claude/skills/plane/` (Claude Code) kopieren oder verlinken.
