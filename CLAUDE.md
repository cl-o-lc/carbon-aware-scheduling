# CLAUDE.md

## 프로젝트

**서버 작업, 언제 돌려야 탄소가 가장 적을까: 탄소 인지 작업 스케줄링.** 미뤄도 되는 서버 작업을 전기가 깨끗한 시간으로 옮기면 탄소가 얼마나 주는지 전력거래소 공개 데이터와 시뮬레이션으로 확인한다. 헤드라인: 새벽 2시 일괄 실행 대비 연간 9.1% 절감, 마감 위반 0건(전력시장 거래량 기준).

## 공모전

- 숭실대 2026학년도 ESD 비교과 공모전, 출품자 박수진
- 마감: **2026-11-16(월)**, 슈패스로 접수
- 제출물: 참가 신청서 + PPT·PDF 각 1부(20페이지 내외) + 발표 영상(PPT 내용 발표, 10분 이내). 신청서를 뺀 파일은 ZIP 1개로
- ZIP 파일명: `2026 ESD 비교과 공모전(탄소 인지 작업 스케줄링)_박수진.zip` (주제명은 "탄소 인지 작업 스케줄링" 고정)
- 심사(서류만): 주제 적합성 40, 전공 연계성 30, 완성도 30. 심사위원은 비전공자일 수 있으니 어려운 개념에는 쉬운 비유를 붙인다
- SDG: 7.3, 9.4, 13.3

## 폴더

| 폴더 | 역할 |
|---|---|
| `scripts/` | 모든 실행 스크립트와 설정(`config_emission_factors.py`, `config_simulation.py`, `common.py`) |
| `02_데이터/` | `SOURCES.md`(데이터 출처), `references.md`(배경 통계·배출계수·요금제 원문), `raw/`(원본, git 제외) |
| `03_분석/` | 분석 결과 CSV·그래프, `summary_stage1.md`, `stage2_summary.md`(스크립트가 자동 생성, 직접 고치지 않음) |
| `04_발표자료/` | `slides_draft.md`(원고·대본·신청서 문구), `figures/`, 제출용 PPTX·PDF(git 제외), `_build/`(git 제외) |
| `docs/decisions/` | 주요 판단 기록 |
| `01_공고_신청서/`, `05_영상/`, `99_제출/` | 공모전 서류, 영상, 제출 ZIP (git 제외) |

## 실행 순서

```bash
pip install -r requirements.txt
python scripts/00_download_data.py      # 원본 다운로드(로그인·인증키 불필요)
python scripts/01_profile_raw.py
python scripts/02_carbon_intensity.py   # 1단계: 시간별 탄소집약도
python scripts/03_stage1_report.py
python scripts/04_simulate.py           # 2단계: 시뮬레이션(약 1.5분)
python scripts/05_stage2_report.py
python scripts/06_presentation_figures.py
python scripts/07_slide_figures.py
python scripts/08_build_deck.py         # 3단계: PPTX 초안
powershell -ExecutionPolicy Bypass -File scripts/09_export_deck.ps1   # 글꼴 포함 PPTX + PDF
```

- 08, 09는 **Windows + Microsoft PowerPoint + Pretendard 글꼴**이 있어야 한다(09는 PowerPoint COM 자동화). `09_export_deck.ps1`은 UTF-8 BOM으로 저장해야 한글 경로가 깨지지 않는다.
- 숫자가 바뀌면 02 이후를 순서대로 다시 돌리면 요약 문서·그림·PPTX가 모두 갱신된다. PPTX 대본은 `slides_draft.md`의 대본 블록(19개)에서 읽는다.

## git에서 제외한 것과 이유

- `02_데이터/raw/`: 원본 데이터. `00_download_data.py`로 다시 받는다
- `04_발표자료/*.pptx`, `*.pdf`, `_build/`: 제출본. 표지에 학번이 들어가고 스크립트로 다시 만든다
- `04_발표자료/author.local.txt`: 표지의 소속·학번·이름 한 줄(`숭실대학교 컴퓨터학부 <학번> 박수진`). 개인정보라 저장소에 넣지 않는다. 없으면 이름만 표시
- `01_공고_신청서/`, `05_영상/`, `99_제출/`, `*.hwp`, `*.zip`
- 저장소: https://github.com/cl-o-lc/carbon-aware-scheduling (공개 전 점검 완료: 원본 데이터·학번·토큰 없음. 커밋 작성자 이메일은 공개 유지로 결정)

## 작업 규칙

- 자료에 쓰는 모든 숫자는 스크립트 출력이나 `references.md`에 출처가 있는 것만. 추정·창작 금지
- 가정은 가정이라고 표시한다(배출계수 대체값, DVFS 모델, 가상 작업 세트 등)
- 문서·PPT는 한국어, 문장에 em dash 문자 금지(쉼표, 괄호, 문장 분리로 대신)
- 사용자가 방향을 정한다. 단계마다 멈추고 보고하고, 판단이 필요한 지점은 선택지와 추천안을 보여준다
- 커밋 메시지는 한국어, 단계별로 나눈다

## 현재 상태 (2026-11-14)

- 완료: 데이터 수집, 탄소집약도 분석, 시뮬레이션, 발표 원고, 제출용 PPTX·PDF 19장(표지 제목 40pt, 그림 없는 표지로 확정), README
- 남은 일
  1. 사용자가 GitHub 저장소를 public으로 전환(17장 "코드와 데이터 출처 공개" 문구의 전제)
  2. 발표 영상 녹화(대본: `slides_draft.md` 또는 PPTX 발표자 노트, 2,225음절, 약 7.4~8.2분)
  3. 참가 신청서 작성(문구: `slides_draft.md` 맨 아래)
  4. ZIP 묶기(PPT, PDF, 영상) → `99_제출/`
  5. 슈패스 제출(11/16까지)

## 미해결

- 전력거래소 5분 단위 BTM·PPA 태양광 추정치: 엑셀 다운로드가 브라우저에서도 HTTP 503(2026-11-06). 받으면 `02_데이터/raw/kpx_solar_5min/2025-MM.xlsx`로 넣고 시간별 집계 스크립트를 새로 만들어 `grid` 곡선(`common.py`의 `CURVES`)을 만든다. 그 전까지 시장 밖 태양광은 EPSIS 월별 배수 가정(`monthly`, C 13.9%)으로 민감도만 둔다
- 주 결과는 A안(`market`, 전력시장 거래량만). 판단 이유는 `docs/decisions/` 참고
