#!/usr/bin/env python3
"""폴더를 스캔해 확장자·날짜·파일명 키워드로 분류 규칙을 제안하고, 이동 계획을 표와 moves.json으로 출력한다.

기본은 dry-run이다. 파일을 실제로 옮기지 않는다. 옮기려면 계획을 확인한 뒤 apply_moves.py를 쓴다.

사용법:
  python3 plan_moves.py ~/Downloads                          # 계획 표 + ./moves.json
  python3 plan_moves.py ~/Downloads --by-year                # 문서/2026/ 처럼 연도 하위 폴더
  python3 plan_moves.py ~/Downloads --rename                 # YYYYMMDD_문서명 정규화도 계획에 표시
  python3 plan_moves.py ~/Downloads --rule "음성:mp3,wav,m4a" # 분류 규칙 추가
  python3 plan_moves.py ~/Downloads --out 계획.json

기본 분류: 문서/ 이미지/ 영상/ 압축/ 설치파일/ 기타/. 파일명 키워드(계약·견적·영수증·회의·보고·스크린샷)로 2개 이상 모이면 하위 폴더를 제안한다.
건너뜀: 숨김 파일, 하위 폴더, 바로가기·심볼릭 링크, 진행 중 다운로드(.crdownload/.part/.download), Office 잠금 파일(~$), moves.json/undo.json.
삭제 기능은 없다. 표준 라이브러리만 사용한다.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

DEFAULT_RULES = [
    ("문서", "pdf doc docx hwp hwpx xls xlsx csv ppt pptx txt md rtf odt key numbers pages"),
    ("이미지", "jpg jpeg png gif heic heif webp bmp tif tiff svg psd ai"),
    ("영상", "mp4 mov avi mkv wmv m4v webm"),
    ("압축", "zip 7z rar tar gz tgz bz2 xz"),
    ("설치파일", "dmg pkg exe msi apk deb rpm appimage"),
]
KEYWORD_RULES = [  # (하위 폴더명, 정규식) — 대상 카테고리 안에서 하위 폴더 제안
    ("계약", r"계약|contract|nda|협약"),
    ("견적·청구", r"견적|invoice|청구|quotation|quote|세금계산서"),
    ("영수증", r"영수증|receipt"),
    ("회의", r"회의|meeting|minutes|회의록"),
    ("보고", r"보고|report|주간|월간"),
    ("이력서", r"이력서|resume|cv_|경력기술"),
    ("스크린샷", r"스크린샷|screenshot|screen shot|화면 캡처|캡처"),
]
SKIP_EXT = {".crdownload", ".part", ".download", ".tmp", ".partial"}
SKIP_NAMES = {"desktop.ini", "thumbs.db", "moves.json", "undo.json"}
SYSTEM_DIRS = ("/System", "/Library", "/Applications", "/usr", "/bin", "/etc",
               "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)")
DATE_IN_NAME = re.compile(r"(20\d{2}|19\d{2})[-._ ]?(0[1-9]|1[0-2])[-._ ]?(0[1-9]|[12]\d|3[01])")


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:,.0f}{unit}" if unit == "B" else f"{n:,.1f}{unit}"
        n /= 1024


def parse_rules(extra):
    rules = []
    for name, exts in DEFAULT_RULES:
        rules.append((name, set(exts.split())))
    for spec in extra or []:
        if ":" not in spec:
            print(f"규칙 형식이 잘못되었습니다: {spec} (예: 음성:mp3,wav)", file=sys.stderr)
            sys.exit(1)
        name, exts = spec.split(":", 1)
        ext_set = {e.strip().lower().lstrip(".") for e in exts.split(",") if e.strip()}
        # 사용자 규칙이 우선: 기존 규칙에서 같은 확장자를 뺀다
        rules = [(n, s - ext_set) for n, s in rules]
        rules.insert(0, (name.strip(), ext_set))
    return rules


def file_date(path, name):
    m = DATE_IN_NAME.search(name)
    if m:
        try:
            return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))), "파일명"
        except ValueError:
            pass
    return dt.date.fromtimestamp(os.path.getmtime(path)), "수정일"


def normalized_name(name, date):
    stem, ext = os.path.splitext(name)
    if stem.lower().endswith(".tar"):  # .tar.gz 같은 이중 확장자
        stem, ext = stem[:-4], ".tar" + ext
    stem = DATE_IN_NAME.sub("", stem)  # 날짜는 앞으로 옮긴다
    stem = re.sub(r"\s*\(\d+\)\s*$", "", stem)  # (1), (2)
    stem = re.sub(r"\s*(copy|복사본|사본)\s*\d*$", "", stem, flags=re.I)
    stem = re.sub(r"[\s\-_.]+", "_", stem).strip("_")
    stem = stem or "이름없음"
    return f"{date:%Y%m%d}_{stem}{ext.lower()}"


def guard_root(root):
    home = os.path.expanduser("~")
    norm = os.path.normpath(root)
    if norm in ("/", home) or norm == os.path.splitdrive(norm)[0] + os.sep:
        print(f"루트 디렉터리나 홈 폴더 전체({norm})는 정리 대상으로 잡지 않습니다. 하위 폴더를 지정하세요.", file=sys.stderr)
        sys.exit(1)
    for s in SYSTEM_DIRS:
        if norm == s or norm.startswith(s + os.sep):
            print(f"시스템 폴더({norm})는 건드리지 않습니다.", file=sys.stderr)
            sys.exit(1)


def scan(root, rules, by_year, rename, use_keywords, skipped):
    entries = []
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        low = name.lower()
        ext = os.path.splitext(low)[1]
        if name.startswith("."):
            skipped.append((name, "숨김 파일"))
        elif os.path.islink(path):
            skipped.append((name, "링크"))
        elif os.path.isdir(path):
            skipped.append((name, "폴더(하위 폴더는 건드리지 않음)"))
        elif ext in SKIP_EXT:
            skipped.append((name, "진행 중 다운로드·임시 파일"))
        elif low in SKIP_NAMES or name.startswith("~$") or low.startswith("정리_로그"):
            skipped.append((name, "시스템·잠금·계획 파일"))
        elif not os.path.isfile(path):
            skipped.append((name, "일반 파일 아님"))
        else:
            entries.append((name, path, ext.lstrip(".")))

    plans = []
    for name, path, ext in entries:
        category = next((n for n, exts in rules if ext in exts), "기타")
        reason = [f"확장자 .{ext}" if ext else "확장자 없음"]
        date, date_src = file_date(path, name)
        sub = ""
        if use_keywords:
            for kw_name, pat in KEYWORD_RULES:
                if re.search(pat, name, flags=re.I):
                    sub = kw_name
                    break
        plans.append({"name": name, "path": path, "category": category, "sub": sub, "date": date,
                      "date_src": date_src, "size": os.path.getsize(path), "reason": reason})

    # 키워드 하위 폴더는 같은 카테고리에서 2개 이상 모일 때만 제안한다
    counts = {}
    for p in plans:
        if p["sub"]:
            counts[(p["category"], p["sub"])] = counts.get((p["category"], p["sub"]), 0) + 1
    for p in plans:
        if p["sub"] and counts[(p["category"], p["sub"])] < 2:
            p["sub"] = ""
        parts = [p["category"]]
        if p["sub"]:
            parts.append(p["sub"])
            p["reason"].append(f"키워드 '{p['sub']}'")
        if by_year:
            parts.append(f"{p['date']:%Y}")
            p["reason"].append(f"{p['date_src']} {p['date']:%Y}")
        new_name = normalized_name(p["name"], p["date"]) if rename else p["name"]
        if rename and new_name != p["name"]:
            p["reason"].append("이름 정규화")
        p["dst"] = os.path.join(*parts, new_name)
    return plans


def main():
    ap = argparse.ArgumentParser(
        description="폴더를 스캔해 이동 계획(표 + moves.json)을 만든다. 기본은 dry-run이며 파일을 옮기지 않는다. 삭제 기능은 없다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="적용: python3 apply_moves.py moves.json --apply   되돌리기: python3 undo_moves.py undo.json --apply")
    ap.add_argument("folder", help="정리할 폴더(바로 아래 파일만 대상, 하위 폴더는 건드리지 않음)")
    ap.add_argument("--by-year", action="store_true", help="카테고리 아래 연도 폴더(파일명 날짜 → 없으면 수정일)")
    ap.add_argument("--rename", action="store_true", help="파일명을 YYYYMMDD_문서명 형식으로 정규화하는 계획을 포함")
    ap.add_argument("--rule", action="append", metavar="이름:확장자,확장자", help="분류 규칙 추가(여러 번 가능). 기본 규칙보다 우선")
    ap.add_argument("--no-keywords", action="store_true", help="파일명 키워드 하위 폴더 제안을 끈다")
    ap.add_argument("--out", default="moves.json", help="계획 파일 경로(기본 ./moves.json, 있으면 _2, _3)")
    ap.add_argument("--apply", action="store_true", help="계획을 만든 직후 바로 적용한다(apply_moves.py 호출). 평소에는 쓰지 않는다")
    args = ap.parse_args()

    root = os.path.abspath(os.path.expanduser(args.folder))
    if not os.path.isdir(root):
        print(f"폴더를 찾을 수 없습니다: {root}", file=sys.stderr)
        sys.exit(1)
    guard_root(root)
    rules = parse_rules(args.rule)
    skipped = []
    plans = scan(root, rules, args.by_year, args.rename, not args.no_keywords, skipped)

    base = os.path.basename(root).lower()
    if base in ("downloads", "다운로드", "desktop", "바탕화면"):
        print(f"※ '{os.path.basename(root)}' 폴더입니다. 계획을 사용자에게 보여주고 명시적인 '적용' 답을 받은 뒤에만 apply_moves.py를 실행한다.\n")

    print(f"대상 폴더: {root}")
    print(f"파일 {len(plans)}개 이동 계획, {len(skipped)}개 건너뜀  (dry-run: 아직 아무것도 옮기지 않았다)\n")
    print("| # | 파일 | 크기 | 날짜 | 분류 근거 | 이동 위치 |")
    print("|---|---|---|---|---|---|")
    for i, p in enumerate(plans, 1):
        print(f"| {i} | {p['name']} | {human(p['size'])} | {p['date']:%Y-%m-%d} | {', '.join(p['reason'])} | {p['dst']} |")

    summary = {}
    for p in plans:
        top = p["dst"].split(os.sep)[0]
        summary[top] = summary.get(top, 0) + 1
    print("\n카테고리별: " + ", ".join(f"{k} {v}개" for k, v in sorted(summary.items())))
    if skipped:
        print(f"건너뜀 {len(skipped)}개: " + ", ".join(f"{n}({r})" for n, r in skipped[:8]) + (" …" if len(skipped) > 8 else ""))

    out = args.out
    if os.path.exists(out):
        stem, ext = os.path.splitext(out)
        n = 2
        while os.path.exists(f"{stem}_{n}{ext}"):
            n += 1
        out = f"{stem}_{n}{ext}"
    data = {
        "version": 1,
        "created": dt.datetime.now().isoformat(timespec="seconds"),
        "root": root,
        "options": {"by_year": args.by_year, "rename": args.rename, "rules": args.rule or [], "keywords": not args.no_keywords},
        "moves": [{"src": p["name"], "dst": p["dst"], "reason": ", ".join(p["reason"])} for p in plans],
        "skipped": [{"name": n, "reason": r} for n, r in skipped],
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n계획 저장: {os.path.abspath(out)}")
    print(f"적용하려면: python3 apply_moves.py \"{os.path.abspath(out)}\" --apply")

    if args.apply and plans:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import apply_moves
        print("\n--apply 지정: 바로 적용한다.\n")
        apply_moves.apply(out, do_apply=True)


if __name__ == "__main__":
    main()
