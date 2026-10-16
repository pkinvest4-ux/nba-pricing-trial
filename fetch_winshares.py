"""Each player's win shares per 48 minutes and Box Plus/Minus for a whole season, from Basketball-Reference.
Used only as last season's numbers (2022-23 for 2023-24, and so on), so nothing comes from the future.
Writes data/winshares.json: {season: {name: {"min", "ws48", "bpm"}}}."""
import json, re, time, pathlib, subprocess

YEARS = {"2022-23": 2023, "2023-24": 2024, "2024-25": 2025}


def cell(row, stat):
    m = re.search(rf'data-stat="{stat}"[^>]*>(.*?)</t[dh]>', row)
    return re.sub("<[^>]+>", "", m.group(1)).strip() if m else ""


def parse(html):
    out = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html.split('id="advanced"')[1].split("</table>")[0], re.S):
        name, mp = cell(row, "name_display"), cell(row, "mp")
        if not name or not mp.isdigit() or name in out:  # traded players: the first row is the season total
            continue
        try:
            out[name] = {"min": int(mp), "ws48": float(cell(row, "ws_per_48") or 0), "bpm": float(cell(row, "bpm") or 0)}
        except ValueError:
            pass
    return out


if __name__ == "__main__":
    cache = pathlib.Path("data/third_party/bbref")
    cache.mkdir(parents=True, exist_ok=True)
    out = {}
    for season, year in YEARS.items():
        f = cache / f"advanced_{year}.html"
        if not f.exists():
            subprocess.run(["curl", "-s", "-A", "Mozilla/5.0", "-o", str(f),
                            f"https://www.basketball-reference.com/leagues/NBA_{year}_advanced.html"], check=True)
            time.sleep(4)
        out[season] = parse(f.read_text())
        print(season, len(out[season]), "players")
    pathlib.Path("data/winshares.json").write_text(json.dumps(out))
