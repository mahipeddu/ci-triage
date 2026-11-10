"""Per-test outcomes from pytest/unittest CI logs (pytorch format: per-test status lines, in-job reruns)."""
import re
from collections import defaultdict

TS = re.compile(r"^\d{4}-\d\d-\d\dT[\d:.]+Z ?")
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\[[0-9;]+m")

_ID = r"[\w/.-]+\.py::(\w+)::(\w+)"  # file.py::Class::test (param suffix like [x] allowed after)
STATUS_AFTER = re.compile(_ID + r"\S*\s+(PASSED|FAILED|ERROR|SKIPPED|\('RERUN')")  # "path::C::t PASSED [0.1s]"
STATUS_BEFORE = re.compile(r"^(PASSED|FAILED|ERROR)(?: CONSISTENTLY:)?\s+(?:\[[\d.]+s\]\s+)?" + _ID)  # summary
HEADER = re.compile(r"^_+ (\w+)\.(\w+) _+$")  # pytest failure section "____ Class.test ____"
REPRO = re.compile(r"python \S+\.py (\w+)\.(\w+)\b")  # pytorch "To execute this test, run ..." line
UNITTEST_FAIL = re.compile(r"^(?:FAIL|ERROR): (\w+) \(([\w.]+)\)")
SECTION_END = re.compile(r"^(_+ \S+ _+|={5,}.*)$")

STATUS = {"PASSED": "pass", "FAILED": "fail", "ERROR": "fail", "('RERUN'": "fail", "SKIPPED": "skip"}

Key = tuple[str, str]  # (test_name, class_name)
Event = tuple[int, str, bool]  # (line index, "pass" | "fail" | "skip", is a status line)


def strip(line: str) -> str:
    return ANSI.sub("", TS.sub("", line)).strip()


def scan(lines: list[str]) -> dict[Key, list[Event]]:
    """Test -> outcome events in log order. Status lines carry PASSED/FAILED/ERROR/RERUN/SKIPPED;
    failure headers, repro commands and unittest FAIL/ERROR lines count as non-status failures."""
    ev: dict[Key, list[Event]] = defaultdict(list)
    for i, raw in enumerate(lines):
        line = strip(raw)
        if line.startswith("Running "):  # "Running N items in this shard: <ids...>"
            continue
        if m := STATUS_AFTER.search(line):
            ev[(m[2], m[1])].append((i, STATUS[m[3]], True))
        elif m := STATUS_BEFORE.match(line):
            ev[(m[3], m[2])].append((i, STATUS[m[1]], True))
        elif m := HEADER.match(line) or REPRO.search(line):
            ev[(m[2], m[1])].append((i, "fail", False))
        elif m := UNITTEST_FAIL.match(line):
            ev[(m[1], m[2].rsplit(".", 1)[-1])].append((i, "fail", False))
    return ev


def failed(events: list[Event]) -> bool:
    return any(st == "fail" for _, st, _ in events)


def passed(events: list[Event]) -> bool:
    return any(st == "pass" and status for _, st, status in events)


def inner_flaky(events: list[Event]) -> bool:
    """Failed (FAILED/RERUN/...) and a PASSED status line comes after the first failure."""
    fails = [i for i, st, _ in events if st == "fail"]
    return bool(fails) and any(st == "pass" and status and i > fails[0] for i, st, status in events)


def traceback_chunk(lines: list[str], key: Key, events: list[Event], max_lines: int = 150) -> str:
    """The pytest failure section for this test ("____ Class.test ____" up to the next section),
    else 60 lines from its first failure line."""
    test, cls = key
    start = next((i for i, l in enumerate(lines) if (m := HEADER.match(strip(l))) and (m[2], m[1]) == key), None)
    if start is None:
        start = next(i for i, st, _ in events if st == "fail")
        return "\n".join(strip(l) for l in lines[start:start + 60])
    end = next((j for j in range(start + 1, min(len(lines), start + max_lines))
                if SECTION_END.match(strip(lines[j]))), min(len(lines), start + max_lines))
    return "\n".join(strip(l) for l in lines[start:end])
