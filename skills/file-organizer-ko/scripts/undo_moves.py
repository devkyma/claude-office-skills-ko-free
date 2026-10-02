#!/usr/bin/env python3
"""apply_moves.py가 남긴 undo.json을 읽어 파일을 원래 자리로 되돌린다.

기본은 dry-run이다. 실제로 되돌리려면 --apply를 붙인다.

사용법:
  python3 undo_moves.py undo.json            # 되돌릴 목록 확인
  python3 undo_moves.py undo.json --apply    # 실제 복원

규칙: 옮긴 역순으로 복원한다. 원래 자리에 다른 파일이 생겼으면 _2 접미사로 복원하고 알린다.
      만들어진 분류 폴더는 비어 있어도 지우지 않는다(삭제 기능 없음). 필요하면 사용자가 직접 정리한다.
표준 라이브러리만 사용한다.
"""
import argparse
import datetime as dt
import json
import os
import shutil
import sys


def unique_path(path):
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(f"{stem}_{n}{ext}"):
        n += 1
    return f"{stem}_{n}{ext}"


def main():
    ap = argparse.ArgumentParser(description="undo.json을 읽어 옮긴 파일을 원래 자리로 되돌린다. 기본은 확인만, --apply 를 줘야 실제로 되돌린다.")
    ap.add_argument("undo", nargs="?", default="undo.json", help="apply_moves.py가 만든 undo.json(기본 ./undo.json)")
    ap.add_argument("--apply", action="store_true", help="실제로 되돌린다")
    args = ap.parse_args()

    try:
        with open(args.undo, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"undo 파일을 찾을 수 없습니다: {args.undo}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as ex:
        print(f"undo 파일을 읽을 수 없습니다: {ex}", file=sys.stderr)
        sys.exit(1)
    if data.get("version") != 1 or "moves" not in data:
        print("undo.json 형식이 아닙니다.", file=sys.stderr)
        sys.exit(1)

    root = data["root"]
    root_real = os.path.realpath(root)
    restored, problems, log = 0, 0, []
    for m in reversed(data["moves"]):
        cur = os.path.join(root, m["dst"])
        back = os.path.join(root, m["src"])
        if not os.path.realpath(back).startswith(root_real + os.sep):
            line = f"건너뜀: {m['dst']} — 복원 경로가 폴더 밖"
            problems += 1
        elif not os.path.isfile(cur):
            line = f"건너뜀: {m['dst']} — 파일이 그 자리에 없음(이미 옮기거나 이름을 바꿈)"
            problems += 1
        else:
            final = unique_path(back)
            note = "" if final == back else f"원래 자리에 다른 파일이 있어 {os.path.basename(final)}로 복원"
            if args.apply:
                os.makedirs(os.path.dirname(final), exist_ok=True)
                shutil.move(cur, final)
            restored += 1
            line = f"{'복원' if args.apply else '예정'}: {m['dst']} → {os.path.relpath(final, root)}" + (f"  ({note})" if note else "")
        log.append(line)
        print(line)

    print(f"\n{'복원 완료' if args.apply else '확인 완료(dry-run)'}: {restored}개, 건너뜀 {problems}개")
    if not args.apply:
        print("실제로 되돌리려면 --apply 를 붙여 다시 실행한다.")
        return
    dirs = data.get("created_dirs") or []
    empty = [d for d in dirs if os.path.isdir(os.path.join(root, d)) and not os.listdir(os.path.join(root, d))]
    if empty:
        print(f"비어 있는 분류 폴더 {len(empty)}개는 지우지 않았다(삭제 기능 없음): " + ", ".join(empty[:6]) + (" …" if len(empty) > 6 else ""))
    log_path = unique_path(os.path.join(os.path.dirname(os.path.abspath(args.undo)), f"복원_로그_{dt.datetime.now():%Y%m%d_%H%M%S}.txt"))
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"대상: {root}\nundo: {os.path.abspath(args.undo)}\n\n" + "\n".join(log) + "\n")
    print(f"로그: {log_path}")


if __name__ == "__main__":
    main()
