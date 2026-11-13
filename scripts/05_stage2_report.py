"""2단계 결과 요약 문서 생성: 03_분석/stage2_summary.md
04_simulate.py 산출물(03_분석/stage2/)만 읽어 숫자를 채운다.
"""
from __future__ import annotations

import json
import sys

import pandas as pd

import config_simulation as cfg
from common import CURVES, OUT, weekend_compare

S2 = OUT / "stage2"


POL = {"A": "A 현재 관행", "A'": "A' 도착 즉시", "B": "B 탄소 탐욕", "C": "C 에이징+가능성 검사", "D": "D C+DVFS",
       "E": "E 전주 예측", "C7": "C7 주말 이동 금지"}


def f1(x):
    return f"{x:.1f}"


def main():
    meta = json.loads((S2 / "stage2_results.json").read_text(encoding="utf-8"))
    names, main_name, figs, ex = meta["curves"], meta["main_curve"], meta["figures"], meta["extras"]
    jobs = pd.read_csv(S2 / "jobs.csv")
    rep = pd.read_csv(S2 / "representative_days.csv")
    order = [main_name] + [n for n in names if n != main_name]
    order = [n for n in order if n in names]

    L = ["# 2단계 결과: 탄소 인지 작업 스케줄링 시뮬레이션", "",
         "`scripts/05_stage2_report.py`가 `03_분석/stage2/` 산출물로 자동 생성한 문서다. 직접 고치지 말고 스크립트를 다시 돌린다.", ""]
    L.append(f"- 주 결과 곡선: **{CURVES[main_name][0]}** (`{main_name}`)")
    if main_name != "grid":
        L.append("- 전력거래소 5분 단위 비계량 태양광 파일이 아직 없어 '실제 전력망 기준' 곡선을 만들지 못했다. "
                 "파일을 넣고 다시 돌리면 주 결과가 그 곡선으로 바뀐다.")
    L.append(f"- 함께 계산한 곡선: " + ", ".join(f"{CURVES[n][0]} (`{n}`)" for n in order))
    dres = pd.read_csv(S2 / f"daily_results_{main_name}.csv", parse_dates=["date"])
    d0, d1, nd = dres["date"].min(), dres["date"].max(), dres["date"].nunique()
    days_note = (f"실험일이 365일이 아니라 {nd}일({d0:%m-%d}~{d1:%m-%d} 시작일)인 이유: 하루 실험은 전날 20시에 시작하고 E가 7일 전 곡선을 쓰므로 "
                 f"1월 초 {(d0 - pd.Timestamp('2025-01-01')).days}일을 빼고, 주간 작업 마감(7일 뒤)과 마감 초과 여유 {cfg.LATE_GRACE_H:g}시간이 "
                 f"2025년 데이터 안에 들어와야 하므로 12월 말 {(pd.Timestamp('2025-12-31') - d1).days}일을 뺐다.")
    L.append(f"- 실험 일수: {nd}일. {days_note}")
    L.append("- 실험 방식: 같은 하루치 작업 세트(30개)가 매일 들어온다고 보고, 날짜마다 독립 실험으로 돌린 뒤 합산")
    L.append("")

    # 핵심 발견
    t_main = pd.read_csv(S2 / f"annual_{main_name}.csv").set_index("정책코드")
    e0 = ex[main_name]
    w0 = e0["주말이동"]
    wk = weekend_compare(main_name)
    dl = e0["지연"]
    rng = {n: pd.read_csv(S2 / f"annual_{n}.csv").set_index("정책코드").loc["C", "A 대비 절감률(%)"] for n in names}
    s_lo, s_hi = min(cfg.STATIC_FRAC_SENS), max(cfg.STATIC_FRAC_SENS)
    dlo = t_main.loc[f"D(정적 {s_hi:.2f})", "A 대비 절감률(%)"]
    dhi = t_main.loc[f"D(정적 {s_lo:.2f})", "A 대비 절감률(%)"]
    L += ["## 핵심 발견", "",
          "**결론: 마감 유연성이 절감을 결정한다.** 같은 스케줄러라도 작업을 얼마나 오래 미룰 수 있느냐에 따라 절감률이 크게 달라진다.", "",
          f"1. **헤드라인(C, 스케줄링만):** 현재 관행(새벽 2시 고정) 대비 연간 **{rng[main_name]:.1f}%** 절감, 마감 위반 0건 "
          f"({CURVES[main_name][0]})."
          + (f" 시장 밖 태양광을 월별 비율로 반영하면 약 {rng['monthly']:.1f}%(가정)." if "monthly" in rng and main_name != "monthly" else ""),
          f"2. **당일 마감 작업만 보면 {e0['구분별']['당일']['C']:.1f}%.** 8~14시 마감 안에서만 움직일 수 있고 슬롯 2개를 나눠 써서, 한낮을 다 쓰지 못한다.",
          f"3. **주말 이동이 절감의 대부분이다.** 같은 정책 C에서 주간 작업이 주말까지 기다리지 못하게 막으면(C7) {wk['전체']['C7']:.1f}%, "
          f"허용하면 {wk['전체']['C']:.1f}%(= 헤드라인 C). 전체 {wk['전체']['일수']}일 기준. 평일에 시작한 {wk['평일 시작']['일수']}일만 보면 "
          f"{wk['평일 시작']['C7']:.1f}% → {wk['평일 시작']['C']:.1f}%.",
          f"4. **현재 관행 대비(곡선 기준):** 심야 2시에서 한낮(10~14시)으로 옮기면 연간 {e0['곡선_연간']['심야→한낮 절감률(%)']:.1f}%, "
          f"봄 {e0['곡선_봄']['심야→한낮 절감률(%)']:.1f}%, 겨울 {e0['곡선_겨울']['심야→한낮 절감률(%)']:.1f}%. 저녁에서 옮길 때({e0['곡선_연간']['저녁→한낮 절감률(%)']:.1f}%)보다 작다.",
          f"5. **마감 위반 0건은 에이징이 아니라 15분마다 수행하는 EDF 가능성 검사(schedulability test) 덕분이다.** "
          f"에이징 강도 γ는 절감률과 대기 시간의 균형만 조절한다(8장). 탄소만 쫓는 B는 {int(t_main.loc['B', 'late']):,}건 위반.",
          f"6. **예측의 한계:** 완전 정보 가정을 풀고 전주 같은 요일 값으로 예측하면(E) 절감률이 {e0['예측']['차이(%p)']:.1f}%p 줄어든다 "
          f"({e0['예측']['C 절감률(%)']:.1f}% → {e0['예측']['E 절감률(%)']:.1f}%).",
          f"7. **기다리는 시간:** 당일 작업의 완료 지연은 중앙값 {dl['C']['당일']['중앙값']:.1f}시간(A는 {dl['A']['당일']['중앙값']:.1f}시간), "
          f"주간 작업은 중앙값 {dl['C']['주간']['중앙값']:.1f}시간. 전체 평균 지연이 큰 것은 주간 작업이 주말을 기다리기 때문이다(2-1절).",
          f"8. **DVFS를 더하면(D) A 대비 전체 절감이 모델 가정에 따라 {dlo:.0f}~{dhi:.0f}%로 커진다** (정적 전력 비율 {s_hi}~{s_lo}, 스케줄링 효과 포함), "
          f"근거 있는 기준값 {cfg.STATIC_FRAC}에서 {t_main.loc['D', 'A 대비 절감률(%)']:.1f}%. 6장 참고.",
          "",
          "외부 연구와 비교: Wiesner et al.(Middleware '21)도 \"shifting workloads whose results are not needed by the next working day can already reduce emissions by over 5 % across all regions\", "
          "\"shifting delay-tolerant workloads towards weekends can result in more than 20 % savings in most regions\"라고 보고했다(references.md 4-4). "
          "미룰 수 있는 기간이 길수록, 특히 주말까지 미룰 수 있을 때 절감이 커진다는 방향이 같다.", ""]

    # 작업 세트
    L += ["## 1. 작업 세트", "",
          f"시드 {cfg.SEED}로 생성(`03_분석/stage2/jobs.csv`). 도착은 전날 20시~당일 2시, 서버 동시 실행 슬롯 {cfg.SLOTS}개.", "",
          "| 마감 구분 | 개수 | 마감 시각 | 실행 시간 합계(h) | 실행 시간 범위(h) | 평균 전력(W) | 메모리 바운드 비율 |", "|---|---|---|---|---|---|---|"]
    dl_txt = {"당일": "당일 8~14시", "익일": "다음 날 8~14시", "주간": "7일 뒤 8~14시"}
    for c in ("당일", "익일", "주간"):
        s = jobs[jobs["cls"] == c]
        L.append(f"| {c} | {len(s)} | {dl_txt[c]} | {s['runtime'].sum():.2f} | {s['runtime'].min()}~{s['runtime'].max()} | "
                 f"{s['power_w'].min():.0f}~{s['power_w'].max():.0f} | {s['mem'].min():.2f}~{s['mem'].max():.2f} |")
    L.append(f"| 합계 | {len(jobs)} | | {jobs['runtime'].sum():.2f} | | | |")
    L.append("")
    L.append("작업 이름: " + ", ".join(jobs["name"]))
    L.append("")

    # 정책별 연간 표
    L += ["## 2. 정책별 연간 결과", ""]
    for n in order:
        t = pd.read_csv(S2 / f"annual_{n}.csv").set_index("정책코드")
        L += [f"### {CURVES[n][0]} (`{n}`)", "",
              "| 정책 | 총 배출(kgCO2eq) | A 대비 절감률 | 마감 위반(건) | 위반 발생 일수 | 평균 완료 지연(h) | 에너지(kWh) |",
              "|---|---|---|---|---|---|---|"]
        for p in ["A", "A'", "B", "C", "D", "E", "C7"]:
            r = t.loc[p]
            L.append(f"| {r['정책']} | {r['emis_g'] / 1000:,.1f} | {r['A 대비 절감률(%)']:.1f}% | {int(r['late']):,} | "
                     f"{int(r['late_days'])} | {r['delay_h']:.1f} | {r['energy_kwh']:,.0f} |")
        L.append("")
        L.append("평균 완료 지연 = 완료 시각 - 도착 시각 - 실행 시간(f=1). 주간 작업이 며칠씩 기다리는 효과가 포함된다.")
        L.append("")

    e = ex[main_name]
    L += [f"### 2-1. 마감 구분별 완료 지연 ({CURVES[main_name][0]}, 단위 시간)", "",
          "모든 실험일의 작업별 지연(완료 시각 - 도착 시각 - 실행 시간)을 모아 계산.", "",
          "| 정책 | 당일 평균 | 당일 중앙값 | 당일 90% | 익일 평균 | 익일 중앙값 | 주간 평균 | 주간 중앙값 | 주간 90% |",
          "|---|---|---|---|---|---|---|---|---|"]
    for p in ["A", "B", "C", "D", "E", "C7"]:
        d = e["지연"][p]
        L.append(f"| {POL.get(p, p)} | {d['당일']['평균']:.1f} | {d['당일']['중앙값']:.1f} | {d['당일']['90백분위']:.1f} | "
                 f"{d['익일']['평균']:.1f} | {d['익일']['중앙값']:.1f} | {d['주간']['평균']:.1f} | {d['주간']['중앙값']:.1f} | {d['주간']['90백분위']:.1f} |")
    L.append("")
    # 심야 → 한낮
    L += ["## 3. 심야(현재 관행)에서 한낮으로 옮길 때", "",
          f"곡선 값만으로 본 비교({CURVES[main_name][0]}). 심야 = 2~3시, 한낮 = 10~14시 평균, 저녁 = 19~23시 평균, 단위 gCO2eq/kWh.", "",
          "| 구분 | 심야 2시 | 한낮 | 저녁 | **심야→한낮 절감률** | 저녁→한낮 절감률 |", "|---|---|---|---|---|---|"]
    for k in ("연간", "봄", "여름", "가을", "겨울"):
        v = e[f"곡선_{k}"]
        L.append(f"| {k} | {f1(v['심야2시'])} | {f1(v['한낮10~14시'])} | {f1(v['저녁19~23시'])} | "
                 f"**{v['심야→한낮 절감률(%)']:.1f}%** | {v['저녁→한낮 절감률(%)']:.1f}% |")
    L.append("")
    L.append("심야에서 한낮으로 옮기는 효과는 저녁에서 한낮으로 옮기는 효과보다 작다. 현재 관행이 이미 저녁보다는 조금 깨끗한 심야에 돌고 있기 때문이다.")
    L.append("")
    L.append("시뮬레이션에서 마감 구분별 A 대비 절감률(연간 합):")
    L.append("")
    L.append("| 마감 구분 | C | D |")
    L.append("|---|---|---|")
    for c, v in e["구분별"].items():
        L.append(f"| {c} | {v['C']:.1f}% | {v['D']:.1f}% |")
    L.append("")
    L.append("당일 마감 작업은 8~14시 마감 안에서만 움직일 수 있고 슬롯 2개를 나눠 써야 해서, 곡선상의 심야→한낮 차이만큼 줄지 못한다.")
    L.append("")

    # 주말 이동
    w = e["주말이동"]
    wk = weekend_compare(main_name)
    L += ["## 4. 주간 작업을 주말까지 미루는 효과", "",
          "두 경우 모두 같은 정책 C다. C7은 주간 작업도 다음 날 14시까지만 미룰 수 있게 막은 것이고, C(헤드라인)는 7일 뒤 마감까지 미룰 수 있다.", "",
          "| 실험일 | 일수 | 주말 이동 금지(C7) | 허용(C) | 차이 | 주간 작업이 주말·공휴일에 시작한 비율(C7 → C) |",
          "|---|---|---|---|---|---|"]
    for key in ("전체", "평일 시작", "주말·공휴일 시작"):
        v = wk[key]
        L.append(f"| {key}{' (헤드라인과 같은 기준)' if key == '전체' else ''} | {v['일수']} | {v['C7']:.1f}% | {v['C']:.1f}% | "
                 f"+{v['C'] - v['C7']:.1f}%p | {v['주말시작비율_C7']:.1f}% → {v['주말시작비율_C']:.1f}% |")
    L += ["", f"- 평일 시작 실험에서 주간 작업 6개만 보면 C가 C7보다 {w['주간 작업만: C7 대비 C 절감률(%)']:.1f}% 덜 배출한다.",
          "- 주말·공휴일에 시작한 실험은 C7도 다음 날(주말)까지는 미룰 수 있어 차이가 작다.", ""]

    # 계절·요일
    L += ["## 5. 계절별, 실험 시작일 요일별 A 대비 절감률", "", "| 구분 | B | C | D |", "|---|---|---|---|"]
    for k in ("봄", "여름", "가을", "겨울"):
        v = e["season별"][k]
        L.append(f"| {k} | {v['B']:.1f}% | {v['C']:.1f}% | {v['D']:.1f}% |")
    for k in ("평일", "주말·공휴일"):
        v = e["daykind별"][k]
        L.append(f"| 시작일 {k} | {v['B']:.1f}% | {v['C']:.1f}% | {v['D']:.1f}% |")
    L.append("")

    # DVFS
    t = pd.read_csv(S2 / f"annual_{main_name}.csv").set_index("정책코드")
    L += ["## 6. DVFS(D) 에너지와 정적 전력 가정 민감도", "",
          "| 정적 전력 비율 | 에너지(kWh) | C 대비 에너지 절감률 | A 대비 배출 절감률 | 마감 위반 |", "|---|---|---|---|---|"]
    for p, sf in ((f"D(정적 {min(cfg.STATIC_FRAC_SENS):.2f})", min(cfg.STATIC_FRAC_SENS)), ("D", cfg.STATIC_FRAC),
                  (f"D(정적 {max(cfg.STATIC_FRAC_SENS):.2f})", max(cfg.STATIC_FRAC_SENS))):
        d = e["DVFS 에너지"][p]
        L.append(f"| {sf:.2f}{' (기준)' if p == 'D' else ''} | {d['에너지(kWh)']:,.0f} | {d['C 대비 에너지 절감률(%)']:.1f}% | "
                 f"{t.loc[p, 'A 대비 절감률(%)']:.1f}% | {int(t.loc[p, 'late'])} |")
    L.append("")
    L.append("D의 절감은 대부분 주파수를 낮춰 에너지를 줄인 효과다. 정적 전력(주파수와 무관하게 드는 전력) 비율을 얼마로 보느냐에 따라 크게 달라지므로, "
             "발표에서는 기준값 하나보다 범위로 말하는 것이 안전하다.")
    L.append("")

    # 예측
    p = e["예측"]
    L += ["## 7. 예측 곡선(E)과 완전 정보(C)의 차이", "",
          f"- 완전 정보 가정을 풀면 절감률이 {p['차이(%p)']:.1f}%p 줄어든다: C(실제 곡선을 미리 안다고 가정) {p['C 절감률(%)']:.1f}% → "
          f"E(전주 같은 요일 같은 시각 값으로 예측) {p['E 절감률(%)']:.1f}%.",
          "- 확률과통계 연결: 예측값은 '지난주 같은 요일 같은 시각'이라는 가장 단순한 추정이다. 계절 평균, 이동평균, 일기예보(일사량) 같은 정보를 더하면 차이를 줄일 여지가 있다.", ""]
    dr = pd.read_csv(S2 / f"daily_results_{main_name}.csv")
    base_d = dr[dr["policy"] == "A"].set_index("date")["emis_g"]
    L += ["날짜별로 보면(현재 관행 A 대비 절감률):", "",
          "| 정책 | 날짜별 절감률 중앙값 | 가장 나쁜 날 | A보다 배출이 늘어난 날 |", "|---|---|---|---|"]
    for pol in ("C", "E"):
        sav = (1 - dr[dr["policy"] == pol].set_index("date")["emis_g"] / base_d) * 100
        L.append(f"| {POL.get(pol, pol)} | {sav.median():.1f}% | {sav.min():.1f}% | {int((sav < 0).sum())}일 / {len(sav)}일 |")
    L.append("")

    # 에이징 민감도
    L += ["## 8. 에이징 강도(γ) 민감도", "",
          "γ가 작을수록 일찍 타협해 대기가 짧고, 클수록 깨끗한 시간을 오래 기다린다. γ=inf는 에이징 없이 마감 보호만 둔 경우.", "",
          "| γ | A 대비 절감률 | 마감 위반 | 평균 완료 지연(h) |", "|---|---|---|---|"]
    for g in cfg.AGING_GAMMA_SENS:
        key = "C" if g == cfg.AGING_GAMMA else f"C(γ={g:g})"
        r = t.loc[key]
        L.append(f"| {g:g}{' (기준)' if key == 'C' else ''} | {r['A 대비 절감률(%)']:.1f}% | {int(r['late'])} | {r['delay_h']:.1f} |")
    L.append("")
    L.append(f"마감 위반 0건은 에이징이 아니라 15분마다 수행하는 EDF 가능성 검사 덕분이다. 운영체제의 실시간 스케줄링에서 "
             "'이 작업들을 모두 마감 안에 끝낼 수 있는가'를 미리 따지는 schedulability test와 같은 개념이다. "
             "에이징 γ는 절감률(과 대기 시간)만 조절한다. "
             f"기준값 γ={cfg.AGING_GAMMA:g}는 2025년 데이터로 여러 값을 돌려 본 뒤 중간값으로 골랐다(같은 데이터로 고른 값이라는 점은 한계).")
    L.append("")

    # 대표일
    L += ["## 9. 대표일", "",
          "고르는 기준(스크립트 자동): 봄 맑은 평일 = 3~5월 평일 중 한낮(10~14시) 탄소집약도가 가장 낮은 날, "
          "여름·겨울 평일 = 그 계절 평일 평균 곡선과 가장 비슷한 날.", ""]
    for n in rep["곡선"].unique():
        L += [f"### {CURVES[n][0]} (`{n}`)", "", "| 대표일 | 날짜 | 정책 | 배출(g) | A 대비 절감률 | 에너지(kWh) | 마감 위반 | 평균 지연(h) |",
              "|---|---|---|---|---|---|---|---|"]
        sub = rep[rep["곡선"] == n]
        for (lab, day), g in sub.groupby(["대표일", "날짜"], sort=False):
            base = g[g["정책"].str.startswith("A ")]["배출(g)"].iloc[0]
            for r in g.itertuples(index=False):
                L.append(f"| {lab} | {day} | {r.정책} | {r._4:,.0f} | {(1 - r._4 / base) * 100 + 0.0:.1f}% | {r._5:.2f} | {r._6} | {r._7:.1f} |")
        L.append("")

    # 그래프
    L += ["## 10. 그래프", ""]
    for k, v in figs.items():
        L.append(f"- {k}: `{v}`")
    L.append("")

    # 가정
    L += ["## 11. 가정 목록", "",
          f"1. 작업 세트는 가상이다. 시드 {cfg.SEED}, 30개(당일 18, 익일 6, 주간 6), 실행 시간·전력·메모리 바운드 비율은 `scripts/config_simulation.py`의 범위에서 무작위.",
          "2. 같은 작업 세트가 매일 들어오고, 날짜마다 독립 실험으로 본다(다른 날 작업과 슬롯을 다투지 않음). 주간 작업이 매일 들어오는 것은 실제보다 많다.",
          f"2-1. {days_note}",
          f"3. 서버 동시 실행 슬롯 {cfg.SLOTS}개, 작업은 한번 시작하면 끝까지 실행(중단·이동 없음).",
          f"4. 스케줄러는 {int(cfg.STEP_H * 60)}분마다 대기열을 보고, 탄소 곡선은 1시간 단위 값을 쓴다.",
          "5. 현재 관행(A)은 모든 작업을 새벽 2시에 마감 빠른 순으로 대기열에 넣는다. 2개 슬롯이 다 차면 오전·낮까지 이어서 돈다.",
          "6. C, D는 실제 탄소 곡선을 미리 안다고 가정(완전 정보). E만 전주 같은 요일 값으로 예측.",
          f"7. DVFS: 주파수 {cfg.FREQS}, 동적 전력 ∝ f³(전압이 주파수에 비례), 정적 전력 비율 {cfg.STATIC_FRAC}(민감도 {cfg.STATIC_FRAC_SENS}), "
          "실행 시간은 CPU 바운드 부분만 1/f로 늘어남. 주파수는 마감 안에서 배출(에너지 × 실행 구간 평균 탄소)이 가장 적은 것을 고름.",
          "8. 에너지는 작업이 도는 동안의 전력만 센다. 작업이 없을 때 서버 대기 전력, 냉방 등 데이터센터 부대 전력(PUE)은 넣지 않았다.",
          f"9. 에이징 γ={cfg.AGING_GAMMA:g}, 마감 보호는 EDF 가능성 검사(f=1 기준, 빈틈 메우기 없는 보수적 검사).", ""]

    # 한계
    L += ["## 12. 한계", "",
          "1. 탄소 곡선은 평균 배출계수 기준이다. 작업 하나를 옮겼을 때 실제로 늘고 주는 발전기(한계 발전기)의 탄소와는 다를 수 있다(1단계 한계 2번).",
          "2. 대학 서버 몇 대의 작업 이동은 전력망 전체에 영향을 주지 않는다고 가정했다. 많은 데이터센터가 동시에 한낮으로 몰리면 곡선 자체가 바뀔 수 있다.",
          "3. 작업 세트와 전력 값은 가상이다. 절감률은 '이런 성격의 작업이라면'이라는 조건부 결과다.",
          "4. DVFS 모델은 단순화했다(f³, 정적 비율 고정, 메모리 바운드 비율 고정). 실제 CPU는 전압을 일정 수준 아래로 못 내리고, 주파수 단계도 더 많다.",
          "5. 완전 정보 가정(C, D)은 실제보다 낙관적이다. 예측 오차의 영향은 E로 따로 보였다.",
          "6. 에이징 강도 γ는 같은 2025년 데이터로 보고 골랐다.", ""]
    out = OUT / "stage2_summary.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
