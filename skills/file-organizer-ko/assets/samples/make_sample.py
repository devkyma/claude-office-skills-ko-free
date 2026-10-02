#!/usr/bin/env python3
"""file-organizer-ko 테스트용 '어질러진 가상 다운로드 폴더'를 만든다. 내용은 모두 빈 껍데기 가상 파일이다.

사용법:
  python3 make_sample.py                       # ./정리_샘플_다운로드 생성
  python3 make_sample.py /tmp/어딘가/테스트폴더   # 지정 위치(비어 있거나 없어야 함)

이후: python3 ../../scripts/plan_moves.py 정리_샘플_다운로드 --by-year --rename
"""
import argparse
import datetime as dt
import os
import sys
import time

FILES = [  # (파일명, 수정일)
    ("20260915_고객사A_용역계약서_v2.pdf", "2026-09-15"),
    ("계약서 초안 (1).docx", "2026-09-20"),
    ("NDA_draft_final_final.docx", "2025-12-03"),
    ("견적서_마바사_2026-09-22.xlsx", "2026-09-22"),
    ("invoice_0831.pdf", "2026-08-31"),
    ("영수증_택시_0912.jpg", "2026-09-12"),
    ("영수증 스캔.pdf", "2026-09-13"),
    ("주간보고_9월3주.pptx", "2026-09-19"),
    ("월간 보고서 초안.hwpx", "2026-09-26"),
    ("회의록_킥오프_20260901.txt", "2026-09-01"),
    ("meeting_notes copy.md", "2026-09-02"),
    ("스크린샷 2026-09-28 오후 3.12.45.png", "2026-09-28"),
    ("스크린샷 2026-09-29 오전 10.02.11.png", "2026-09-29"),
    ("IMG_2031.HEIC", "2025-07-14"),
    ("배너시안_v3.psd", "2026-09-10"),
    ("제품소개영상.mp4", "2026-06-05"),
    ("zoom_recording_2025-11-20.mp4", "2025-11-20"),
    ("자료모음.zip", "2026-09-27"),
    ("backup-2025.tar.gz", "2025-12-31"),
    ("ClaudeCodeSetup.dmg", "2026-09-30"),
    ("KakaoTalk_Setup.exe", "2026-03-02"),
    ("noname", "2026-09-05"),
    ("data.json", "2026-09-08"),
    ("Untitled.key", "2026-04-11"),
    ("큰파일.iso.crdownload", "2026-09-30"),
    ("영상.mp4.part", "2026-09-30"),
    ("~$계약서 초안 (1).docx", "2026-09-20"),
    (".DS_Store", "2026-09-30"),
]
SUBDIR_FILES = [("이미 정리된 폴더/옛날자료.pdf", "2024-05-05")]


def main():
    ap = argparse.ArgumentParser(description="어질러진 가상 다운로드 폴더를 만든다(가상 빈 파일).")
    ap.add_argument("folder", nargs="?", default="정리_샘플_다운로드", help="만들 폴더(없거나 비어 있어야 함)")
    args = ap.parse_args()
    root = os.path.abspath(os.path.expanduser(args.folder))
    if os.path.isdir(root) and os.listdir(root):
        print(f"폴더가 비어 있지 않습니다: {root}. 다른 경로를 지정하세요.", file=sys.stderr)
        sys.exit(1)
    os.makedirs(root, exist_ok=True)
    for rel, day in FILES + SUBDIR_FILES:
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"가상 샘플 파일: {rel}\n")
        ts = time.mktime(dt.datetime.strptime(day, "%Y-%m-%d").timetuple())
        os.utime(path, (ts, ts))
    print(f"생성: {root}  (파일 {len(FILES) + len(SUBDIR_FILES)}개)")


if __name__ == "__main__":
    main()
