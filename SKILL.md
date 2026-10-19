---
name: plane
description: "Arbeiten mit Plane (Projekt- und Aufgabenboard, z. B. plane.udk.digital/genki): Aufgaben lesen, anlegen, Status ändern, Unteraufgaben, Links, Relationen, Kommentare, Wochenüberblick. Nutzen, sobald es um Plane, Work Items, Tickets, Aufgaben im Lab-Board, „was ist offen“, „trag das in Plane ein“ oder Kennungen wie GENKILAB-6 / INFRA-13 geht."
metadata:
  version: "0.1"
  stand: "2026-10-20"
  getestet_mit: "Plane 1.4.2 Community Edition (selbst gehostet)"
---

# Plane

Plane ist das Aufgabenboard des GenKI Lab: https://plane.udk.digital/genki/

## Einrichtung (einmal pro Person)

1. In Plane: Profil → Settings → **API Tokens** → Token anlegen (am besten mit Ablaufdatum).
   Der Token hat dieselben Rechte wie dein Account – nicht teilen, nicht in Repos oder Doku schreiben.
2. Datei `~/.config/plane.json` anlegen (`chmod 600`):
   ```json
   {"PLANE_API_KEY": "plane_api_…", "PLANE_WORKSPACE_SLUG": "genki", "PLANE_BASE_URL": "https://plane.udk.digital"}
   ```
   Alternativ als Umgebungsvariablen, oder der MCP-Eintrag `plane` (siehe unten) wird mitgelesen.
3. Test: `python3 <skill-ordner>/plane.py projects`

Optional zusätzlich der offizielle MCP-Server (`uvx plane-mcp-server stdio`, gleiche drei Variablen).
Für die Alltagsarbeit reicht `plane.py` – es umgeht die Lücken des MCP auf unserer Version (siehe unten).

## Werkzeug: `plane.py`

Aufgaben werden immer über ihre Kennung angesprochen (`GENKILAB-6`), Personen über den
Anzeigenamen (`vorname.nachname`, `anderer.name`), Status über den Namen (`Todo`, `In Progress`, `Done`).

| Zweck | Befehl |
|---|---|
| Projekte | `plane.py projects` |
| Mitglieder | `plane.py members` |
| Status eines Projekts | `plane.py states GENKILAB` |
| Aufgaben (Unteraufgaben eingerückt) | `plane.py list GENKILAB [--open] [--mine]` |
| Eine Aufgabe komplett | `plane.py show GENKILAB-6` (Unteraufgaben, Links, Relationen, Kommentare) |
| Anlegen | `plane.py create GENKILAB "Titel" --parent GENKILAB-6 --state Todo --assign vorname.nachname --desc "<p>…</p>" --priority high --due 2026-11-01` |
| Ändern | `plane.py update GENKILAB-11 --state Done` · `--assign` / `--unassign` · `--name` · `--desc` · `--parent` |
| Link anhängen | `plane.py link GENKILAB-8 https://github.com/… "Repo"` |
| Relation | `plane.py relate GENKILAB-10 relates_to INFRA-13 INFRA-16` |
| Kommentar | `plane.py comment GENKILAB-8 "Text" [--mention anderer.name]` |
| Was hat sich getan | `plane.py changes --days 7` |

Relationstypen: `relates_to`, `blocking`, `blocked_by`, `duplicate`, `start_before`, `start_after`,
`finish_before`, `finish_after`.

## So arbeiten wir in Plane

- **Ein Ding = ein Work Item.** Mehrere Punkte nicht als Liste in die Beschreibung schreiben,
  sondern als **Unteraufgaben** (`--parent`). Die Sammelaufgabe bekommt nur einen Satz Beschreibung.
- **Status pflegen** statt „erledigt“ in den Text zu schreiben: Backlog → Todo → In Progress → Done (oder Cancelled).
- **Links** (Repo, Doku, Figma …) als Link anhängen, nicht in den Text.
- **Zusammenhänge** zwischen Aufgaben (auch über Projekte hinweg, z. B. GENKILAB ↔ INFRA) als Relation.
- **Fragen an Leute** als Kommentar mit Erwähnung, damit sie benachrichtigt werden.
- Beschreibungen kurz und in der Sprache des Teams – nicht nach KI klingen: keine Überschriften,
  keine fetten Status-Zeilen, schlichte Listen.

## Regeln für Agents

- **Erst lesen, dann schreiben.** Vor jeder Änderung `show` ausführen.
- **Fremde Aufgaben nicht umbauen** (Text, Status, Zuständige), ohne dass der Mensch es ausdrücklich will.
  Eigene Aufgaben (wo man selbst zuständig ist) nach Absprache.
- **Vor dem Überschreiben einer Beschreibung** den alten Text sichern – `update --desc` ersetzt sie komplett.
- **Kommentare und Erwähnungen** benachrichtigen echte Menschen – nur nach Freigabe posten.
- **Nichts löschen.** Lieber Status `Cancelled`.
- Nach dem Schreiben mit `show` / `list` prüfen, ob es angekommen ist.

## Was auf unserer Version (1.4.2 Community) geht – und was nicht

Geht über API/`plane.py`: Work Items, Unteraufgaben, Status, Zuständige, Priorität, Fälligkeit,
Labels, Links, Relationen, Kommentare, Verlauf (activities), Anhänge, Cycles, Module, Intake, Suche.

Gibt es nicht (nur Plane Pro/Cloud, API antwortet 404): Pages, Work-Item-Typen, Schätzungen,
Zeiterfassung (Worklogs), Meilensteine, Initiativen, Releases, eigene Relationstypen.

Lücken im MCP-Server `plane-mcp-server` auf dieser Version:
- `workitem list` geht nur mit `project_id` (ohne → 404)
- PQL-Filter (`pql=…`) und `count` → 404
- `workitem_relation` → 404 (der Pfad passt nicht zu 1.4.2)
Deshalb für Listen, Filter und Relationen `plane.py` nehmen.

Weitere Eigenheiten:
- Projekte, in denen man nicht Mitglied ist, liefern 403 – `plane.py` blendet sie aus.
- Relationen kommen als `{project_id, issue_id}` zurück, nicht als reine ID.
- `parent=` als Filter in der Liste wird ignoriert – `plane.py` filtert selbst.
