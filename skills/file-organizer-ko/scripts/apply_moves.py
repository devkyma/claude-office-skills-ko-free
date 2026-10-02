#!/usr/bin/env python3
"""plan_moves.py가 만든 moves.json을 적용해 파일을 옮긴다. 되돌리기용 undo.json과 로그를 남긴다.

기본은 dry-run(검증만)이다. 실제로 옮기려면 --apply를 붙인다.

사용법:
  python3 apply_moves.py moves.json            # 검증: 원본 존재 여부, 이름 충돌 예고
  python3 apply_moves.py moves.json --apply    # 실제 이동

규칙: 이름이 충돌하면 _2, _3 접미사를 붙인다. 아무것도 삭제하거나 덮어쓰지 않는다.
      이동 결과는 moves.json 옆 undo.json(있으면 undo_2.json)과 정리_로그_YYYYMMDD_HHMMSS.txt에 기록한다.
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


def load_plan(plan_path):
    with open(plan_path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("version") != 1 or "root" not in data or "moves" not in data:
        raise ValueError("moves.json 형식이 아닙니다(plan_moves.py로 만든 파일을 지정하세요).")
    return data


def apply(plan_path, do_apply=False):
    data = load_plan(plan_path)
    root = data["root"]
    if not os.path.isdir(root):
        print(f"대상 폴더가 없습니다: {root}", file=sys.stderr)
        sys.exit(1)
    root_real = os.path.realpath(root)
    plan_dir = os.path.dirname(os.path.abspath(plan_path))
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")

    done, problems, log = [], [], []
    created_dirs = []
    for m in data["moves"]:
        src = os.path.join(root, m["src"])
        dst = os.path.join(root, m["dst"])
        # 대상 폴더 밖으로 나가는 경로는 거부한다
        if not os.path.realpath(dst).startswith(root_real + os.sep):
            problems.append((m["src"], "대상 경로가 폴더 밖을 가리킴 — 건너뜀"))
            continue
        if not os.path.isfile(src):
            problems.append((m["src"], "원본이 없음(이미 옮겨졌거나 삭제됨) — 건너뜀"))
            continue
        if os.path.abspath(src) == os.path.abspath(dst):
            problems.append((m["src"], "원본과 대상이 같음 — 건너뜀"))
            continue
        final = unique_path(dst)
        note = "" if final == dst else f"이름 충돌 → {os.path.basename(final)}"
        if do_apply:
            d = os.path.dirname(final)
            if not os.path.isdir(d):
                os.makedirs(d)
                created_dirs.append(os.path.relpath(d, root))
            shutil.move(src, final)
        rel_final = os.path.relpath(final, root)
        done.append({"src": m["src"], "dst": rel_final})
        line = f"{'이동' if do_apply else '예정'}: {m['src']} → {rel_final}" + (f"  ({note})" if note else "")
        log.append(line)
        print(line)

    for name, why in problems:
        line = f"건너뜀: {name} — {why}"
        log.append(line)
        print(line)

    print(f"\n{'이동 완료' if do_apply else '검증 완료(dry-run)'}: {len(done)}개, 건너뜀 {len(problems)}개")
    if not do_apply:
        print("실제로 옮기려면 --apply 를 붙여 다시 실행한다.")
        return

    undo_path = unique_path(os.path.join(plan_dir, "undo.json"))
    with open(undo_path, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "applied": dt.datetime.now().isoformat(timespec="seconds"), "root": root,
                   "plan": os.path.abspath(plan_path), "moves": done, "created_dirs": created_dirs},
                  f, ensure_ascii=False, indent=2)
    log_path = unique_path(os.path.join(plan_dir, f"정리_로그_{stamp}.txt"))
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"대상: {root}\n계획: {os.path.abspath(plan_path)}\n시각: {dt.datetime.now():%Y-%m-%d %H:%M:%S}\n\n" + "\n".join(log) + "\n")
    print(f"되돌리기 파일: {undo_path}\n로그: {log_path}")
    print(f"되돌리려면: python3 undo_moves.py \"{undo_path}\" --apply")


def main():
    ap = argparse.ArgumentParser(description="moves.json 계획대로 파일을 옮긴다. 기본은 검증(dry-run), --apply 를 줘야 실제로 옮긴다. 삭제·덮어쓰기는 하지 않는다.")
    ap.add_argument("plan", nargs="?", default="moves.json", help="plan_moves.py가 만든 계획 파일(기본 ./moves.json)")
    ap.add_argument("--apply", action="store_true", help="실제로 파일을 옮긴다")
    args = ap.parse_args()
    try:
        apply(args.plan, args.apply)
    except FileNotFoundError:
        print(f"계획 파일을 찾을 수 없습니다: {args.plan}", file=sys.stderr)
        sys.exit(1)
    except (ValueError, json.JSONDecodeError) as ex:
        print(f"계획 파일을 읽을 수 없습니다: {ex}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
