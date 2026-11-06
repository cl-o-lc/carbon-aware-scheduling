"""1단계: 한국 전력의 시간별 탄소집약도 계산, 변동폭 지표, 민감도 분석, 그래프.

시간별 탄소집약도(gCO2eq/kWh) = Σ(연료원별 거래량 × 배출계수) / Σ거래량

시간 표기: 원본 '거래시간' h는 (h-1)시~h시 구간이다(태양광이 13~14 구간에서 최대).
          그래프와 보고서에서는 구간 시작 시각 0~23시로 표기한다. 예) 원본 3 -> '2시'(2~3시).

사용법:  python scripts/02_carbon_intensity.py
산출물:  03_분석/ 아래 CSV, PNG, summary.md, logs/02_carbon_intensity.log
"""
from __future__ import annotations

import json
import logging
import sys

import holidays
import numpy as np
import pandas as pd

from common import (C_AQUA, C_BLUE, C_INK, C_INK2, C_ORANGE, C_YELLOW, COMPARE_YEAR, MAIN_YEAR, OUT,
                    YEAR_COLOR, load_epsis_solar, load_year, setup_matplotlib)
from config_emission_factors import ASSUMED, CLIP_NEGATIVE_TO_ZERO, FACTORS

FIG = OUT / "figures"
LOG = OUT / "logs"
SEASONS = {"봄": (3, 4, 5), "여름": (6, 7, 8), "가을": (9, 10, 11), "겨울": (12, 1, 2)}
SEASON_COLOR = {"봄": C_BLUE, "여름": C_ORANGE, "가을": C_AQUA, "겨울": C_YELLOW}  # 고정 순서
WINDOW = 6  # 배치 작업 이동 단위로 보는 시간 수
log = logging.getLogger("ci")


# ---------------------------------------------------------------- 계산
def prepare(year: int) -> pd.DataFrame:
    df = load_year(year)
    unknown = sorted(set(df["fuel"]) - set(FACTORS))
    if unknown:
        raise SystemExit(f"[중단] 배출계수 매핑에 없는 연료원: {unknown}")
    neg = df["mwh"] < 0
    log.info("%d년 음수 거래량 %d행 (합계 %.2f MWh), 연료원별 %s -> %s",
             year, neg.sum(), df.loc[neg, "mwh"].sum(), df[neg].groupby("fuel").size().to_dict(),
             "0으로 처리" if CLIP_NEGATIVE_TO_ZERO else "그대로 사용")
    if CLIP_NEGATIVE_TO_ZERO:
        df.loc[neg, "mwh"] = 0.0
    tot = df.groupby("fuel")["mwh"].sum()
    log.info("%d년 가정 항목(IPCC 표에 없어 대체값·연간 평균을 쓴 연료원) 거래량 비중: %.2f%%",
             year, tot[tot.index.isin(ASSUMED)].sum() / tot.sum() * 100)
    df["slot"] = df["hour"] - 1  # 구간 시작 시각 0~23
    df["date"] = pd.to_datetime(df["date"])
    return df


def factor_table(df: pd.DataFrame, mult: dict[str, float] | None = None) -> tuple[pd.Series, float]:
    """연료원별 계수 Series와 연간 평균(저장장치·기타 제외) 탄소집약도를 돌려준다.
    mult: 연료원별 배수(민감도 분석용). 연간 평균을 쓰는 항목은 연간 평균 × 배수."""
    mult = mult or {}
    fixed = {k: v[0] * mult.get(k, 1.0) for k, v in FACTORS.items() if v[0] is not None}
    tot = df.groupby("fuel")["mwh"].sum()
    fx = tot[tot.index.isin(fixed)]
    annual_avg = float((fx * fx.index.map(fixed)).sum() / fx.sum())
    f = {k: fixed.get(k, annual_avg * mult.get(k, 1.0)) for k in FACTORS}
    return pd.Series(f), annual_avg


def hourly_ci(df: pd.DataFrame, mult: dict[str, float] | None = None, extra_solar: pd.Series | None = None):
    """(date, slot)별 탄소집약도. extra_solar: (date, slot) 인덱스의 추가 태양광 MWh(비계량 태양광 민감도용)."""
    f, annual_avg = factor_table(df, mult)
    d = df.assign(em=df["mwh"] * df["fuel"].map(f))
    g = d.groupby(["date", "slot"]).agg(em=("em", "sum"), mwh=("mwh", "sum"))
    if extra_solar is not None:
        add = extra_solar.reindex(g.index).fillna(0.0)
        g["em"] += add * f["태양광"]
        g["mwh"] += add
    g["ci"] = g["em"] / g["mwh"]
    return g.reset_index(), annual_avg


def add_calendar(h: pd.DataFrame, year: int) -> pd.DataFrame:
    kr = holidays.KR(years=year)
    h["month"] = h["date"].dt.month
    h["season"] = h["month"].map({m: s for s, ms in SEASONS.items() for m in ms})
    h["holiday"] = h["date"].dt.date.map(lambda x: x in kr)
    h["daytype"] = np.where((h["date"].dt.dayofweek >= 5) | h["holiday"], "주말·공휴일", "평일")
    return h


def curve_metrics(curve: pd.Series) -> dict:
    """24시간 곡선(인덱스 0~23)의 변동폭 지표."""
    c = curve.sort_index().to_numpy()
    srt = np.sort(c)
    clean, dirty = srt[:WINDOW].mean(), srt[-WINDOW:].mean()
    roll = np.array([np.r_[c, c][i:i + WINDOW].mean() for i in range(24)])  # 자정을 넘는 연속 구간 포함
    return {
        "평균": c.mean(), "최소": c.min(), "최대": c.max(),
        "최소시각": int(curve.idxmin()), "최대시각": int(curve.idxmax()),
        "최대/최소": c.max() / c.min(), "최대-최소": c.max() - c.min(),
        "깨끗6h평균": clean, "더러운6h평균": dirty, "더러운6h/깨끗6h": dirty / clean,
        "절감률_더러운6h→깨끗6h": 1 - clean / dirty,
        "절감률_하루평균→깨끗6h": 1 - clean / c.mean(),
        "연속6h_최저평균": roll.min(), "연속6h_최저시작": int(roll.argmin()),
        "연속6h_최고평균": roll.max(), "연속6h_최고시작": int(roll.argmax()),
        "절감률_연속6h": 1 - roll.min() / roll.max(),
    }


def daily_metrics(h: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for d, g in h.groupby("date"):
        s = np.sort(g["ci"].to_numpy())
        rows.append({"date": d, "season": g["season"].iat[0], "daytype": g["daytype"].iat[0],
                     "최대/최소": s[-1] / s[0], "최대-최소": s[-1] - s[0],
                     "절감률_6h": 1 - s[:WINDOW].mean() / s[-WINDOW:].mean()})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- 그래프
def hour_axis(ax):
    ax.set_xlim(-0.5, 23.5)
    ax.set_xticks(range(0, 24, 3))
    ax.set_xticklabels([f"{x}시" for x in range(0, 24, 3)])
    ax.set_xlabel("시각 (구간 시작)")


def fig_daily_curve(plt, H: dict[int, pd.DataFrame]):
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for y in (MAIN_YEAR, COMPARE_YEAR):
        h = H[y]
        q = h.groupby("slot")["ci"].quantile([0.25, 0.75]).unstack()
        m = h.groupby("slot")["ci"].mean()
        if y == MAIN_YEAR:
            ax.fill_between(m.index, q[0.25], q[0.75], color=YEAR_COLOR[y], alpha=0.12, linewidth=0,
                            label=f"{y}년 날짜별 25~75% 범위")
        ax.plot(m.index, m.values, color=YEAR_COLOR[y], marker="o", markersize=4, label=f"{y}년 평균")
        ax.annotate(f"{y}", (23, m.iloc[-1]), xytext=(6, 0), textcoords="offset points",
                    va="center", color=C_INK, fontweight="bold")
    hour_axis(ax)
    ax.set_ylabel("탄소집약도 (gCO2eq/kWh)")
    ax.set_title("하루 24시간 평균 탄소집약도: 2025년과 2023년")
    ax.legend(loc="upper left", fontsize=9)
    fig.savefig(FIG / "fig1_daily_curve_2025_vs_2023.png")
    plt.close(fig)


def label_line_ends(ax, items, gap_frac=0.055):
    """선 끝 직접 라벨이 겹치지 않게 세로 위치를 벌려서 단다. items: [(y, text)]"""
    lo, hi = ax.get_ylim()
    gap = (hi - lo) * gap_frac
    items = sorted(items)
    ys = [y for y, _ in items]
    for i in range(1, len(ys)):
        ys[i] = max(ys[i], ys[i - 1] + gap)
    for (y0, t), y in zip(items, ys):
        ax.annotate(t, (23, y0), xytext=(23.6, y), textcoords="data", va="center", fontsize=9, color=C_INK,
                    annotation_clip=False)


def fig_grouped(plt, H, col, order, colors, title, fname):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
    ends = {}
    for ax, y in zip(axes, (MAIN_YEAR, COMPARE_YEAR)):
        h = H[y]
        ends[y] = []
        for k in order:
            m = h[h[col] == k].groupby("slot")["ci"].mean()
            ax.plot(m.index, m.values, color=colors[k], label=k)
            ends[y].append((m.iloc[-1], k))
        hour_axis(ax)
        ax.set_title(f"{y}년")
    for ax, y in zip(axes, (MAIN_YEAR, COMPARE_YEAR)):
        label_line_ends(ax, ends[y])
    axes[0].set_ylabel("탄소집약도 (gCO2eq/kWh)")
    hs, ls = axes[0].get_legend_handles_labels()
    fig.legend(hs, ls, loc="lower center", ncol=len(order), bbox_to_anchor=(0.5, -0.06), fontsize=10)
    fig.suptitle(title, fontweight="bold", y=1.0)
    fig.tight_layout()
    fig.savefig(FIG / fname)
    plt.close(fig)


def fig_daily_hist(plt, D: dict[int, pd.DataFrame]):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    specs = [("절감률_6h", 100, "절감률 (%)", "(가) 더러운 6시간 → 깨끗한 6시간 절감률", np.arange(0, 36, 2)),
             ("최대-최소", 1, "gCO2eq/kWh", "(나) 하루 최대-최소 차이", np.arange(0, 171, 10))]
    for ax, (col, k, unit, title, bins) in zip(axes, specs):
        for y in (MAIN_YEAR, COMPARE_YEAR):
            v = D[y][col] * k
            ax.hist(v, bins=bins, histtype="step", linewidth=2, color=YEAR_COLOR[y], label=f"{y}년")
            ax.axvline(v.median(), color=YEAR_COLOR[y], linestyle="--", linewidth=1)
        ax.set_title(title, fontsize=11)
        ax.set_xlabel(unit)
        ax.set_ylabel("일수")
        ax.legend(fontsize=9)
    axes[0].axvline(10, color=C_INK2, linewidth=1, linestyle=":")
    axes[0].annotate("10%", (10, axes[0].get_ylim()[1] * 0.95), xytext=(3, 0), textcoords="offset points",
                     fontsize=9, color=C_INK2)
    fig.suptitle("날짜별 하루 안 변동폭 분포 (세로 파선: 연도별 중앙값)", fontweight="bold", y=1.0)
    fig.tight_layout()
    fig.savefig(FIG / "fig4_daily_variation_hist.png")
    plt.close(fig)


def fig_heatmap(plt, h: pd.DataFrame, year: int):
    from matplotlib.colors import LinearSegmentedColormap

    cmap = LinearSegmentedColormap.from_list("blue", ["#cde2fb", "#6da7ec", "#2a78d6", "#184f95", "#0d366b"])
    p = h.groupby(["month", "slot"])["ci"].mean().unstack()
    fig, ax = plt.subplots(figsize=(9, 4.2))
    im = ax.imshow(p.values, aspect="auto", cmap=cmap, origin="upper")
    ax.set_yticks(range(12))
    ax.set_yticklabels([f"{m}월" for m in p.index])
    ax.set_xticks(range(0, 24, 3))
    ax.set_xticklabels([f"{x}시" for x in range(0, 24, 3)])
    ax.set_xlabel("시각 (구간 시작)")
    ax.grid(False)
    cb = fig.colorbar(im, ax=ax)
    cb.set_label("gCO2eq/kWh")
    ax.set_title(f"{year}년 월 x 시각별 평균 탄소집약도 (진할수록 탄소가 많음)")
    fig.savefig(FIG / f"fig5_heatmap_month_hour_{year}.png")
    plt.close(fig)


def fig_sensitivity(plt, base: pd.Series, lo: pd.Series, hi: pd.Series, solar: dict[str, pd.Series]):
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.fill_between(base.index, np.minimum(lo, hi), np.maximum(lo, hi), color=C_BLUE, alpha=0.18, linewidth=0,
                    label="가정 항목 계수 -50% ~ +50%")
    ax.plot(base.index, base.values, color=C_BLUE, label="기준")
    for (name, s), color in zip(solar.items(), (C_ORANGE, C_AQUA)):
        ax.plot(s.index, s.values, color=color, linestyle="--", label=name)
    hour_axis(ax)
    ax.set_ylabel("탄소집약도 (gCO2eq/kWh)")
    ax.set_title(f"{MAIN_YEAR}년 24시간 곡선 민감도")
    ax.legend(fontsize=9, loc="upper left")
    fig.savefig(FIG / "fig6_sensitivity.png")
    plt.close(fig)


# ---------------------------------------------------------------- 민감도
def sensitivity(df: pd.DataFrame, base_curve: pd.Series):
    def run(mult):
        h, _ = hourly_ci(df, mult)
        return h.groupby("slot")["ci"].mean()

    rows, curves = [], {}
    cases = [("가정 항목 전체 -50%", {k: 0.5 for k in ASSUMED}), ("가정 항목 전체 +50%", {k: 1.5 for k in ASSUMED})]
    present = set(df["fuel"])
    cases += [(f"{k} {s}", {k: m}) for k in ASSUMED if k in present for s, m in (("-50%", 0.5), ("+50%", 1.5))]
    bm = curve_metrics(base_curve)
    bshape = base_curve / base_curve.mean()
    for name, mult in [("기준", {})] + cases:
        c = base_curve if not mult else run(mult)
        curves[name] = c
        m = curve_metrics(c)
        shape = c / c.mean()
        rows.append({
            "케이스": name, "연평균": m["평균"], "최대/최소": m["최대/최소"], "더러운6h/깨끗6h": m["더러운6h/깨끗6h"],
            "절감률_6h(%)": m["절감률_더러운6h→깨끗6h"] * 100,
            "절감률_6h 변화(%p)": (m["절감률_더러운6h→깨끗6h"] - bm["절감률_더러운6h→깨끗6h"]) * 100,
            "곡선모양 상관계수": float(np.corrcoef(c, base_curve)[0, 1]),
            "정규화곡선 최대차이(%)": float((shape - bshape).abs().max() * 100),
            "최소시각": m["최소시각"], "최대시각": m["최대시각"],
        })
    return pd.DataFrame(rows), curves


# ---------------------------------------------------------------- 실행
def main():
    for d in (OUT, FIG, LOG):
        d.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(message)s",
                        handlers=[logging.FileHandler(LOG / "02_carbon_intensity.log", "w", encoding="utf-8"),
                                  logging.StreamHandler(sys.stdout)])
    plt = setup_matplotlib()

    DF, H, D, curves, metrics = {}, {}, {}, {}, {}
    for y in (MAIN_YEAR, COMPARE_YEAR):
        DF[y] = prepare(y)
        h, annual_avg = hourly_ci(DF[y])
        log.info("%d년 저장장치·기타에 적용한 연간 평균 탄소집약도: %.2f gCO2eq/kWh", y, annual_avg)
        H[y] = add_calendar(h, y)
        tot = H[y]
        log.info("%d년 거래량 가중 연평균 탄소집약도: %.2f gCO2eq/kWh", y, tot["em"].sum() / tot["mwh"].sum())
        H[y].assign(시각=H[y]["slot"]).to_csv(OUT / f"ci_hourly_{y}.csv", index=False, encoding="utf-8-sig",
                                             float_format="%.4f")
        D[y] = daily_metrics(H[y])
        curves[y] = {"연간": H[y].groupby("slot")["ci"].mean()}
        for s in SEASONS:
            curves[y][s] = H[y][H[y]["season"] == s].groupby("slot")["ci"].mean()
        for t in ("평일", "주말·공휴일"):
            curves[y][t] = H[y][H[y]["daytype"] == t].groupby("slot")["ci"].mean()
        metrics[y] = {k: curve_metrics(c) for k, c in curves[y].items()}
        wd, we = np.sort(curves[y]["평일"].to_numpy()), np.sort(curves[y]["주말·공휴일"].to_numpy())
        metrics[y]["평일→주말"] = {
            "평일 더러운6h평균": wd[-WINDOW:].mean(), "주말·공휴일 깨끗6h평균": we[:WINDOW].mean(),
            "절감률_평일더러운6h→주말깨끗6h": 1 - we[:WINDOW].mean() / wd[-WINDOW:].mean(),
            "절감률_평일평균→주말깨끗6h": 1 - we[:WINDOW].mean() / wd.mean(),
        }
        sol = DF[y][DF[y]["fuel"] == "태양광"].groupby("slot")["mwh"].sum()
        log.info("%d년 태양광 거래량 중 19~24시 구간(시작 19~23시) 비중: %.2f%% (일몰 후 방전하는 태양광 연계 저장장치 영향 추정)",
                 y, sol.loc[19:23].sum() / sol.sum() * 100)

    # 곡선 표 저장
    tab = pd.concat({f"{y}_{k}": c for y in curves for k, c in curves[y].items()}, axis=1)
    tab.index.name = "시각"
    tab.to_csv(OUT / "ci_curves_24h.csv", encoding="utf-8-sig", float_format="%.2f")
    mt = pd.DataFrame({f"{y}_{k}": v for y in metrics for k, v in metrics[y].items() if k != "평일→주말"}).T
    mt.to_csv(OUT / "ci_curve_metrics.csv", encoding="utf-8-sig", float_format="%.4f")

    # 날짜별 분포 요약
    dsum = {}
    for y in D:
        d = D[y]
        dsum[y] = {
            "일수": len(d),
            "최대/최소 중앙값": d["최대/최소"].median(), "최대/최소 25%": d["최대/최소"].quantile(.25),
            "최대/최소 75%": d["최대/최소"].quantile(.75),
            "최대-최소 중앙값": d["최대-최소"].median(),
            "절감률_6h 중앙값(%)": d["절감률_6h"].median() * 100,
            "절감률_6h 25%(%)": d["절감률_6h"].quantile(.25) * 100,
            "절감률_6h 75%(%)": d["절감률_6h"].quantile(.75) * 100,
            "절감률_6h 10% 이상 일수 비율(%)": (d["절감률_6h"] >= 0.10).mean() * 100,
            "계절별 절감률_6h 중앙값(%)": (d.groupby("season")["절감률_6h"].median() * 100).round(2).to_dict(),
            "요일유형별 절감률_6h 중앙값(%)": (d.groupby("daytype")["절감률_6h"].median() * 100).round(2).to_dict(),
        }
        d.to_csv(OUT / f"ci_daily_variation_{y}.csv", index=False, encoding="utf-8-sig", float_format="%.4f")

    # 상위 5개 시각
    top = {}
    for y in curves:
        c = curves[y]["연간"]
        hh = H[y].sort_values("ci")
        top[y] = {
            "깨끗한 시각(연평균 곡선)": [(int(i), round(v, 1)) for i, v in c.nsmallest(5).items()],
            "더러운 시각(연평균 곡선)": [(int(i), round(v, 1)) for i, v in c.nlargest(5).items()],
            "가장 깨끗한 개별 시간": [(r.date.strftime("%Y-%m-%d"), int(r.slot), round(r.ci, 1)) for r in hh.head(5).itertuples()],
            "가장 더러운 개별 시간": [(r.date.strftime("%Y-%m-%d"), int(r.slot), round(r.ci, 1)) for r in hh.tail(5)[::-1].itertuples()],
        }

    # 민감도
    sens, sens_curves = sensitivity(DF[MAIN_YEAR], curves[MAIN_YEAR]["연간"])
    sens.to_csv(OUT / "sensitivity_assumed_factors.csv", index=False, encoding="utf-8-sig", float_format="%.4f")

    # 그래프
    fig_daily_curve(plt, H)
    fig_grouped(plt, H, "season", list(SEASONS), SEASON_COLOR, "계절별 24시간 평균 탄소집약도", "fig2_seasonal_curves.png")
    fig_grouped(plt, H, "daytype", ["평일", "주말·공휴일"], {"평일": C_BLUE, "주말·공휴일": C_ORANGE},
                "평일과 주말·공휴일의 24시간 평균 탄소집약도", "fig3_weekday_weekend.png")
    fig_daily_hist(plt, D)
    for y in (MAIN_YEAR, COMPARE_YEAR):
        fig_heatmap(plt, H[y], y)
    fig_sensitivity(plt, curves[MAIN_YEAR]["연간"], sens_curves["가정 항목 전체 -50%"],
                    sens_curves["가정 항목 전체 +50%"], solar_cases(DF[MAIN_YEAR]))

    solar = solar_sensitivity(DF, {y: metrics[y] for y in metrics}, dsum)
    (OUT / "solar_sensitivity.json").write_text(json.dumps(solar, ensure_ascii=False, indent=1, default=float),
                                                encoding="utf-8")

    result = {"metrics": metrics, "daily": dsum, "top": top}
    (OUT / "ci_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=1, default=float),
                                         encoding="utf-8")
    log.info("완료: %s", OUT)


SOLAR_CASE = "비계량 태양광 포함(EPSIS 월별 비율로 확대)"


def solar_extra(df: pd.DataFrame, year: int) -> tuple[pd.Series, pd.DataFrame]:
    """전력시장 밖 태양광(한전PPA + 자가용 추계)을 시간별로 추정한다.
    가정: 시장 밖 태양광의 시간별 모양은 전력시장 태양광과 같다. 월별 확대 배수 = EPSIS (시장+PPA+자가용)/시장."""
    ep = load_epsis_solar()
    ep = ep[ep["year"] == year].set_index("month")
    if len(ep) != 12:
        raise SystemExit(f"[중단] EPSIS {year}년 월별 자료가 12개월이 아님: {len(ep)}")
    sol = df[df["fuel"] == "태양광"].set_index(["date", "slot"])["mwh"]
    k = sol.index.get_level_values("date").month.map(ep["factor"]).to_numpy()
    return sol * (k - 1), ep


def solar_cases(df: pd.DataFrame) -> dict[str, pd.Series]:
    """fig6에 겹쳐 그릴 비계량 태양광 케이스 곡선(주 분석 연도)."""
    extra, _ = solar_extra(df, MAIN_YEAR)
    h, _ = hourly_ci(df, extra_solar=extra)
    return {SOLAR_CASE: h.groupby("slot")["ci"].mean()}


def solar_sensitivity(DF: dict[int, pd.DataFrame], metrics: dict, dsum: dict) -> dict:
    out = {"lines": []}
    L = out["lines"]
    L.append("근거 자료: 한국전력거래소 EPSIS 전력수급 > 추계정보, 태양광 발전량 월별 '전력시장 참여(실적)', "
             "'한전PPA(실적)', '자가용태양광(추계)' (https://epsis.kpx.or.kr/epsisnew/selectEkgeEpsEstGrid.do?menuId=030400). "
             "자가용은 전력거래소 추정치다.")
    L.append("")
    L.append("방법(가정): 전력시장 밖 태양광의 시간별 모양이 시장 태양광과 같다고 보고, 시장 태양광 거래량에 "
             "월별 (시장+PPA+자가용)/시장 배수를 곱해 늘린 만큼을 공급에 더한다. 배출계수는 태양광 48을 쓴다.")
    L.append("")
    L.append("| 연도 | EPSIS 시장 (MWh) | 한전PPA (MWh) | 자가용 추계 (MWh) | 합계/시장 배수 | 월별 배수 범위 |")
    L.append("|---|---|---|---|---|---|")
    for y in (MAIN_YEAR, COMPARE_YEAR):
        _, ep = solar_extra(DF[y], y)
        L.append(f"| {y} | {ep['market'].sum():,.0f} | {ep['ppa'].sum():,.0f} | {ep['btm'].sum():,.0f} | "
                 f"{ep['total'].sum() / ep['market'].sum():.3f} | {ep['factor'].min():.2f}~{ep['factor'].max():.2f} |")
    L.append("")
    L.append("| 연도 | 케이스 | 연평균 | 최대/최소 | 더러운6h/깨끗6h | 6h 절감률 | 날짜별 6h 절감률 중앙값 | 10% 이상 일수 비율 | 봄 6h 절감률 | 주말·공휴일 6h 절감률 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for y in (MAIN_YEAR, COMPARE_YEAR):
        extra, _ = solar_extra(DF[y], y)
        h, _ = hourly_ci(DF[y], extra_solar=extra)
        h = add_calendar(h, y)
        h.to_csv(OUT / f"ci_hourly_{y}_with_nonmarket_solar.csv", index=False, encoding="utf-8-sig", float_format="%.4f")
        d = daily_metrics(h)
        cm = {k: curve_metrics(h[sel].groupby("slot")["ci"].mean()) for k, sel in
              [("연간", slice(None)), ("봄", h["season"] == "봄"), ("주말·공휴일", h["daytype"] == "주말·공휴일")]}
        for name, m, med, share in [
            ("기준(시장 거래량만)", metrics[y], dsum[y]["절감률_6h 중앙값(%)"] / 100, dsum[y]["절감률_6h 10% 이상 일수 비율(%)"] / 100),
            (SOLAR_CASE, cm, d["절감률_6h"].median(), (d["절감률_6h"] >= 0.10).mean())]:
            a = m["연간"]
            L.append(f"| {y} | {name} | {a['평균']:.1f} | {a['최대/최소']:.3f} | {a['더러운6h/깨끗6h']:.3f} | "
                     f"{a['절감률_더러운6h→깨끗6h'] * 100:.1f}% | {med * 100:.1f}% | {share * 100:.1f}% | "
                     f"{m['봄']['절감률_더러운6h→깨끗6h'] * 100:.1f}% | {m['주말·공휴일']['절감률_더러운6h→깨끗6h'] * 100:.1f}% |")
        out[str(y)] = {k: v for k, v in cm.items()}
        out[str(y)]["daily_median"] = float(d["절감률_6h"].median())
    L.append("")
    L.append("주의: 시장 태양광에는 해가 진 뒤 방전하는 태양광 연계 저장장치 물량이 섞여 있어(처리 로그 참고), "
             "같은 배수로 늘리면 저녁 시간 태양광도 함께 늘어난다. 한전PPA·자가용 태양광의 실제 시간별 모양은 "
             "확인하지 않았다(아래 5분 단위 자료로 확인 가능).")
    L.append("")
    L.append("참고: 전력거래소 홈페이지 '실시간 전력수급현황'(https://www.kpx.or.kr/powerSource.es?mid=a10606030000)에 "
             "5분 단위 '태양광(PPA,추정)', '태양광(BTM,추정)'이 2024-11-23부터 공개되어 있다(한 번에 최대 31일 엑셀 다운로드). "
             "2025년은 이것으로 시간별 모양까지 반영할 수 있으나 이번에는 쓰지 않았다.")
    return out


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
