#!/usr/bin/env python3
"""plane.py — kleines CLI für Plane (getestet mit Plane 1.4.2 Community, plane.udk.digital).

Nur Python-Standardbibliothek. Token + Workspace aus Umgebung oder ~/.config/plane.json:
  PLANE_API_KEY, PLANE_WORKSPACE_SLUG (z. B. genki), PLANE_BASE_URL (z. B. https://plane.udk.digital)
Fallback: der MCP-Eintrag "plane" in ~/.config/mcp/mcp.json.

Aufgaben werden überall per Kennung angesprochen, z. B. GENKILAB-6.

  plane.py projects                         Projekte
  plane.py members                          Mitglieder (Name → ID)
  plane.py states PROJ                      Status eines Projekts
  plane.py list PROJ [--open] [--mine]      Aufgaben eines Projekts
  plane.py show GENKILAB-6                  Aufgabe mit Unteraufgaben, Links, Relationen, Kommentaren
  plane.py create PROJ "Titel" [--parent GENKILAB-6] [--state "In Progress"] [--assign vorname.nachname]
                    [--desc "<p>…</p>"] [--priority high] [--due 2026-11-01]
  plane.py update GENKILAB-7 [--name …] [--state Done] [--assign …] [--unassign …] [--desc …] [--parent …]
  plane.py link GENKILAB-7 URL [Titel]      Link anhängen
  plane.py relate GENKILAB-7 relates_to INFRA-13   (relates_to|blocking|blocked_by|duplicate|
                                                    start_before|start_after|finish_before|finish_after)
  plane.py comment GENKILAB-7 "Text" [--mention anderer.name]
  plane.py changes [--days 7]               alles, was sich zuletzt geändert hat (alle Projekte)
"""
import argparse, json, os, re, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from html import escape


# ---------- Verbindung ----------
def config():
    c = {k: os.environ.get(k, "") for k in ("PLANE_API_KEY", "PLANE_WORKSPACE_SLUG", "PLANE_BASE_URL")}
    for f in ("~/.config/plane.json", "~/.config/mcp/mcp.json"):
        p = os.path.expanduser(f)
        if all(c.values()) or not os.path.exists(p):
            continue
        d = json.load(open(p))
        d = d.get("mcpServers", {}).get("plane", {}).get("env", d)
        for k in c:
            c[k] = c[k] or d.get(k, "")
    if not c["PLANE_API_KEY"] or not c["PLANE_WORKSPACE_SLUG"]:
        sys.exit("PLANE_API_KEY und PLANE_WORKSPACE_SLUG fehlen (Umgebung oder ~/.config/plane.json)")
    c["PLANE_BASE_URL"] = (c["PLANE_BASE_URL"] or "https://api.plane.so").rstrip("/")
    return c


C = None


class PlaneFehler(Exception):
    def __init__(self, code, msg):
        super().__init__(msg); self.code = code


def api(method, path, data=None, query=None, workspace=True):
    global C
    C = C or config()
    base = f"{C['PLANE_BASE_URL']}/api/v1/" + (f"workspaces/{C['PLANE_WORKSPACE_SLUG']}/" if workspace else "")
    url = base + path.lstrip('/')
    if query:
        url += "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(url, method=method, data=json.dumps(data).encode() if data is not None else None,
                                 headers={"X-API-Key": C["PLANE_API_KEY"], "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise PlaneFehler(e.code, f"Plane-API {e.code} bei {method} {path}: {e.read().decode()[:300]}")


def alle(path, query=None):
    """Alle Seiten einer Liste holen."""
    q, out = dict(query or {}, per_page=100), []
    while True:
        d = api("GET", path, query=q)
        if isinstance(d, list):
            return d
        out += d.get("results", [])
        if not d.get("next_page_results"):
            return out
        q["cursor"] = d["next_cursor"]


# ---------- Nachschlagen ----------
_cache = {}


def projekte():
    """Nur Projekte, in denen man Mitglied ist (andere liefern 403)."""
    if "p" not in _cache:
        ok = []
        for p in alle("projects/"):
            try:
                zustaende(p["id"]); ok.append(p)
            except PlaneFehler as e:
                if e.code not in (403, 404):
                    raise
        _cache["p"] = ok
    return _cache["p"]


def projekt(kennung):
    for p in projekte():
        if kennung.upper() in (p["identifier"].upper(), p["name"].upper()) or kennung == p["id"]:
            return p
    sys.exit(f"Projekt {kennung} nicht gefunden: " + ", ".join(p["identifier"] for p in projekte()))


def mitglieder():
    if "m" not in _cache:
        _cache["m"] = alle("members/")
    return _cache["m"]


def mitglied(name):
    n = name.lower().lstrip("@")
    for m in mitglieder():
        if n in (m["id"], (m.get("display_name") or "").lower(), (m.get("email") or "").lower(),
                 (m.get("first_name") or "").lower()):
            return m
    sys.exit(f"Mitglied {name} nicht gefunden: " + ", ".join(m["display_name"] for m in mitglieder()))


def name_von(uid):
    return next((m["display_name"] for m in mitglieder() if m["id"] == uid), uid[:8])


def zustaende(pid):
    k = "s" + pid
    if k not in _cache:
        _cache[k] = alle(f"projects/{pid}/states/")
    return _cache[k]


def zustand(pid, name):
    for s in zustaende(pid):
        if s["name"].lower() == name.lower() or s["group"] == name.lower():
            return s
    sys.exit(f"Status {name} nicht gefunden: " + ", ".join(s["name"] for s in zustaende(pid)))


def aufgabe(kennung):
    """GENKILAB-6 → (projekt, work item)."""
    m = re.fullmatch(r"([A-Za-z0-9]+)-(\d+)", kennung.strip())
    if not m:
        sys.exit(f"Kennung wie GENKILAB-6 erwartet, nicht {kennung}")
    p = projekt(m.group(1))
    for w in alle(f"projects/{p['id']}/work-items/"):
        if w["sequence_id"] == int(m.group(2)):
            return p, w
    sys.exit(f"{kennung} nicht gefunden")


def kenn(p, w):
    return f"{p['identifier']}-{w['sequence_id']}"


def text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


# ---------- Befehle ----------
def cmd_projects(a):
    for p in projekte():
        print(f"{p['identifier']:<12} {p['name']}")


def cmd_members(a):
    for m in mitglieder():
        print(f"{m['display_name']:<14} {m.get('first_name') or '':<22} {m['id']}")


def cmd_states(a):
    for s in zustaende(projekt(a.projekt)["id"]):
        print(f"{s['name']:<14} {s['group']}")


def cmd_list(a):
    p = projekt(a.projekt)
    st = {s["id"]: s for s in zustaende(p["id"])}
    me = api("GET", "users/me/", workspace=False)["id"] if a.mine else None
    for w in sorted(alle(f"projects/{p['id']}/work-items/"), key=lambda w: w["sequence_id"]):
        s = st.get(w["state"], {})
        if a.open and s.get("group") in ("completed", "cancelled"):
            continue
        if me and me not in w["assignees"]:
            continue
        einr = "  ↳ " if w.get("parent") else ""
        print(f"{einr}{kenn(p, w):<14} {s.get('name', '?'):<12} {w['name']}  [{', '.join(map(name_von, w['assignees']))}]")


def cmd_show(a):
    p, w = aufgabe(a.kennung)
    pid, wid = p["id"], w["id"]
    st = {s["id"]: s["name"] for s in zustaende(pid)}
    print(f"{kenn(p, w)}  {w['name']}\nStatus: {st.get(w['state'])} · Priorität: {w['priority']} · "
          f"Zuständig: {', '.join(map(name_von, w['assignees'])) or '–'} · Fällig: {w.get('target_date') or '–'}")
    if w.get("parent"):
        par = api("GET", f"projects/{pid}/work-items/{w['parent']}/")
        print(f"Gehört zu: {kenn(p, par)} {par['name']}")
    if text(w.get("description_html")):
        print("\n" + text(w["description_html"]))
    kinder = alle(f"projects/{pid}/work-items/", {"parent": wid})
    kinder = [k for k in kinder if k.get("parent") == wid]
    if kinder:
        print("\nUnteraufgaben:")
        for k in sorted(kinder, key=lambda k: k["sequence_id"]):
            print(f"  {kenn(p, k):<14} {st.get(k['state'], '?'):<12} {k['name']}")
    links = alle(f"projects/{pid}/work-items/{wid}/links/")
    if links:
        print("\nLinks:")
        for l in links:
            print(f"  {l.get('title') or ''} {l['url']}")
    rel = api("GET", f"projects/{pid}/work-items/{wid}/relations/")
    rel = {k: v for k, v in rel.items() if v}
    if rel:
        print("\nRelationen:")
        idx = {x["id"]: (pp, x) for pp in projekte() for x in alle(f"projects/{pp['id']}/work-items/")}
        for typ, ids in rel.items():
            for i in ids:
                i = i.get("issue_id") if isinstance(i, dict) else i  # Plane 1.4 liefert {project_id, issue_id}
                pp, x = idx.get(i, (None, None))
                print(f"  {typ:<13} {kenn(pp, x) + ' ' + x['name'] if x else i}")
    kom = alle(f"projects/{pid}/work-items/{wid}/comments/")
    if kom:
        print("\nKommentare:")
        for k in kom:
            print(f"  {name_von(k.get('actor') or k.get('created_by'))} ({k['created_at'][:10]}): {text(k.get('comment_html'))}")


def felder(a, pid):
    d = {}
    if getattr(a, "name", None):
        d["name"] = a.name
    if a.state:
        d["state"] = zustand(pid, a.state)["id"]
    if a.desc is not None:
        d["description_html"] = a.desc if a.desc.lstrip().startswith("<") else f"<p>{escape(a.desc)}</p>"
    if a.priority:
        d["priority"] = a.priority
    if a.due:
        d["target_date"] = a.due
    if a.parent:
        d["parent"] = aufgabe(a.parent)[1]["id"]
    return d


def cmd_create(a):
    p = projekt(a.projekt)
    d = felder(a, p["id"])
    d["name"] = a.titel
    d["assignees"] = [mitglied(x)["id"] for x in a.assign or []]
    w = api("POST", f"projects/{p['id']}/work-items/", d)
    print(f"angelegt: {kenn(p, w)} {w['name']}")


def cmd_update(a):
    p, w = aufgabe(a.kennung)
    d = felder(a, p["id"])
    if a.assign or a.unassign:
        ids = set(w["assignees"]) | {mitglied(x)["id"] for x in a.assign or []}
        d["assignees"] = sorted(ids - {mitglied(x)["id"] for x in a.unassign or []})
    if not d:
        sys.exit("nichts zu ändern")
    w = api("PATCH", f"projects/{p['id']}/work-items/{w['id']}/", d)
    print(f"geändert: {kenn(p, w)} ({', '.join(d)})")


def cmd_link(a):
    p, w = aufgabe(a.kennung)
    api("POST", f"projects/{p['id']}/work-items/{w['id']}/links/", {"url": a.url, "title": a.titel or a.url})
    print(f"Link an {kenn(p, w)}: {a.url}")


def cmd_relate(a):
    p, w = aufgabe(a.kennung)
    ziele = [aufgabe(k)[1]["id"] for k in a.ziele]
    api("POST", f"projects/{p['id']}/work-items/{w['id']}/relations/", {"relation_type": a.typ, "issues": ziele})
    print(f"{kenn(p, w)} {a.typ} {', '.join(a.ziele)}")


def cmd_comment(a):
    p, w = aufgabe(a.kennung)
    html = f"<p>{escape(a.text)}</p>"
    if a.mention:
        html = "<p>" + " ".join(
            f'<mention-component entity_identifier="{mitglied(m)["id"]}" entity_name="user_mention"></mention-component>'
            for m in a.mention) + f" {escape(a.text)}</p>"
    api("POST", f"projects/{p['id']}/work-items/{w['id']}/comments/", {"comment_html": html})
    print(f"Kommentar an {kenn(p, w)}")


def aenderungen(tage=7):
    """Alle Aufgaben, die in den letzten `tage` Tagen geändert wurden, mit Projekt + Status."""
    seit = datetime.now(timezone.utc) - timedelta(days=tage)
    out = []
    for p in projekte():
        st = {s["id"]: s for s in zustaende(p["id"])}
        for w in alle(f"projects/{p['id']}/work-items/"):
            w["_projekt"], w["_kennung"] = p, kenn(p, w)
            w["_status"] = st.get(w["state"], {"name": "?", "group": "?"})
            w["_neu"] = datetime.fromisoformat(w["created_at"].replace("Z", "+00:00")) >= seit
            w["_geaendert"] = datetime.fromisoformat(w["updated_at"].replace("Z", "+00:00")) >= seit
            out.append(w)
    return out


def cmd_changes(a):
    for w in aenderungen(a.days):
        if w["_geaendert"]:
            print(f"{w['_kennung']:<14} {w['_status']['name']:<12} {'NEU ' if w['_neu'] else ''}{w['name']}")


def main():
    try:
        _main()
    except PlaneFehler as e:
        sys.exit(str(e))


def _main():
    ap = argparse.ArgumentParser(description="Plane-CLI", formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog=__doc__)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("projects"); sp.add_parser("members")
    s = sp.add_parser("states"); s.add_argument("projekt")
    s = sp.add_parser("list"); s.add_argument("projekt"); s.add_argument("--open", action="store_true"); s.add_argument("--mine", action="store_true")
    s = sp.add_parser("show"); s.add_argument("kennung")
    for n in ("create", "update"):
        s = sp.add_parser(n)
        if n == "create":
            s.add_argument("projekt"); s.add_argument("titel")
        else:
            s.add_argument("kennung"); s.add_argument("--name"); s.add_argument("--unassign", nargs="+")
        s.add_argument("--state"); s.add_argument("--desc"); s.add_argument("--priority"); s.add_argument("--due")
        s.add_argument("--parent"); s.add_argument("--assign", nargs="+")
    s = sp.add_parser("link"); s.add_argument("kennung"); s.add_argument("url"); s.add_argument("titel", nargs="?")
    s = sp.add_parser("relate"); s.add_argument("kennung"); s.add_argument("typ"); s.add_argument("ziele", nargs="+")
    s = sp.add_parser("comment"); s.add_argument("kennung"); s.add_argument("text"); s.add_argument("--mention", nargs="+")
    s = sp.add_parser("changes"); s.add_argument("--days", type=int, default=7)
    a = ap.parse_args()
    globals()["cmd_" + a.cmd](a)


if __name__ == "__main__":
    main()
