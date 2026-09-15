#!/usr/bin/env python3
"""Build the static CareerBot job dashboard.

Inputs
  ../current-shortlist.md   -> today's numbered leads (awaiting decision / submitted / skipped)
  applications.json         -> snapshot of Supabase public.job_applications (source of truth)

Output
  site/index.html           -> single self-contained page, published via GitHub Pages
"""

import json
import re
import html
import pathlib
import datetime

HERE = pathlib.Path(__file__).resolve().parent
SHORTLIST = HERE.parent / "current-shortlist.md"
APPS = HERE / "applications.json"
OUT = HERE / "site" / "index.html"


def parse_shortlist(text):
    generated = ""
    m = re.search(r"^Generated:\s*(.+)$", text, re.M)
    if m:
        generated = m.group(1).strip()

    leads = []
    blocks = re.split(r"^## (?=\d+\.)", text, flags=re.M)[1:]
    for block in blocks:
        head, _, body = block.partition("\n")
        num, _, title = head.partition(".")
        company, sep, role = title.partition("—")
        if not sep:
            company, sep, role = title.partition("-")
        lead = {
            "num": num.strip(),
            "company": company.strip(),
            "role": role.strip(),
        }
        for key in ("Location", "Salary", "Source", "Job ID", "URL", "Posted",
                    "Fit", "Concern", "Status"):
            fm = re.search(r"^- %s:\s*(.+)$" % re.escape(key), body, re.M)
            if fm:
                lead[key.lower().replace(" ", "_")] = fm.group(1).strip()
        leads.append(lead)

    excluded = []
    em = re.search(r"## Excluded this run.*?\n(.*)$", text, re.S)
    if em:
        for line in em.group(1).splitlines():
            line = line.strip()
            if line.startswith("- "):
                excluded.append(line[2:].strip())
    return generated, leads, excluded


def md_bold(s):
    """Escape then re-enable **bold** from the markdown source."""
    s = html.escape(s)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)


def card_lead(lead):
    status = lead.get("status", "awaiting decision").lower()
    pill = {"awaiting decision": "wait", "submitted": "done", "skipped": "skip"}.get(status, "wait")
    url = lead.get("url", "")
    title = html.escape(lead["role"])
    if url:
        title = f'<a href="{html.escape(url)}" target="_blank" rel="noopener">{title}</a>'
    meta = []
    for label, key in (("", "location"), ("", "salary"), ("Posted", "posted"),
                       ("Source", "source"), ("Job ID", "job_id")):
        if lead.get(key):
            v = html.escape(lead[key])
            meta.append(f'<span class="m">{label + " " if label else ""}{v}</span>')
    notes = ""
    if lead.get("fit"):
        notes += f'<p class="fit"><b>Fit</b> {html.escape(lead["fit"])}</p>'
    if lead.get("concern"):
        notes += f'<p class="concern"><b>Concern</b> {html.escape(lead["concern"])}</p>'
    return f"""      <article class="card lead">
        <div class="row"><span class="num">{html.escape(lead['num'])}</span>
          <span class="pill {pill}">{html.escape(status)}</span></div>
        <h3>{title}</h3>
        <p class="co">{html.escape(lead['company'])}</p>
        <div class="metas">{''.join(meta)}</div>
        <details><summary>Why / watch out</summary>{notes}</details>
        <p class="cmd">Reply to CareerBot: <code>Apply {html.escape(lead['num'])}</code></p>
      </article>"""


def card_app(app):
    title = html.escape(app["role"])
    if app.get("url"):
        title = f'<a href="{html.escape(app["url"])}" target="_blank" rel="noopener">{title}</a>'
    meta = []
    for key, label in (("location", ""), ("salary", ""), ("job_id", "Job ID"), ("source", "Source")):
        if app.get(key):
            meta.append(f'<span class="m">{(label + " ") if label else ""}{html.escape(str(app[key]))}</span>')
    return f"""      <article class="card app">
        <div class="row"><span class="date">{html.escape(app.get('date_applied') or 'unknown')}</span>
          <span class="pill done">{html.escape(app.get('status') or 'unknown')}</span></div>
        <h3>{title}</h3>
        <p class="co">{html.escape(app['company'])}</p>
        <div class="metas">{''.join(meta)}</div>
      </article>"""


def build():
    text = SHORTLIST.read_text(encoding="utf-8")
    generated, leads, excluded = parse_shortlist(text)
    apps = json.loads(APPS.read_text(encoding="utf-8"))

    by_status = {}
    for a in apps:
        by_status.setdefault((a.get("status") or "unknown").lower(), []).append(a)
    applied = sorted(by_status.get("applied", []), key=lambda a: a.get("date_applied") or "", reverse=True)
    interviewing = by_status.get("interviewing", []) + by_status.get("phone screen", [])
    offers = by_status.get("offer", [])
    closed = by_status.get("rejected", []) + by_status.get("withdrawn", [])

    awaiting = [l for l in leads if l.get("status", "awaiting decision").lower() == "awaiting decision"]

    built = datetime.datetime.now().strftime("%Y-%m-%d %H:%M %Z").strip() or \
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    def column(key, title, cards, empty):
        body = "\n".join(cards) if cards else f'<p class="empty">{empty}</p>'
        return f"""    <section class="col {key}">
      <h2>{title}<span class="count">{len(cards)}</span></h2>
{body}
    </section>"""

    cols = "\n".join([
        column("wait", "Awaiting your decision", [card_lead(l) for l in awaiting],
               "No open leads — next shortlist lands at 7:00am PT."),
        column("applied", "Applied", [card_app(a) for a in applied], "Nothing submitted yet."),
        column("interviewing", "Interviewing", [card_app(a) for a in interviewing], "No interviews scheduled."),
        column("offer", "Offer / Closed", [card_app(a) for a in offers + closed], "Nothing here yet."),
    ])

    excl = "".join(f"<li>{md_bold(e)}</li>" for e in excluded)
    excl_block = f"""  <details class="excluded">
    <summary>Screened out this run ({len(excluded)})</summary>
    <ul>{excl}</ul>
  </details>""" if excluded else ""

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#0f1117">
<title>CareerBot — Job Board</title>
<style>
  :root {{
    --bg:#0f1117; --card:#1a1d27; --card2:#222534; --border:#2a2d3a;
    --text:#e1e4ed; --muted:#8a90a6; --blue:#60a5fa; --orange:#f59e0b;
    --cyan:#22d3ee; --green:#34d399; --red:#f87171;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; -webkit-text-size-adjust:100%; }}
  body {{
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
    background:var(--bg); color:var(--text); line-height:1.45;
    padding:env(safe-area-inset-top) 16px 48px; padding-top:20px;
  }}
  header {{ border-bottom:1px solid var(--border); padding-bottom:14px; margin-bottom:18px; }}
  header h1 {{ font-size:1.35rem; letter-spacing:-.02em; color:#fff; }}
  header .sub {{ font-size:.78rem; color:var(--muted); margin-top:6px; }}
  .stats {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:12px; }}
  .stat {{ background:var(--card); border:1px solid var(--border); border-radius:10px;
          padding:8px 12px; min-width:84px; }}
  .stat b {{ display:block; font-size:1.25rem; color:#fff; }}
  .stat span {{ font-size:.66rem; text-transform:uppercase; letter-spacing:.07em; color:var(--muted); }}
  .board {{ display:grid; grid-template-columns:1fr; gap:14px; }}
  @media (min-width:900px) {{ .board {{ grid-template-columns:repeat(4,1fr); align-items:start; }} }}
  .col {{ background:var(--card); border:1px solid var(--border); border-radius:14px; padding:12px; }}
  .col h2 {{ font-size:.74rem; text-transform:uppercase; letter-spacing:.09em;
            color:var(--muted); display:flex; justify-content:space-between;
            align-items:center; padding-bottom:9px; margin-bottom:11px;
            border-bottom:1px solid var(--border); }}
  .col .count {{ background:var(--border); color:var(--text); border-radius:10px;
                padding:1px 8px; font-size:.7rem; }}
  .col.wait h2 {{ color:var(--blue); }}
  .col.applied h2 {{ color:var(--orange); }}
  .col.interviewing h2 {{ color:var(--cyan); }}
  .col.offer h2 {{ color:var(--green); }}
  .card {{ background:var(--card2); border:1px solid #2d3142; border-radius:10px;
          padding:11px 12px; margin-bottom:9px; }}
  .card:last-child {{ margin-bottom:0; }}
  .card h3 {{ font-size:.92rem; font-weight:650; line-height:1.3; margin:5px 0 2px; }}
  .card h3 a {{ color:var(--text); text-decoration:none; border-bottom:1px solid #3d4258; }}
  .card .co {{ font-size:.8rem; color:var(--blue); font-weight:600; margin-bottom:7px; }}
  .row {{ display:flex; justify-content:space-between; align-items:center; gap:8px; }}
  .num {{ font-size:.72rem; font-weight:800; color:var(--muted); }}
  .date {{ font-size:.7rem; color:var(--muted); font-variant-numeric:tabular-nums; }}
  .pill {{ font-size:.6rem; font-weight:800; text-transform:uppercase; letter-spacing:.06em;
          padding:2px 7px; border-radius:999px; white-space:nowrap; }}
  .pill.wait {{ background:rgba(96,165,250,.15); color:var(--blue); }}
  .pill.done {{ background:rgba(245,158,11,.15); color:var(--orange); }}
  .pill.skip {{ background:rgba(138,144,166,.15); color:var(--muted); }}
  .metas {{ display:flex; flex-wrap:wrap; gap:5px; }}
  .m {{ font-size:.68rem; color:var(--muted); background:rgba(255,255,255,.04);
       border:1px solid var(--border); border-radius:6px; padding:1px 6px; }}
  details {{ margin-top:9px; }}
  summary {{ font-size:.72rem; color:var(--muted); cursor:pointer; list-style:none; }}
  summary::-webkit-details-marker {{ display:none; }}
  summary::before {{ content:"▸ "; }}
  details[open] summary::before {{ content:"▾ "; }}
  details p {{ font-size:.76rem; color:#b6bccd; margin-top:7px; }}
  .fit b {{ color:var(--green); }}
  .concern b {{ color:var(--red); }}
  .cmd {{ font-size:.7rem; color:var(--muted); margin-top:9px;
         border-top:1px dashed var(--border); padding-top:7px; }}
  .cmd code {{ background:rgba(96,165,250,.14); color:var(--blue);
              padding:1px 6px; border-radius:5px; font-weight:700; }}
  .empty {{ font-size:.76rem; color:var(--muted); padding:8px 2px; }}
  .excluded {{ margin-top:22px; background:var(--card); border:1px solid var(--border);
              border-radius:14px; padding:12px 14px; }}
  .excluded ul {{ margin:10px 0 0 18px; }}
  .excluded li {{ font-size:.76rem; color:#aab0c2; margin-bottom:7px; }}
  footer {{ margin-top:26px; font-size:.7rem; color:var(--muted); line-height:1.6;
           border-top:1px solid var(--border); padding-top:12px; }}
</style>
</head>
<body>
<header>
  <h1>CareerBot — Job Board</h1>
  <div class="sub">Shortlist generated {html.escape(generated)}<br>Page built {html.escape(built)} · source of truth: Supabase <code>job_applications</code></div>
  <div class="stats">
    <div class="stat"><b>{len(awaiting)}</b><span>Awaiting you</span></div>
    <div class="stat"><b>{len(applied)}</b><span>Applied</span></div>
    <div class="stat"><b>{len(interviewing)}</b><span>Interviewing</span></div>
    <div class="stat"><b>{len(offers)}</b><span>Offers</span></div>
  </div>
</header>
<main class="board">
{cols}
</main>
{excl_block}
<footer>
  Decisions happen in Telegram, not here — this page is read-only.<br>
  CareerBot never applies without your explicit per-role approval.
</footer>
</body>
</html>
"""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT} ({len(page)} bytes)")
    print(f"leads awaiting={len(awaiting)} applied={len(applied)} "
          f"interviewing={len(interviewing)} offers={len(offers)} excluded={len(excluded)}")


if __name__ == "__main__":
    build()
