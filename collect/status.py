"""Progress bars + ETA for the background jobs, read from their logs.

Usage: watch -n 30 python3 -m collect.status
"""
import argparse
import re
from datetime import datetime, timedelta
from pathlib import Path

from collect.github_logs import ROOT

PROGRESS = re.compile(r"^\s*(\d\d:\d\d:\d\d) (?:labeled|refetched|gemini|teacher|rationalized|step|predicted) (\d+)/(\d+)")
MODEL_BYTES = 8.05e9  # Qwen3-4B-Instruct-2507 safetensors
HUB = Path.home() / ".cache/huggingface/hub"


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


def read(p: Path) -> str:
    return p.read_text(errors="replace") if p.exists() else ""


def distill_rows(data: Path) -> None:
    dl = read(data / "models/download.log")
    if "DOWNLOADED" in dl:
        print(f"{'distill: student model download':34} done")
    elif dl:
        recent = datetime.now().timestamp() - 300
        got = sum(f.stat().st_size for f in HUB.glob("models--Qwen--Qwen3-4B-Instruct-2507/blobs/*.incomplete")
                  if f.stat().st_mtime >= recent)  # active partials only; stale ones from a stalled attempt ignored
        done = sum(f.stat().st_size for f in HUB.glob("models--Qwen--Qwen3-4B-Instruct-2507/blobs/*")
                   if not f.name.endswith(".incomplete") and f.stat().st_size > 1e8)
        gb = (got + done) / 1e9
        fill = min(30, int(30 * gb * 1e9 / MODEL_BYTES))
        print(f"{'distill: student model download':34} [{'#' * fill}{'.' * (30 - fill)}] {gb:4.1f}/{MODEL_BYTES / 1e9:.1f} GB")
    tl = read(data / "teacher_data.log")
    lines = tl.splitlines()
    last = next((l for l in reversed(lines) if re.search(r"teacher \d+/|rationalized \d+/|quota: sleeping|DONE|FAILED", l)), "")
    pts = progress(data / "teacher_data.log")
    teacher_pts = [p for p, l in zip(pts, [l for l in lines if PROGRESS.match(l)]) if " teacher " in l]
    rat_pts = [p for p, l in zip(pts, [l for l in lines if PROGRESS.match(l)]) if " rationalized " in l]
    main_done = "main pass complete" in tl
    paused = (m := re.search(r"sleeping until (.+?) \w{3} \w{3} \d+ [\d:]+ [AP]M", last)) and m[1]
    kept = next((l for l in reversed(lines) if l.startswith("kept/dropped")), "")
    state = "done" if main_done else (f"paused: daily quota, resumes {paused} "
                                      f"({teacher_pts[-1][1]}/{teacher_pts[-1][2]})" if paused and teacher_pts else "")
    print(bar("distill: teacher data (train)", teacher_pts, state))
    if kept:
        print(f"{'':34} {kept}")
    if main_done or rat_pts:
        rs = "done" if "TEACHER DATA COMPLETE" in tl else (f"paused: daily quota, resumes {paused}" if paused else "")
        print(bar("distill: rationalization", rat_pts, rs))
    t38 = data / "teacher_data_38.log"
    if t38.exists():
        tl38 = read(t38)
        print(bar("distill: teacher data (3.8-flash)", progress(t38),
                  "done" if "TEACHER DATA COMPLETE" in tl38 else "STOPPED (budget cap)" if "budget cap" in tl38 else ""))
    up = read(data / "teacher_upgrade.log")
    if up:
        print(f"{'distill: 3.8-flash upgrade':34} " + (up.strip().splitlines()[-1][:110]))
    for name in ("labels", "rationale", "rationale_rationalized", "rationale_flash38", "rationale_rationalized_flash38",
                 "rationale_mixed38", "rationale_rationalized_mixed38"):
        log = data / f"models/student_{name}/train.log"
        if log.exists():
            st = read(log)
            print(bar(f"distill: student {name} training", progress(log),
                      "done" if "TRAIN DONE" in st else "FAILED" if "Traceback" in st else ""))
        plog = data / f"models/predict_{name}.log"
        if plog.exists():
            pt = read(plog)
            print(bar(f"distill: student {name} predict (150)", progress(plog),
                      "done" if "PREDICT DONE" in pt else "FAILED" if "FAILED" in pt or "Traceback" in pt
                      else "" if "start predict" in pt else "after training"))


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
    distill_rows(data)
    print(bar("main: pytorch log re-download", progress(data / "collect.log", "restart"), refetch))
    print(bar("main: labeling (all repos)", progress(data / "collect.log", "refetch done") if "refetch done" in tail
              else [], labeling or ("" if "refetch done" in tail else "after re-download")))
    print(bar("small: labeling mpv/libavif/arrow", progress(data / "label_small.log"),
              "done" if "SMALL DONE" in small else "FAILED (see data/label_small.log)" if "SMALL FAILED" in small else ""))
    runs = [m[1] for l in ev.splitlines() if (m := re.match(r"== (\S+ \S+ n=\d+)", l))]
    if runs:
        print(f"{'teacher runs':34} run {len(runs)}/6: {runs[-1]}" + ("  (all done)" if "EVAL DONE" in ev else ""))
    print(bar("fast-track eval: Gemini", progress(data / "eval_small.log", "gemini 0/"),
              "done" if "EVAL DONE" in ev else "FAILED (see data/eval_small.log)" if "EVAL FAILED" in ev
              else "" if ev else "after small labeling"))


if __name__ == "__main__":
    main()
