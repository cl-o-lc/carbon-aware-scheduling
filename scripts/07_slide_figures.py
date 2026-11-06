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
from common import CURVES, OUT, ROOT, main_curve, setup_matplotlib, weekend_compare

DEST = ROOT / "04_발표자료" / "figures"
W, H = 10.667, 6.0  # 16:9 (인치). 슬라이드에 폭 8.2인치로 넣으므로 글자가 너무 작아지지 않게 작게 잡음

# 발표 자료 색: 잉크 2단계 + SDG 공식 색(13 초록 = 주 강조, 7 노랑·9 주황 = 보조 강조)
C_INK, C_INK2 = "#1F2D2A", "#5F6B66"
SDG13, SDG7, SDG9 = "#3F7E44", "#FCC30B", "#FD6925"
C_BLUE, C_AQUA, C_ORANGE = SDG13, SDG13, SDG9  # 아래 함수들이 쓰던 이름을 발표 색으로 연결
LIGHT_GREEN, LIGHT_GRAY = "#E6F0E7", "#F0F2F1"

# 2026년 개편 후 봄·가을 평일 요금 시간대 (references.md 5-2, 5-3). (시작, 끝, 이름)
TOU_SPRING_FALL_WEEKDAY = [(0, 8, "경부하"), (8, 15, "중간부하"), (15, 21, "최대부하"), (21, 22, "중간부하"), (22, 24, "경부하")]
TOU_COLOR = {"경부하": "#F0F2F1", "중간부하": "#FEEDB5", "최대부하": "#FFC9AF"}  # 요금이 비쌀수록 진하게


def big(plt):
    plt.rcParams.update({"savefig.bbox": "standard", "savefig.dpi": 200, "font.size": 18, "axes.titlesize": 24, "axes.labelsize": 19, "xtick.labelsize": 16,
                         "ytick.labelsize": 16, "legend.fontsize": 16, "font.family": "Pretendard",
                         "axes.edgecolor": C_INK2, "axes.labelcolor": C_INK, "xtick.color": C_INK2, "ytick.color": C_INK2,
                         "text.color": C_INK})


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
    ax.scatter([night], [c[night]], s=260, color=SDG9, zorder=4, edgecolor="white", linewidth=2)
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
    ax.set_ylim(0, 62)
    ax.axis("off")

    def box(x, y, w, h, text, fc, bold=False, size=16):
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.6,rounding_size=1.5",
                                    fc=fc, ec=C_INK2, lw=1.8))
        ax.text(x, y, text, ha="center", va="center", fontsize=size, color=C_INK, fontweight="bold" if bold else None,
                linespacing=1.35)

    def arrow(p, q, label=None, lx=0, ly=0):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=24, lw=2.2, color=C_INK2))
        if label:
            ax.text((p[0] + q[0]) / 2 + lx, (p[1] + q[1]) / 2 + ly, label, fontsize=16, color=C_INK, ha="center",
                    va="center", fontweight="bold")

    box(50, 57, 46, 6.5, "15분마다: 대기 중인 작업 확인", LIGHT_GREEN, bold=True, size=17)
    box(52, 43, 74, 11, "① 마감 가능성 검사\n지금 아무것도 안 돌려도 마감 빠른 순으로 모두 끝낼 수 있나?", "#ffffff")
    box(13, 24, 24, 11, "마감이 급한 작업부터\n즉시 실행", "#FFE1D3", bold=True)
    box(60, 24, 50, 15, "② 탄소 기준 (에이징 반영)\n지금이 남은 시간 중 충분히 깨끗한가?\n오래 기다릴수록 기준이 넓어진다", "#ffffff")
    box(43, 5.5, 26, 6.5, "빈 슬롯에서 실행", LIGHT_GREEN, bold=True)
    box(78, 5.5, 28, 6.5, "다음 15분까지 대기", LIGHT_GRAY, bold=True)
    arrow((50, 53.4), (50, 49.2))
    arrow((24, 37.1), (16, 30.2), "아니오", lx=-5, ly=0.5)
    arrow((60, 37.1), (60, 32.2), "예", lx=3)
    arrow((50, 16.2), (45, 9.4), "예", lx=-3)
    arrow((72, 16.2), (76, 9.4), "아니오", lx=5)
    # 다음 15분에 다시 확인: 오른쪽 가장자리를 따라 위로 돌아가는 점선
    ax.plot([92.6, 97.5, 97.5], [5.5, 5.5, 57], color=C_INK2, lw=1.8, linestyle="--")
    ax.add_patch(FancyArrowPatch((97.5, 57), (73.6, 57), arrowstyle="-|>", mutation_scale=22, lw=1.8,
                                 color=C_INK2, linestyle="--"))
    ax.text(1, 12.5, "위반 0건은 ① 덕분\n에이징은 ② 기준만 조절", fontsize=14, color=C_INK2, va="top", linespacing=1.4)
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
    fig.text(0.01, 0.012, f"2025년 시뮬레이션, 전력시장 거래량 기준. 세 정책 모두 마감 위반 0건.\n"
             f"D의 세로선: 정적 전력 비율 {s_hi}~{s_lo} 가정 범위(기본 {cfg.STATIC_FRAC}). D는 스케줄링 효과를 포함한 전체 절감률.",
             fontsize=12.5, color=C_INK2)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(DEST / "08_정책별_절감률_ACD.png")
    plt.close(fig)
    return {"A": v["A"], "C": v["C"], "D": v["D"], "D_lo": d_lo, "D_hi": d_hi}


def fig_curve_heatmap(plt, name: str):
    """슬라이드 3: 왼쪽 2025 vs 2023 하루 평균 곡선, 오른쪽 2025년 월 x 시각 히트맵(한 장의 16:9 그림)."""
    from matplotlib.colors import LinearSegmentedColormap

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(W, H), gridspec_kw={"width_ratios": [1.05, 1]})
    for y, col in ((2025, SDG13), (2023, SDG9)):
        f = OUT / CURVES[name][1] if y == 2025 else OUT / "ci_hourly_2023.csv"
        c = pd.read_csv(f).groupby("slot")["ci"].mean()
        a1.plot(c.index, c.values, color=col, lw=3.5, marker="o", ms=5)
        a1.annotate(f"{y}년", (23, c.iloc[-1]), xytext=(8, 0), textcoords="offset points", va="center",
                    fontsize=18, fontweight="bold", color=col, annotation_clip=False)
    a1.set_xlim(-0.5, 23.5)
    a1.set_xticks(range(0, 24, 6))
    a1.set_xticklabels([f"{x}시" for x in range(0, 24, 6)])
    a1.set_ylabel("탄소집약도 (gCO2eq/kWh)")
    a1.set_title("하루 24시간 평균", fontsize=20, pad=10)
    a1.grid(axis="x", visible=False)
    h = pd.read_csv(OUT / CURVES[name][1], parse_dates=["date"])
    h["month"] = h["date"].dt.month
    p = h.groupby(["month", "slot"])["ci"].mean().unstack()
    cmap = LinearSegmentedColormap.from_list("g", ["#FFFFFF", "#CFE3D0", "#7FB283", SDG13, "#1E4523"])
    im = a2.imshow(p.values, aspect="auto", cmap=cmap)
    a2.set_yticks(range(0, 12, 2))
    a2.set_yticklabels([f"{m}월" for m in range(1, 13, 2)])
    a2.set_xticks(range(0, 24, 6))
    a2.set_xticklabels([f"{x}시" for x in range(0, 24, 6)])
    a2.grid(False)
    a2.set_title("2025년 월 × 시각 (진할수록 탄소 많음)", fontsize=20, pad=10)
    cb = fig.colorbar(im, ax=a2, fraction=0.05)
    cb.ax.tick_params(labelsize=14)
    fig.text(0.01, 0.012, "전력거래소 연료원별 시간대별 전력거래량 × IPCC 생애주기 배출계수. 시각은 구간 시작(12시 = 12~13시).",
             fontsize=12.5, color=C_INK2)
    fig.tight_layout(rect=(0, 0.05, 0.97, 1))
    fig.savefig(DEST / "09_슬라이드3_탄소곡선_히트맵.png")
    plt.close(fig)


def fig_gantt_ac(plt, name: str):
    """슬라이드 7: 봄 맑은 평일 A vs C 실행 시간표(16:9, 큰 글씨)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("sim", ROOT / "scripts" / "04_simulate.py")
    sim = importlib.util.module_from_spec(spec)
    sys.modules["sim"] = sim
    spec.loader.exec_module(sim)
    jobs = sim.make_jobs()
    cv = sim.Curve(name)
    rep = pd.read_csv(OUT / "stage2" / "representative_days.csv")
    d = pd.Timestamp(rep[(rep["곡선"] == name) & (rep["대표일"] == "봄 맑은 평일")]["날짜"].iloc[0])
    di = list(cv.dates).index(d)
    act = cv.window(di, sim.horizon_end(jobs))
    runs = {p: sim.simulate(jobs, act, act, p) for p in ("A", "C")}
    colors = {"당일": SDG13, "익일": SDG9, "주간": SDG7}
    x_max = 40.0
    fig, axes = plt.subplots(3, 1, figsize=(W, H), sharex=True, gridspec_kw={"height_ratios": [1.2, 1, 1]})
    t = cfg.T0_H + np.arange(len(act)) * cfg.STEP_H
    m = t <= x_max
    axes[0].step(t[m], act[m], where="post", color=C_INK, lw=2.5)
    axes[0].set_ylabel("g/kWh", fontsize=16)
    axes[0].set_title(f"{d:%Y-%m-%d}({'월화수목금토일'[d.dayofweek]}) 봄 맑은 평일의 탄소집약도와 실행 시간표", fontsize=19, pad=8)
    base = runs["A"]["emis_g"].sum()
    for ax, (p, lab) in zip(axes[1:], (("A", "A 현재 관행 (새벽 2시 일괄)"), ("C", "C 탄소 인지 스케줄링"))):
        r = runs[p]
        for row in r.itertuples():
            if row.start_h >= x_max:
                continue
            ax.barh(row.slot, min(row.end_h, x_max) - row.start_h, left=row.start_h, height=0.7,
                    color=colors[row.cls], edgecolor="white", lw=1.2)
        ax.set_yticks(range(cfg.SLOTS))
        ax.set_yticklabels([f"슬롯{i + 1}" for i in range(cfg.SLOTS)], fontsize=15)
        ax.set_ylim(-0.6, cfg.SLOTS - 0.4)
        ax.grid(axis="y", visible=False)
        tot = r["emis_g"].sum()
        note = "" if p == "A" else f"  →  이날 {(1 - tot / base) * 100:.1f}% 절감, 마감 위반 {int(r['late'].sum())}건"
        out = r[r["start_h"] >= x_max]
        if len(out):
            on_weekend = all(sim.day_kind((d + pd.Timedelta(hours=h)).normalize()) == "주말·공휴일" for h in out["start_h"])
            note += f", 주간 작업 {len(out)}개는 {'주말에' if on_weekend else '40시간 이후에'} 실행(그림 밖)"
        ax.set_title(lab + note, fontsize=17, loc="left", pad=6)
    xt = np.arange(-4, x_max + 1, 4)
    axes[-1].set_xticks(xt)
    axes[-1].set_xticklabels([("전날 " if v < 0 else ("다음날 " if v == 24 else "")) + f"{int(v % 24)}시" for v in xt], fontsize=14)
    for ax in axes:
        ax.axvline(24, color=C_INK2, lw=1, ls=":")  # 날짜가 바뀌는 지점
    axes[-1].set_xlim(cfg.T0_H, x_max)
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=c, label=f"{k} 마감 작업") for k, c in colors.items()], loc="lower center",
               ncol=3, fontsize=15, frameon=False, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(DEST / "10_슬라이드7_간트_A_vs_C.png")
    plt.close(fig)


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    plt = setup_matplotlib()
    big(plt)
    name = main_curve()
    fig_curve_heatmap(plt, name)
    fig_gantt_ac(plt, name)
    print("09, 10 ok")
    print("05", fig_curve_tou(plt, name))
    fig_flow(plt)
    print("06 ok")
    print("07", {k: (round(x, 2) if isinstance(x, float) else x) for k, x in fig_weekend(plt, name).items()})
    print("08", {k: round(x, 2) for k, x in fig_acd(plt, name).items()})


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
