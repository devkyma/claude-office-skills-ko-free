#!/usr/bin/env python3
"""캘린더(.ics) 파일에서 특정 주의 일정만 뽑아 표로 출력한다.

사용법:
  python3 ics_to_events.py 캘린더.ics                 # 이번 주(월~일)
  python3 ics_to_events.py 캘린더.ics --week 2026-09-29   # 해당 날짜가 속한 주
  python3 ics_to_events.py 캘린더.ics --from 2026-09-01 --to 2026-09-30

표준 라이브러리만 사용한다. 반복 일정(RRULE)은 첫 발생만 표시하고 '반복' 표시를 붙인다.
"""
import argparse
import datetime as dt
import re
import sys


def unfold(lines):
    out = []
    for line in lines:
        line = line.rstrip("\r\n")
        if line.startswith((" ", "\t")) and out:
            out[-1] += line[1:]
        else:
            out.append(line)
    return out


def parse_dt(value, params):
    # 형식: 20260929T090000Z / 20260929T090000 / 20260929 (종일)
    value = value.strip()
    if re.fullmatch(r"\d{8}", value):
        return dt.datetime.strptime(value, "%Y%m%d"), True
    m = re.fullmatch(r"(\d{8}T\d{6})(Z?)", value)
    if not m:
        return None, False
    naive = dt.datetime.strptime(m.group(1), "%Y%m%dT%H%M%S")
    if m.group(2) == "Z":
        # UTC → 로컬(KST 가정, 시스템 시간대 사용)
        local = naive.replace(tzinfo=dt.timezone.utc).astimezone().replace(tzinfo=None)
        return local, False
    return naive, False


def parse_ics(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        lines = unfold(f.readlines())
    events, cur = [], None
    for line in lines:
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT":
            if cur is not None:
                events.append(cur)
            cur = None
        elif cur is not None and ":" in line:
            head, value = line.split(":", 1)
            name, *param_parts = head.split(";")
            params = dict(p.split("=", 1) for p in param_parts if "=" in p)
            if name in ("DTSTART", "DTEND"):
                when, allday = parse_dt(value, params)
                cur[name] = when
                cur["ALLDAY"] = cur.get("ALLDAY", False) or allday
            elif name in ("SUMMARY", "LOCATION", "DESCRIPTION", "RRULE", "ATTENDEE", "ORGANIZER"):
                value = value.replace("\\n", " ").replace("\\,", ",")
                if name == "ATTENDEE":
                    cur.setdefault("ATTENDEES", []).append(params.get("CN", value.replace("mailto:", "")))
                else:
                    cur[name] = value
    return events


def week_range(anchor):
    monday = anchor - dt.timedelta(days=anchor.weekday())
    return monday, monday + dt.timedelta(days=7)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ics")
    ap.add_argument("--week", help="이 날짜가 속한 주(월~일), 예: 2026-09-29")
    ap.add_argument("--from", dest="start", help="시작일 YYYY-MM-DD")
    ap.add_argument("--to", dest="end", help="종료일 YYYY-MM-DD (포함)")
    args = ap.parse_args()

    if args.start and args.end:
        start = dt.datetime.strptime(args.start, "%Y-%m-%d")
        end = dt.datetime.strptime(args.end, "%Y-%m-%d") + dt.timedelta(days=1)
    else:
        anchor = dt.datetime.strptime(args.week, "%Y-%m-%d") if args.week else dt.datetime.now()
        start, end = week_range(anchor.replace(hour=0, minute=0, second=0, microsecond=0))

    events = [e for e in parse_ics(args.ics) if e.get("DTSTART") and start <= e["DTSTART"] < end]
    events.sort(key=lambda e: e["DTSTART"])

    days = "월화수목금토일"
    print(f"기간: {start:%Y-%m-%d} ~ {(end - dt.timedelta(days=1)):%Y-%m-%d}  (일정 {len(events)}건)\n")
    print("| 날짜 | 시간 | 일정 | 장소 | 참석자 | 비고 |")
    print("|---|---|---|---|---|---|")
    for e in events:
        s = e["DTSTART"]
        date = f"{s:%m/%d}({days[s.weekday()]})"
        if e.get("ALLDAY"):
            time = "종일"
        else:
            en = e.get("DTEND")
            time = f"{s:%H:%M}" + (f"~{en:%H:%M}" if en else "")
        att = ", ".join(e.get("ATTENDEES", [])[:4])
        if len(e.get("ATTENDEES", [])) > 4:
            att += f" 외 {len(e['ATTENDEES']) - 4}명"
        note = "반복" if e.get("RRULE") else ""
        print(f"| {date} | {time} | {e.get('SUMMARY', '(제목 없음)')} | {e.get('LOCATION', '')} | {att} | {note} |")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as ex:
        print(f"파일을 찾을 수 없습니다: {ex.filename}", file=sys.stderr)
        sys.exit(1)
