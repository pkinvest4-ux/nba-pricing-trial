"""Injury information known by the END OF THE DAY BEFORE each game (Jaden's rule).

Source: the NBA's official injury report, published hourly; the file for hour HH goes up at HH:30 ET.
For a game on day D we read only the last report of day D-1 (8:30 PM). If it already lists the team's
game on D, we use those rows. If not, we carry forward the team's statuses from its most recent game
before D, which were already announced. Nothing published on game day is used.
After Dec 21, 2025 the NBA's own addresses stop working, so the latest report of the evening comes from a
research archive of the original PDFs (see archive_reports). If no report exists, the game is marked unknown.
Needs `pdftotext` (poppler). Writes data/injuries.json: {game_id: {team: {"First Last": status}}}.
"""
import json, re, pathlib, subprocess, tempfile, urllib.request, concurrent.futures as cf
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from common import UA

SEASONS = ("2021-22", "2022-23", "2023-24", "2024-25", "2025-26")
ET = ZoneInfo("America/New_York")
CACHE = pathlib.Path("data/injury_reports")
URL = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_{day}_{hh}.pdf"
LAST_REPORTS = ("08PM", "07PM", "06PM")  # latest of the evening that exists

TEAMS = {
    "Atlanta Hawks": "ATL", "Boston Celtics": "BOS", "Brooklyn Nets": "BKN", "Charlotte Hornets": "CHA",
    "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE", "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN",
    "Detroit Pistons": "DET", "Golden State Warriors": "GS", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Clippers": "LAC", "Los Angeles Lakers": "LAL", "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA", "Milwaukee Bucks": "MIL", "Minnesota Timberwolves": "MIN", "New Orleans Pelicans": "NO",
    "New York Knicks": "NY", "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI",
    "Phoenix Suns": "PHX", "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC", "San Antonio Spurs": "SA",
    "Toronto Raptors": "TOR", "Utah Jazz": "UTAH", "Washington Wizards": "WSH",
}
TEAM_RE = re.compile("|".join(sorted(map(re.escape, TEAMS), key=len, reverse=True)))
MATCHUP_RE = re.compile(r"\b[A-Z]{2,4}@[A-Z]{2,4}\b")
DATE_RE = re.compile(r"(\d{2}/\d{2}/\d{4})")
ROW_RE = re.compile(r"([A-Z][A-Za-z'.\- ]+?, [A-Za-z'.\- ]+?)\s{2,}(Out|Doubtful|Questionable|Probable|Available)\b")


def blank(line, m):
    return line[:m.start()] + " " * (m.end() - m.start()) + line[m.end():]


def parse(text):
    """{game date 'MM/DD/YYYY': {team: {"First Last": status}}}"""
    out, date, tm = {}, None, None
    for line in text.splitlines():
        m = DATE_RE.match(line.strip())
        if m:
            date = m.group(1)
        t = TEAM_RE.search(line)
        if t:
            tm = TEAMS[t.group(0)]
            line = blank(line, t)  # so a team name can't glue onto a player's name
        for mu in list(MATCHUP_RE.finditer(line)):
            line = blank(line, mu)
        for name, status in ROW_RE.findall(line):
            last, first = [p.strip() for p in name.split(",", 1)]
            if date and tm:
                out.setdefault(date, {}).setdefault(tm, {})[f"{first} {last}"] = status
    return out


def evening_report(day):
    """Parsed last report published on `day` (YYYY-MM-DD), or None."""
    f = CACHE / f"{day}.json"
    if f.exists():
        return json.loads(f.read_text())
    for hh in LAST_REPORTS:
        try:
            req = urllib.request.Request(URL.format(day=day, hh=hh), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                pdf = r.read()
        except Exception:
            continue
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            tmp.write(pdf)
            tmp.flush()
            text = subprocess.run(["pdftotext", "-layout", tmp.name, "-"], capture_output=True, text=True).stdout
        parsed = {"published": f"{day} {hh}:30", "rows": parse(text)}
        f.write_text(json.dumps(parsed))
        return parsed
    f.write_text(json.dumps(None))
    return None


ARCHIVE_ZIP = pathlib.Path("data/third_party/nba-official-reports-2026.zip")
ARCHIVE_MAP = pathlib.Path("data/third_party/map_2026.json")
NAME_RE = re.compile(r"Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{2})(?:_(\d{2}))?(AM|PM)\.pdf")


def published_minutes(hh, mm, ampm):
    """Minutes after midnight ET. Hourly files (old naming, '08PM') go up at HH:30;
    the quarter-hour files used from late December 2025 ('06_45PM') at the time in the name."""
    h = int(hh) % 12 + (12 if ampm == "PM" else 0)
    return h * 60 + (int(mm) if mm is not None else 30)


def archive_reports():
    """The latest report published each day, from a research archive of the NBA's original PDFs
    (github.com/niksmdmarketing/NFLFutures, release 'nba-official-reports'). It fills the period after
    Dec 21, 2025, when the NBA's own addresses stop working. Checked in WRITEUP: every file matches its
    sha256, and the 30 files that overlap with reports we downloaded from the NBA parse identically."""
    if not (ARCHIVE_ZIP.exists() and ARCHIVE_MAP.exists()):
        return {}
    import zipfile
    z, mapping, latest = zipfile.ZipFile(ARCHIVE_ZIP), json.loads(ARCHIVE_MAP.read_text()), {}
    for fn, info in mapping.items():
        m = NAME_RE.match(fn)
        if not m:
            continue
        day, minutes = m.group(1), published_minutes(m.group(2), m.group(3), m.group(4))
        if day not in latest or minutes > latest[day][0]:
            latest[day] = (minutes, info["sha256"], fn)
    out = {}
    for day, (minutes, sha, fn) in latest.items():
        f = CACHE / f"archive_{day}.json"
        if not f.exists():
            with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
                tmp.write(z.read(sha + ".pdf"))
                tmp.flush()
                text = subprocess.run(["pdftotext", "-layout", tmp.name, "-"], capture_output=True, text=True).stdout
            f.write_text(json.dumps({"published": f"{day} {fn}", "minutes": minutes, "rows": parse(text)}))
        out[day] = json.loads(f.read_text())
    return out


def local_day(g):
    return datetime.fromisoformat(g["date"].replace("Z", "+00:00")).astimezone(ET).date()


if __name__ == "__main__":
    CACHE.mkdir(parents=True, exist_ok=True)
    games = [json.loads(l) for l in open("data/games.jsonl")]
    games = [g for g in games if g["season"] in SEASONS]
    eves = sorted({(local_day(g) - timedelta(days=1)).isoformat() for g in games})
    with cf.ThreadPoolExecutor(6) as ex:
        reports = dict(zip(eves, ex.map(evening_report, eves)))
    archive = archive_reports()
    for day in eves:  # use whichever report went up latest that evening (official 8:30 PM = 1230 minutes)
        a = archive.get(day)
        if a and (reports.get(day) is None or a["minutes"] > 20 * 60 + 30):
            reports[day] = a
    result, last_known, direct, carried, none = {}, {}, 0, 0, 0
    for g in sorted(games, key=lambda g: g["date"]):
        d = local_day(g)
        rep = reports.get((d - timedelta(days=1)).isoformat())
        if rep is None:  # no report that evening: we know nothing new, so record "unknown"
            result[g["id"]] = None  # (not last week's statuses, which would go stale)
            none += 2
            continue
        prev = rep["rows"].get((d - timedelta(days=1)).strftime("%m/%d/%Y"), {})
        today = rep["rows"].get(d.strftime("%m/%d/%Y"), {})
        for t in (g["home"], g["away"]):  # statuses from yesterday's games are now "already announced"
            if t in prev:
                last_known[t] = prev[t]
        result[g["id"]] = {}
        for t in (g["home"], g["away"]):
            if t in today:
                result[g["id"]][t], direct = today[t], direct + 1
            elif t in last_known:
                result[g["id"]][t], carried = last_known[t], carried + 1
            else:
                result[g["id"]][t], none = {}, none + 1
    pathlib.Path("data/injuries.json").write_text(json.dumps(result))
    print(f"{len(eves)} evening reports, {sum(r is None for r in reports.values())} missing; team-games: "
          f"{direct} from the evening-before report, {carried} carried from the last game, {none} with nothing")
