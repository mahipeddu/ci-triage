"""Progress bars + ETA for the background jobs, read from their logs.

Usage: watch -n 30 python3 -m collect.status
"""
import argparse
import re
from datetime import datetime, timedelta
from pathlib import Path

from collect.github_logs import ROOT

PROGRESS = re.compile(r"^\s*(\d\d:\d\d:\d\d) (?:labeled|refetched|gemini) (\d+)/(\d+)")


def progress(log: Path, start_marker: str | None = None) -> list[tuple[datetime, int, int]]:
    """(time, done, total) points after the last start_marker line; HH:MM:SS made monotonic across midnight."""
    if not log.exists():
        return []
    lines = log.read_text(errors="replace").splitlines()
    if start_marker:
        starts = [i for i, l in enumerate(lines) if start_marker in l]
        lines = lines[starts[-1] + 1:] if starts else []
    pts, day, prev = [], datetime.now().replace(hour=0, minute=0, second=0, microsecond=0), None
    for l in lines:
        if m := PROGRESS.match(l):
            t = datetime.combine(day.date(), datetime.strptime(m[1], "%H:%M:%S").time())
            if prev and t < prev:
                day += timedelta(days=1)
                t += timedelta(days=1)
            prev = t
            pts.append((t, int(m[2]), int(m[3])))
    # anchor the series so its last point is not in the future (log may span earlier days)
    if pts and pts[-1][0] > datetime.now() + timedelta(minutes=5):
        shift = pts[-1][0] - datetime.now()
        pts = [(t - timedelta(days=shift.days + 1), d, n) for t, d, n in pts]
    return pts


def bar(name: str, pts: list[tuple[datetime, int, int]], state: str) -> str:
    if state:
        return f"{name:34} {state}"
    if not pts:
        return f"{name:34} waiting"
    t1, done, total = pts[-1]
    width = 30
    fill = int(width * done / total) if total else 0
    eta = ""
    t0, d0, _ = pts[max(0, len(pts) - 6)]  # recent rate: last ~5 progress intervals
    if len(pts) >= 2 and done > d0:
        rate = (done - d0) / max((t1 - t0).total_seconds(), 1)  # items / s
        eta_t = t1 + timedelta(seconds=(total - done) / rate)
        eta = f"  {rate * 60:6.1f}/min  ETA {eta_t:%H:%M}"
    return f"{name:34} [{'#' * fill}{'.' * (width - fill)}] {done:5}/{total:<5} {100 * done / total:5.1f}%{eta}"


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    data = ROOT / "data"
    main_log = (data / "collect.log").read_text(errors="replace") if (data / "collect.log").exists() else ""
    tail = main_log[main_log.rfind("restart"):]
    if "ALL DONE" in tail:
        refetch, labeling = "done", "done"
    elif "FAILED exit" in tail:
        refetch, labeling = "FAILED (see data/collect.log)", "FAILED (see data/collect.log)"
    else:
        refetch, labeling = ("done" if "refetch done" in tail else ""), ""
    small = (data / "label_small.log").read_text(errors="replace") if (data / "label_small.log").exists() else ""
    ev = (data / "eval_small.log").read_text(errors="replace") if (data / "eval_small.log").exists() else ""

    print(f"{datetime.now():%Y-%m-%d %H:%M:%S}")
    print(bar("main: pytorch log re-download", progress(data / "collect.log", "restart"), refetch))
    print(bar("main: labeling (all repos)", progress(data / "collect.log", "refetch done") if "refetch done" in tail
              else [], labeling or ("" if "refetch done" in tail else "after re-download")))
    print(bar("small: labeling mpv/libavif/arrow", progress(data / "label_small.log"),
              "done" if "SMALL DONE" in small else "FAILED (see data/label_small.log)" if "SMALL FAILED" in small else ""))
    print(bar("fast-track eval: Gemini", progress(data / "eval_small.log"),
              "done" if "EVAL DONE" in ev else "FAILED (see data/eval_small.log)" if "EVAL FAILED" in ev
              else "" if ev else "after small labeling"))


if __name__ == "__main__":
    main()
