"""Shared helpers: polite HTTP with retries, and team-code matching between sources."""
import json, time, urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129 Safari/537.36"

# One code per franchise, whichever way a source spells it.
ALIASES = {"GSW": "GS", "NOP": "NO", "SAS": "SA", "UTA": "UTAH", "NYK": "NY", "WAS": "WSH", "BRK": "BKN", "PHO": "PHX"}
NBA = {"ATL", "BKN", "BOS", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GS", "HOU", "IND", "LAC", "LAL", "MEM",
       "MIA", "MIL", "MIN", "NO", "NY", "OKC", "ORL", "PHI", "PHX", "POR", "SA", "SAC", "TOR", "UTAH", "WSH"}


def team(code):
    return ALIASES.get(code, code)


def fetch(url, tries=4, pause=0.0, as_json=True):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read().decode("utf-8", "replace")
            time.sleep(pause)
            return json.loads(body) if as_json else body
        except Exception:
            time.sleep(2 * (i + 1))
    return None
