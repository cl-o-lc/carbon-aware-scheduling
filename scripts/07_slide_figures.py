"""발표 슬라이드 전용 그림(16:9, 큰 글씨)을 04_발표자료/figures/에 만든다.

  05_탄소곡선_요금시간대.png  2025년 봄·가을 평일 탄소 곡선 + 2026년 개편 후 봄·가을 평일 요금 시간대
  06_스케줄러_흐름도.png      15분마다 도는 판단 흐름
  07_주말이동_비교.png        같은 정책 C에서 주간 작업 주말 이동 금지(C7) vs 허용(C, 헤드라인)
  08_정책별_절감률_ACD.png    A, C, D 연간 절감률(D는 정적 전력 가정 범위)

사용법:  python scripts/07_slide_figures.py   (02, 04 스크립트를 먼저 실행)
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

import config_simulation as cfg
from common import (C_AQUA, C_BLUE, C_INK, C_INK2, C_ORANGE, CURVES, OUT, ROOT, main_curve, setup_matplotlib,
                    weekend_compare)

DEST = ROOT / "04_발표자료" / "figures"
W, H = 13.333, 7.5  # 16:9 (인치)

# 2026년 개편 후 봄·가을 평일 요금 시간대 (references.md 5-2, 5-3). (시작, 끝, 이름)
TOU_SPRING_FALL_WEEKDAY = [(0, 8, "경부하"), (8, 15, "중간부하"), (15, 21, "최대부하"), (21, 22, "중간부하"), (22, 24, "경부하")]
TOU_COLOR = {"경부하": "#e8f1fc", "중간부하": "#fbe3d6", "최대부하": "#f5b99a"}  # 요금이 비쌀수록 진하게


def big(plt):
    plt.rcParams.update({"savefig.bbox": "standard", "savefig.dpi": 200, "font.size": 18, "axes.titlesize": 24, "axes.labelsize": 19, "xtick.labelsize": 16,
                         "ytick.labelsize": 16, "legend.fontsize": 16})


def fig_curve_tou(plt, name: str):
    h = pd.read_csv(OUT / CURVES[name][1], parse_dates=["date"])
    if "daytype" not in h.columns:  # 곡선 파일에 달력 정보가 없으면 붙인다
        import holidays
        kr = holidays.KR(years=2025)
        h["daytype"] = np.where((h["date"].dt.dayofweek >= 5) | h["date"].dt.date.map(lambda x: x in kr), "주말·공휴일", "평일")
    sel = h[h["date"].dt.month.isin([3, 4, 5, 9, 10]) & (h["daytype"] == "평일")]
    c = sel.groupby("slot")["ci"].mean()
    fig, ax = plt.subplots(figsize=(W, H))
    lo, hi = c.min() - 25, c.max() + 22
    for a, b, k in TOU_SPRING_FALL_WEEKDAY:
        ax.axvspan(a - 0.5, b - 0.5, color=TOU_COLOR[k], linewidth=0, zorder=0)
        if b - a >= 2:  # 좁은 구간(21~22시 중간부하)은 이름을 생략해 겹침 방지, 색으로만 표시
            ax.text((a + b) / 2 - 0.5, hi - 4, k, ha="center", va="top", fontsize=17, color=C_INK, fontweight="bold")
    ax.plot(c.index, c.values, color=C_INK, linewidth=3.5, marker="o", markersize=7, zorder=3)
    night = cfg.NIGHT_SLOT
    m = int(c.idxmin())
    ax.scatter([night], [c[night]], s=260, color=C_BLUE, zorder=4, edgecolor="white", linewidth=2)
    ax.annotate(f"현재 관행: 새벽 2시\n{c[night]:.0f} g/kWh (요금 가장 쌈)", (night, c[night]), xytext=(night + 1.2, c[night] - 30),
                fontsize=17, color=C_INK, arrowprops=dict(arrowstyle="-", color=C_INK2, lw=1.5))
    ax.scatter([m], [c[m]], s=260, color=C_AQUA, zorder=4, edgecolor="white", linewidth=2)
    ax.annotate(f"가장 깨끗한 시각: {m}시\n{c[m]:.0f} g/kWh", (m, c[m]), xytext=(m + 1.5, c[m] - 4), fontsize=17, color=C_INK,
                arrowprops=dict(arrowstyle="-", color=C_INK2, lw=1.5))
    ax.set_xlim(-0.5, 23.5)
    ax.set_ylim(lo, hi)
    ax.set_xticks(range(0, 24, 3))
    ax.set_xticklabels([f"{x}시" for x in range(0, 24, 3)])
    ax.set_ylabel("탄소집약도 (gCO2eq/kWh)")
    ax.grid(axis="x", visible=False)
    ax.set_title("평일에는 가장 싼 시간(심야)과 가장 깨끗한 시간(한낮)이 다르다", pad=14)
    fig.text(0.01, 0.012, "탄소 곡선: 2025년 봄·가을(3~5월, 9~10월) 평일 평균, 전력시장 거래량 기준.\n"
             "요금 시간대: 2026년 개편 후 봄·가을 평일(여름도 같음, 겨울은 다름, 21~22시는 중간부하), 계절·시간대별 요금 종별 공통.",
             fontsize=12.5, color=C_INK2)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(DEST / "05_탄소곡선_요금시간대.png")
    plt.close(fig)
    return {"night": float(c[night]), "min_slot": m, "min": float(c[m])}


def fig_flow(plt):
    fig, ax = plt.subplots(figsize=(W, H))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 56)
    ax.axis("off")

    def box(x, y, w, h, text, fc, bold=False):
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.6,rounding_size=1.5",
                                    fc=fc, ec=C_INK2, lw=1.8))
        ax.text(x, y, text, ha="center", va="center", fontsize=18, color=C_INK, fontweight="bold" if bold else None,
                linespacing=1.4)

    def arrow(p, q, label=None, lx=0, ly=0):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=26, lw=2.2, color=C_INK2))
        if label:
            ax.text((p[0] + q[0]) / 2 + lx, (p[1] + q[1]) / 2 + ly, label, fontsize=17, color=C_INK, ha="center",
                    va="center", fontweight="bold")

    box(50, 50, 40, 6, "15분마다: 대기 중인 작업 확인", "#e8f1fc", bold=True)
    box(50, 36, 62, 9, "① 마감 가능성 검사\n지금 아무것도 안 돌려도 마감 빠른 순으로 모두 끝낼 수 있나?", "#ffffff")
    box(14, 20, 24, 9, "마감이 급한 작업부터\n즉시 실행", "#fbe3d6", bold=True)
    box(56, 20, 44, 9, "② 탄소 기준 (에이징 반영)\n지금이 남은 시간 중 충분히 깨끗한가?\n오래 기다릴수록 기준이 넓어진다", "#ffffff")
    box(42, 5, 22, 6, "빈 슬롯에서 실행", "#dff3ea", bold=True)
    box(78, 5, 26, 6, "다음 15분까지 대기", "#f2f1ec", bold=True)
    arrow((50, 46.6), (50, 41))
    arrow((26, 31.5), (18, 25), "아니오", lx=-3, ly=1.5)
    arrow((56, 31.4), (56, 25), "예", lx=3)
    arrow((48, 15.3), (44, 8.3), "예", lx=-3)
    arrow((66, 15.3), (74, 8.3), "아니오", lx=5)
    ax.add_patch(FancyArrowPatch((92, 5), (71, 50), connectionstyle="arc3,rad=0.35", arrowstyle="-|>",
                                 mutation_scale=22, lw=1.8, color=C_INK2, linestyle="--"))
    ax.text(97, 30, "다시\n확인", fontsize=15, color=C_INK2, ha="center")
    ax.text(1, 44, "마감 위반 0건은\n①(가능성 검사) 덕분\n\n에이징은 ②의 기준만\n조절해 절감률을 정함",
            fontsize=15, color=C_INK2, va="top")
    fig.tight_layout()
    fig.savefig(DEST / "06_스케줄러_흐름도.png")
    plt.close(fig)


def fig_weekend(plt, name: str):
    wk = weekend_compare(name)["전체"]
    fig, ax = plt.subplots(figsize=(W, H))
    labels = ["주간 작업을\n주말까지 못 미룸 (C7)", "주말까지 미룰 수 있음\n(C, 헤드라인)"]
    vals = [wk["C7"], wk["C"]]
    bars = ax.bar(labels, vals, color=[C_INK2, C_BLUE], width=0.55)
    for b_, v in zip(bars, vals):
        ax.text(b_.get_x() + b_.get_width() / 2, v + 0.25, f"{v:.1f}%", ha="center", va="bottom", fontsize=30,
                fontweight="bold", color=C_INK)
    ax.set_ylim(0, max(vals) * 1.3)
    ax.set_ylabel("현재 관행(새벽 2시) 대비 절감률 (%)")
    ax.grid(axis="x", visible=False)
    ax.set_title("같은 스케줄러, 기다릴 수 있는 기간만 다르게", pad=14)
    fig.text(0.01, 0.01, f"2025년 {wk['일수']}일 시뮬레이션 합계, 전력시장 거래량 기준. 두 경우 모두 마감 위반 0건.",
             fontsize=13, color=C_INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(DEST / "07_주말이동_비교.png")
    plt.close(fig)
    return wk


def fig_acd(plt, name: str):
    t = pd.read_csv(OUT / "stage2" / f"annual_{name}.csv").set_index("정책코드")
    s_lo, s_hi = min(cfg.STATIC_FRAC_SENS), max(cfg.STATIC_FRAC_SENS)
    v = {p: t.loc[p, "A 대비 절감률(%)"] for p in ("A", "C", "D")}
    d_lo, d_hi = t.loc[f"D(정적 {s_hi:.2f})", "A 대비 절감률(%)"], t.loc[f"D(정적 {s_lo:.2f})", "A 대비 절감률(%)"]
    fig, ax = plt.subplots(figsize=(W, H))
    labels = ["A 현재 관행\n(새벽 2시 일괄)", "C 탄소 인지 스케줄링\n(헤드라인)", "D C + DVFS\n(모델 가정)"]
    bars = ax.bar(labels, [v["A"], v["C"], v["D"]], color=[C_INK2, C_BLUE, C_ORANGE], width=0.55)
    ax.errorbar([2], [v["D"]], yerr=[[v["D"] - d_lo], [d_hi - v["D"]]], fmt="none", ecolor=C_INK, capsize=12, lw=2.5)
    ax.text(2.07, d_hi, f"{d_hi:.0f}%", va="center", fontsize=20, color=C_INK)
    ax.text(2.07, d_lo, f"{d_lo:.0f}%", va="center", fontsize=20, color=C_INK)
    for b_, val in zip(bars[:2], (v["A"], v["C"])):
        ax.text(b_.get_x() + b_.get_width() / 2, val + 0.8, "기준" if val == 0 else f"{val:.1f}%", ha="center",
                va="bottom", fontsize=28, fontweight="bold", color=C_INK)
    ax.text(bars[2].get_x() - 0.02, v["D"], f"{v['D']:.0f}%", ha="right", va="center", fontsize=28, fontweight="bold",
            color=C_INK)
    ax.set_ylim(0, d_hi * 1.15)
    ax.set_ylabel("현재 관행 대비 연간 절감률 (%)")
    ax.grid(axis="x", visible=False)
    ax.set_title(f"스케줄링만 {v['C']:.1f}%, DVFS를 더하면 가정에 따라 더 커진다", pad=14)
    fig.text(0.01, 0.012, f"2025년 시뮬레이션, 전력시장 거래량 기준. 세 정책 모두 마감 위반 0건.\n"
             f"D의 세로선: 정적 전력 비율 {s_hi}~{s_lo} 가정 범위(기본 {cfg.STATIC_FRAC}). D는 스케줄링 효과를 포함한 전체 절감률.",
             fontsize=12.5, color=C_INK2)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(DEST / "08_정책별_절감률_ACD.png")
    plt.close(fig)
    return {"A": v["A"], "C": v["C"], "D": v["D"], "D_lo": d_lo, "D_hi": d_hi}


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    plt = setup_matplotlib()
    big(plt)
    name = main_curve()
    print("05", fig_curve_tou(plt, name))
    fig_flow(plt)
    print("06 ok")
    print("07", {k: (round(x, 2) if isinstance(x, float) else x) for k, x in fig_weekend(plt, name).items()})
    print("08", {k: round(x, 2) for k, x in fig_acd(plt, name).items()})


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
