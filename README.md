# 한국 직장인용 Claude Code 업무 스킬 (무료 3종)

Claude Code에 넣으면 한국 회사 업무 양식에 맞춰 일해 주는 스킬입니다. 개발자가 아니어도 됩니다.

| 스킬 | 하는 일 | 이렇게 말하면 됩니다 |
|---|---|---|
| `weekly-report-ko` | 메모·캘린더(.ics)·메신저 기록을 금주 실적/차주 계획/이슈 양식의 주간보고로 | "이번 주 메모야, 주간보고 써줘" |
| `biz-email-ko` | 요청·독촉·거절·사과 등 12개 상황별 비즈니스 이메일과 메신저 버전 | "견적 회신 독촉 메일 정중하게 써줘" |
| `file-organizer-ko` | 폴더를 스캔해 이동 계획표를 먼저 보여주고, 승인 후 실행, 되돌리기 파일 생성 | "다운로드 폴더 정리 계획 보여줘" |

## 설치 (1분)

```bash
git clone https://github.com/devkyma/claude-office-skills-ko-free.git
cp -R claude-office-skills-ko-free/skills/* ~/.claude/skills/
```
Windows(PowerShell): `Copy-Item -Recurse .\skills\* "$env:USERPROFILE\.claude\skills\"`

Claude Code를 다시 실행하면 스킬이 자동으로 인식됩니다. 파이썬 3.9 이상이 있으면 캘린더 파싱·폴더 정리 스크립트가 동작합니다(표준 라이브러리만 사용, 추가 설치 없음).

## 원칙
- 어떤 스킬도 파일을 삭제하지 않습니다. 폴더 정리는 계획 확인 → 적용 → 되돌리기 3단계입니다.
- 원본을 덮어쓰지 않습니다. 데이터를 외부로 보내는 코드가 없습니다.

## 10종 풀팩
엑셀 정리, 차트, 슬라이드 초안(pptx), 문서 요약(계약서·HWPX), 회의록·액션아이템, 공지문, 한영 번역·검수와 CLAUDE.md 템플릿 3종, 설치 스크립트, 가이드가 포함된 풀팩은 여기서 받을 수 있습니다: [래피드 링크]

## 고지
Anthropic 공식 제품이 아니며 Anthropic과 관계가 없습니다. 결과물은 초안이며 중요한 판단은 담당자가 확인하세요.
