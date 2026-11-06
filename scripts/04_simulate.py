"""2단계: 탄소 인지 작업 스케줄링 시뮬레이션.

입력 곡선(시간별 탄소집약도)만 바꾸면 같은 실험을 다시 돌린다.
  python scripts/04_simulate.py              # 주 곡선(main_curve) + 나머지 있는 곡선 모두
  python scripts/04_simulate.py market       # 지정 곡선만

실험 단위: '하루치 작업 세트'(30개). 같은 작업 세트가 매일 들어온다고 보고, 2025년 각 날짜를
독립 실험으로 돌린다. 작업은 전날 20시~당일 2시에 도착하고 마감은 당일/익일/7일 뒤 8~14시.

정책
  A   현재 관행: 모든 작업을 새벽 2시에 일괄 시작(2개 슬롯, 마감 빠른 순 대기열)
  A'  도착 즉시 실행(참고)
  B   탄소 인지 탐욕: 남은 마감 구간에서 배출이 가장 적은 시작 시각이 '지금'일 때만 시작(도착 순)
  C   B + 에이징 + 마감 보호: 오래 기다릴수록 허용 기준을 넓히고(에이징), 마감 여유가 적은 작업부터 실행.
      매 단계 EDF 가능성 검사로 마감이 위태로운 작업은 탄소와 상관없이 먼저 시작
  D   C + DVFS: 시작할 때 주파수 {1.0, 0.8, 0.6} 중 마감 안에서 배출(에너지 × 탄소)이 가장 적은 것 선택
  E   C와 같되 탄소 곡선을 '전주 같은 요일 같은 시각' 값으로 예측해서 결정, 배출은 실제 곡선으로 계산
  C7  C와 같되 주간 작업도 익일 마감까지만 미룰 수 있게 제한(주말 이동 효과 분리용)
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, asdict

import holidays
import numpy as np
import pandas as pd

import config_simulation as cfg
from common import (C_AQUA, C_BLUE, C_GRID, C_INK, C_INK2, C_ORANGE, C_YELLOW, CURVES, OUT, available_curves,
                    load_curve, main_curve, setup_matplotlib)

S2 = OUT / "stage2"
FIG = S2 / "figures"
CLS_COLOR = {"당일": C_BLUE, "익일": C_ORANGE, "주간": C_AQUA}
POLICIES = ["A", "A'", "B", "C", "D", "E", "C7"]
POLICY_NAME = {"A": "A 현재 관행(새벽 2시 고정)", "A'": "A' 도착 즉시", "B": "B 탄소 인지 탐욕",
               "C": "C B+에이징+마감 검사", "D": "D C+DVFS", "E": "E C+전주 예측 곡선", "C7": "C7 C(주간 작업 익일까지만)"}
K_STEPS_PER_H = int(round(1 / cfg.STEP_H))
KR_HOL = holidays.KR(years=[2025, 2026])


# ---------------------------------------------------------------- 작업 세트
@dataclass
class Job:
    id: int
    name: str
    cls: str
    arrival: float   # 시각(h), 당일 0시 기준. 음수는 전날
    runtime: float   # f=1.0 기준 실행 시간(h)
    deadline: float  # 시각(h), 당일 0시 기준
    power_w: float
    mem: float       # 메모리 바운드 비율


def make_jobs(seed: int = cfg.SEED) -> list[Job]:
    rng = np.random.default_rng(seed)
    q = lambda x: round(x / cfg.STEP_H) * cfg.STEP_H
    jobs = []
    for name, cls, n, rt, pw, mem in cfg.JOB_TEMPLATES:
        for i in range(n):
            arrival = q(rng.uniform(*cfg.ARRIVAL_RANGE_H))
            runtime = q(rng.uniform(*rt))
            dl = cfg.DEADLINE_DAY_OFFSET[cls] * 24 + cfg.FIXED_START_H + rng.integers(cfg.DEADLINE_WINDOW_H[0],
                                                                                     cfg.DEADLINE_WINDOW_H[1] + 1)
            jobs.append(Job(len(jobs) + 1, name + (f" {i + 1}" if n > 1 else ""), cls, arrival, runtime, float(dl),
                            float(round(rng.uniform(*pw), -1)), round(float(rng.uniform(*mem)), 2)))
    return jobs


def run_time(job: Job, f: float) -> float:
    return job.runtime * (job.mem + (1 - job.mem) / f)


def power_kw(job: Job, f: float, static_frac: float) -> float:
    return job.power_w / 1000 * (static_frac + (1 - static_frac) * f ** 3)


# ---------------------------------------------------------------- 시뮬레이션 엔진
def step_index(t: float) -> int:
    return int(round((t - cfg.T0_H) / cfg.STEP_H))


def simulate(jobs: list[Job], ci_act: np.ndarray, ci_dec: np.ndarray, policy: str,
             static_frac: float = cfg.STATIC_FRAC, deadline_cap: float | None = None,
             gamma: float | None = None) -> pd.DataFrame:
    """ci_act / ci_dec: 실험 구간의 15분 단위 탄소집약도(실제 / 결정용). 반환: 작업별 결과."""
    N = len(ci_act)
    cum_act = np.concatenate([[0.0], np.cumsum(ci_act)])
    cum_dec = np.concatenate([[0.0], np.cumsum(ci_dec)])
    freqs = cfg.FREQS if policy == "D" else (1.0,)

    st = []  # 작업별 사전 계산
    for j in jobs:
        dl = j.deadline if (deadline_cap is None or j.cls != "주간") else min(j.deadline, deadline_cap)
        D = step_index(dl)
        a = step_index(j.arrival)
        opts = []
        for f in freqs:
            T = run_time(j, f)
            n = int(math.ceil(T / cfg.STEP_H - 1e-9))
            pk = power_kw(j, f, static_frac)
            s = np.arange(N)
            ok = s + n <= N
            e = np.full(N, np.inf)
            e[ok] = pk * T * (cum_dec[s[ok] + n] - cum_dec[s[ok]]) / n  # 배출(g) = 에너지 × 구간 평균 탄소
            opts.append((f, T, n, pk, e))
        n1 = opts[0][2]
        L = D - n1  # f=1.0 기준 최종 시작 가능 단계
        cost = opts[0][4].copy()
        best_f = np.zeros(N, dtype=int)
        for k, (f, T, n, pk, e) in enumerate(opts[1:], start=1):
            feas = np.arange(N) + n <= D
            better = feas & (e < cost)
            cost[better] = e[better]
            best_f[better] = k
        st.append(dict(job=j, D=D, a=a, L=L, cost=cost, best_f=best_f, opts=opts, deadline=dl))

    release = step_index(cfg.FIXED_START_H)
    slot_free_at = [0] * cfg.SLOTS
    waiting = set(range(len(jobs)))
    edf_order = sorted(range(len(jobs)), key=lambda i: (st[i]["D"], st[i]["a"], i))
    guarded = policy in ("C", "D")
    gamma = cfg.AGING_GAMMA if gamma is None else gamma
    res = {}

    def start(idx: int, k: int, fi: int) -> None:
        x = st[idx]
        f, T, n, pk, _ = x["opts"][fi]
        n = min(n, N - k)
        slot = min((i for i in range(cfg.SLOTS) if slot_free_at[i] <= k), key=lambda i: i)
        ci_mean = (cum_act[k + n] - cum_act[k]) / n
        res[idx] = dict(id=x["job"].id, slot=slot, start_step=k, f=f, n=n, T=T,
                        energy_kwh=pk * T, emis_g=pk * T * ci_mean,
                        start_h=cfg.T0_H + k * cfg.STEP_H, end_h=cfg.T0_H + (k + n) * cfg.STEP_H,
                        deadline_h=x["deadline"])
        slot_free_at[slot] = k + n
        waiting.discard(idx)

    def feasible_after(k: int, extra: list[tuple[int, int]]) -> bool:
        """마감 보호 검사: extra[(작업, 점유 단계 수)]를 지금 시작한다고 할 때, 나머지 대기 작업을 k+1부터
        마감 빠른 순(EDF)으로 가장 먼저 비는 슬롯에 넣으면 모두 마감 안에 끝나는가(f=1 기준, 보수적)."""
        frees = sorted(slot_free_at)
        busy = [max(fa, k) for fa in frees]
        busy.sort()
        for _, n in extra:
            busy[0] = k + n
            busy.sort()
        busy = [max(b, k + 1) for b in busy]
        skip = {i for i, _ in extra}
        for i in edf_order:
            if i not in waiting or i in skip:
                continue
            x = st[i]
            s = max(busy[0], x["a"])
            if s + x["opts"][0][2] > x["D"]:
                return False
            busy[0] = s + x["opts"][0][2]
            busy.sort()
        return True

    for k in range(N):
        n_free = sum(1 for i in range(cfg.SLOTS) if slot_free_at[i] <= k)
        if not waiting:
            break
        if n_free == 0:
            continue
        arrived = [i for i in waiting if st[i]["a"] <= k]
        if not arrived:
            continue
        if policy == "A":
            for i in sorted((i for i in arrived if k >= release), key=lambda i: (st[i]["D"], st[i]["a"], i))[:n_free]:
                start(i, k, 0)
            continue
        if policy == "A'":
            for i in sorted(arrived, key=lambda i: (st[i]["D"], st[i]["a"], i))[:n_free]:
                start(i, k, 0)
            continue

        # 탄소 기준으로 '지금 시작해도 좋은' 작업 고르기
        cand = []
        for i in arrived:
            x = st[i]
            if k > x["L"]:  # 이미 늦음: 바로 실행
                cand.append(((-1, x["L"] - k, i), i))
                continue
            cmin, cmax = sufmin_of(x, k)
            if policy == "B":
                if x["cost"][k] <= cmin + 1e-9:
                    cand.append(((x["a"], i), i))
            else:  # C, D, E, C7: 에이징
                span = max(x["L"] - x["a"], 1)
                u = min(max((k - x["a"]) / span, 0.0), 1.0) ** gamma
                if x["cost"][k] <= cmin + u * (cmax - cmin) + 1e-9:
                    cand.append(((0, x["L"] - k, x["cost"][k], i), i))
        cand.sort()

        def fi_for(i: int) -> int:
            return int(st[i]["best_f"][k]) if policy == "D" and k <= st[i]["L"] else 0

        chosen: list[tuple[int, int]] = []  # (작업, 주파수 인덱스)
        if guarded:
            # 1) 마감 보호: 아무도 안 시작하면 EDF로도 마감을 못 지키는 상황이면, 마감 빠른 작업부터 강제 시작
            while len(chosen) < n_free and not feasible_after(k, [(i, st[i]["opts"][f][2]) for i, f in chosen]):
                nxt = next((i for i in edf_order if i in waiting and st[i]["a"] <= k
                            and i not in {c for c, _ in chosen}), None)
                if nxt is None:
                    break
                chosen.append((nxt, 0))
        # 2) 남은 슬롯은 탄소 기준 후보로 채우되(보호 정책은 마감 검사를 통과할 때만)
        for _, i in cand:
            if len(chosen) >= n_free:
                break
            if i in {c for c, _ in chosen}:
                continue
            fi = fi_for(i)
            if guarded:
                ok = False
                for f_try in range(fi, -1, -1):  # 고른 주파수가 마감 검사에 걸리면 한 단계씩 빠르게
                    if feasible_after(k, [(c, st[c]["opts"][f][2]) for c, f in chosen] + [(i, st[i]["opts"][f_try][2])]):
                        fi, ok = f_try, True
                        break
                if not ok:
                    continue
            chosen.append((i, fi))
        for i, fi in chosen:
            start(i, k, fi)
    if waiting:
        raise RuntimeError(f"{policy}: 실험 구간 안에 시작하지 못한 작업 {len(waiting)}개 (LATE_GRACE_H를 늘릴 것)")
    df = pd.DataFrame([res[i] for i in sorted(res)])
    jd = pd.DataFrame([asdict(j) for j in jobs])
    df = df.merge(jd, on="id")
    df["late"] = df["end_h"] > df["deadline_h"] + 1e-9
    df["delay_h"] = df["end_h"] - df["arrival"] - df["runtime"]
    return df


def sufmin_of(x: dict, k: int) -> tuple[float, float]:
    """남은 구간 [k, L]의 최저·최고 배출. 처음 부를 때 한 번 계산해 저장."""
    if "smin" not in x:
        L = x["L"]
        c = x["cost"][: L + 1]
        x["smin"] = np.minimum.accumulate(c[::-1])[::-1]
        x["smax"] = np.maximum.accumulate(c[::-1])[::-1]
    return x["smin"][k], x["smax"][k]


# ---------------------------------------------------------------- 곡선 처리
class Curve:
    def __init__(self, name: str):
        self.name = name
        df = load_curve(name)
        self.dates = pd.DatetimeIndex(df["date"].drop_duplicates())
        self.hourly = df["ci"].to_numpy()  # 8760, 2025-01-01 0시부터
        fc = np.full_like(self.hourly, np.nan)
        fc[168:] = self.hourly[:-168]      # 전주 같은 요일 같은 시각
        self.forecast = fc

    def window(self, day_idx: int, t_end: float, forecast=False) -> np.ndarray | None:
        """day_idx일 0시 기준 [T0, t_end) 구간을 15분 단위로. 범위를 벗어나면 None."""
        h0 = day_idx * 24 + int(math.floor(cfg.T0_H))
        h1 = day_idx * 24 + int(math.ceil(t_end))
        if h0 < 0 or h1 > len(self.hourly):
            return None
        src = self.forecast if forecast else self.hourly
        seg = src[h0:h1]
        if np.isnan(seg).any():
            return None
        return np.repeat(seg, K_STEPS_PER_H)


def horizon_end(jobs: list[Job]) -> float:
    return max(j.deadline for j in jobs) + cfg.LATE_GRACE_H


def day_kind(d: pd.Timestamp) -> str:
    return "주말·공휴일" if d.dayofweek >= 5 or d.date() in KR_HOL else "평일"


def season(d: pd.Timestamp) -> str:
    return {12: "겨울", 1: "겨울", 2: "겨울", 3: "봄", 4: "봄", 5: "봄", 6: "여름", 7: "여름", 8: "여름"}.get(d.month, "가을")


def summarize(df: pd.DataFrame, t0: pd.Timestamp) -> dict:
    out = {"emis_g": df["emis_g"].sum(), "energy_kwh": df["energy_kwh"].sum(), "late": int(df["late"].sum()),
           "delay_h": df["delay_h"].mean()}
    for c in ("당일", "익일", "주간"):
        s = df[df["cls"] == c]
        out[f"emis_g_{c}"] = s["emis_g"].sum()
        out[f"delay_h_{c}"] = s["delay_h"].mean()
    w = df[df["cls"] == "주간"]
    starts = [t0 + pd.Timedelta(hours=h) for h in w["start_h"]]
    out["weekly_on_weekend"] = sum(day_kind(s.normalize()) == "주말·공휴일" for s in starts)
    return out


# ---------------------------------------------------------------- 실행
def run_curve(name: str, jobs: list[Job]) -> dict:
    cv = Curve(name)
    t_end = horizon_end(jobs)
    rows = []
    delays = {}  # (정책, 마감 구분) -> 작업별 지연(h) 목록
    for di, d in enumerate(cv.dates):
        act = cv.window(di, t_end)
        fc = cv.window(di, t_end, forecast=True)
        if act is None or fc is None:
            continue
        for p in POLICIES:
            dec = fc if p == "E" else act
            cap = 24 + cfg.FIXED_START_H + cfg.DEADLINE_WINDOW_H[1] if p == "C7" else None
            r = simulate(jobs, act, dec, "C" if p in ("E", "C7") else p, deadline_cap=cap)
            for c, g in r.groupby("cls"):
                delays.setdefault((p, c), []).extend(g["delay_h"].tolist())
            rows.append({"date": d, "policy": p, "daykind": day_kind(d), "season": season(d), **summarize(r, d)})
        for sf in cfg.STATIC_FRAC_SENS:
            r = simulate(jobs, act, act, "D", static_frac=sf)
            rows.append({"date": d, "policy": f"D(정적 {sf:.2f})", "daykind": day_kind(d), "season": season(d),
                         **summarize(r, d)})
        for g in cfg.AGING_GAMMA_SENS:
            if g == cfg.AGING_GAMMA:
                continue
            r = simulate(jobs, act, act, "C", gamma=g)
            rows.append({"date": d, "policy": f"C(γ={g:g})", "daykind": day_kind(d), "season": season(d),
                         **summarize(r, d)})
    res = pd.DataFrame(rows)
    res.to_csv(S2 / f"daily_results_{name}.csv", index=False, encoding="utf-8-sig", float_format="%.4f")
    dstat = {}
    for (p, c), v in delays.items():
        a = np.array(v)
        dstat.setdefault(p, {})[c] = {"평균": float(a.mean()), "중앙값": float(np.median(a)),
                                      "90백분위": float(np.percentile(a, 90)), "최대": float(a.max())}
    return {"name": name, "res": res, "curve": cv, "delays": dstat}


def pick_representative(cv: Curve, valid_dates: set) -> dict[str, pd.Timestamp]:
    """대표일 3개를 데이터로 고른다(평일, 실험 가능 날짜만).
    봄 맑은 평일: 3~5월 평일 중 한낮(10~14시) 평균 탄소집약도가 가장 낮은 날(태양광이 가장 많이 들어온 날로 봄).
    여름 평일, 겨울 평일: 해당 계절 평일 중 24시간 곡선이 계절 평일 평균 곡선과 가장 가까운 날(전형적인 날)."""
    H = cv.hourly.reshape(-1, 24)
    dates = cv.dates
    pick = {}

    def ok(i, months):
        d = dates[i]
        return d.month in months and day_kind(d) == "평일" and d in valid_dates

    spring = [i for i in range(len(dates)) if ok(i, (3, 4, 5))]
    noon = H[:, list(cfg.NOON_SLOTS)].mean(axis=1)
    pick["봄 맑은 평일"] = dates[min(spring, key=lambda i: noon[i])]
    for label, months in (("여름 평일", (6, 7, 8)), ("겨울 평일", (12, 1, 2))):
        idx = [i for i in range(len(dates)) if ok(i, months)]
        mean = H[idx].mean(axis=0)
        pick[label] = dates[min(idx, key=lambda i: float(((H[i] - mean) ** 2).sum()))]
    return pick


def gantt(plt, jobs, cv: Curve, d: pd.Timestamp, label: str, name: str, pols=("A", "B", "C", "D"), tag: str = ""):
    di = list(cv.dates).index(d)
    t_end = horizon_end(jobs)
    act = cv.window(di, t_end)
    pols = list(pols)
    sims = {p: simulate(jobs, act, act, p) for p in pols}
    x_max = 40.0
    fig, axes = plt.subplots(len(pols) + 1, 1, figsize=(12, 2.0 + 1.65 * len(pols)), sharex=True,
                             gridspec_kw={"height_ratios": [1.3] + [1] * len(pols)})
    t = cfg.T0_H + np.arange(len(act)) * cfg.STEP_H
    m = t <= x_max
    axes[0].step(t[m], act[m], where="post", color=C_INK2, linewidth=1.5)
    axes[0].set_ylabel("탄소집약도\n(gCO2eq/kWh)", fontsize=9)
    axes[0].set_title(f"{label} {d:%Y-%m-%d}({'월화수목금토일'[d.dayofweek]}) 정책별 실행 시간표  [{CURVES[name][0]}]",
                      fontsize=12)
    for ax, p in zip(axes[1:], pols):
        r = sims[p]
        tot = r["emis_g"].sum()
        base = sims["A"]["emis_g"].sum()
        for row in r.itertuples():
            if row.start_h >= x_max:
                continue
            w = min(row.end_h, x_max) - row.start_h
            ax.barh(row.slot, w, left=row.start_h, height=0.72, color=CLS_COLOR[row.cls],
                    edgecolor="white", linewidth=1, hatch="///" if row.f < 1 else None, alpha=0.95)
        beyond = (r["start_h"] >= x_max).sum()
        ax.set_yticks(range(cfg.SLOTS))
        ax.set_yticklabels([f"슬롯{i + 1}" for i in range(cfg.SLOTS)], fontsize=9)
        ax.set_ylim(-0.6, cfg.SLOTS - 0.4)
        ax.grid(axis="y", visible=False)
        note = f"배출 {tot / 1000:.2f} kgCO2eq" + ("" if p == "A" else f" (A 대비 {(1 - tot / base) * 100:.1f}% 절감)")
        note += f", 마감 위반 {int(r['late'].sum())}건"
        if beyond:
            note += f", 주간 작업 {beyond}개는 그래프 밖(40시간 이후)에서 실행"
        ax.set_title(f"{POLICY_NAME[p]}: {note}", fontsize=10, loc="left")
    xt = np.arange(-4, x_max + 1, 4)
    axes[-1].set_xticks(xt)
    axes[-1].set_xticklabels([f"{'전날 ' if v < 0 else ('다음날 ' if v >= 24 else '')}{int(v % 24)}시" for v in xt],
                             fontsize=9)
    axes[-1].set_xlim(cfg.T0_H, x_max)
    from matplotlib.patches import Patch
    hs = [Patch(color=c, label=f"{k} 마감 작업") for k, c in CLS_COLOR.items()]
    if "D" in pols:
        hs.append(Patch(facecolor="white", edgecolor=C_INK2, hatch="///", label="주파수 낮춤(DVFS)"))
    fig.legend(handles=hs, loc="lower center", ncol=len(hs), bbox_to_anchor=(0.5, -0.02), fontsize=9)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fn = FIG / f"gantt{tag}_{name}_{d:%Y%m%d}.png"
    fig.savefig(fn)
    plt.close(fig)
    rows = []
    for p, r in sims.items():
        rows.append({"대표일": label, "날짜": f"{d:%Y-%m-%d}", "정책": POLICY_NAME[p], "배출(g)": r["emis_g"].sum(),
                     "에너지(kWh)": r["energy_kwh"].sum(), "마감 위반": int(r["late"].sum()),
                     "평균 지연(h)": r["delay_h"].mean()})
        r.assign(policy=p).to_csv(S2 / f"schedule_{name}_{d:%Y%m%d}_{p}.csv", index=False, encoding="utf-8-sig",
                                  float_format="%.3f")
    return fn, rows


def hist(plt, results: dict, name: str):
    res = results["res"]
    base = res[res["policy"] == "A"].set_index("date")["emis_g"]
    fig, ax = plt.subplots(figsize=(8, 4.4))
    bins = np.arange(-10, 41, 1.5)
    for p, c in (("B", C_YELLOW), ("C", C_BLUE), ("D", C_ORANGE), ("E", C_AQUA)):
        s = res[res["policy"] == p].set_index("date")["emis_g"]
        sav = (1 - s / base) * 100
        ax.hist(sav, bins=bins, histtype="step", linewidth=2, color=c, label=f"{POLICY_NAME[p]} (중앙값 {sav.median():.1f}%)")
    ax.set_xlabel("현재 관행(A) 대비 절감률 (%)")
    ax.set_ylabel("일수")
    ax.set_title(f"날짜별 절감률 분포 [{CURVES[name][0]}]", fontsize=12)
    ax.legend(fontsize=9)
    fn = FIG / f"hist_savings_{name}.png"
    fig.savefig(fn)
    plt.close(fig)
    return fn


def bars(plt, tables: dict):
    """정책별 연간 절감률 막대(곡선별 묶음)."""
    pols = ["A'", "B", "C", "D", "E"]
    names = list(tables)
    fig, ax = plt.subplots(figsize=(10.5, 4.8))
    w = 0.8 / len(names)
    colors = {"grid": C_BLUE, "market": C_ORANGE, "monthly": C_AQUA}
    for i, n in enumerate(names):
        t = tables[n].set_index("정책코드")
        v = [t.loc[p, "A 대비 절감률(%)"] for p in pols]
        xs = np.arange(len(pols)) + (i - (len(names) - 1) / 2) * w
        ax.bar(xs, v, width=w * 0.92, color=colors.get(n, C_INK2), label=CURVES[n][0])
        for p, x_, y_ in zip(pols, xs, v):
            ax.annotate(f"{y_:.1f}", (x_, y_), xytext=(0, 3 if y_ >= 0 else -11), textcoords="offset points",
                        ha="center", fontsize=8, color=C_INK)
        lo, hi = (t.loc[f"D(정적 {sf:.2f})", "A 대비 절감률(%)"] for sf in (max(cfg.STATIC_FRAC_SENS), min(cfg.STATIC_FRAC_SENS)))
        xd = xs[pols.index("D")]
        ax.errorbar([xd], [t.loc["D", "A 대비 절감률(%)"]], yerr=[[t.loc["D", "A 대비 절감률(%)"] - lo],
                    [hi - t.loc["D", "A 대비 절감률(%)"]]], fmt="none", ecolor=C_INK, capsize=4, linewidth=1)
    ax.axhline(0, color=C_INK2, linewidth=1)
    ax.set_xticks(range(len(pols)))
    lates = {p: " / ".join(f"{int(tables[n].set_index('정책코드').loc[p, 'late']):,}" for n in names) for p in pols}
    ax.set_xticklabels([f"{POLICY_NAME[p]}\n마감 위반 {lates[p]}건" for p in pols], fontsize=8.5)
    ax.set_ylim(min(-3, ax.get_ylim()[0]), None)
    ax.set_ylabel("현재 관행(A) 대비 연간 절감률 (%)")
    ax.set_title(f"정책별 연간 배출 절감률 (D의 세로선: 정적 전력 비율 {max(cfg.STATIC_FRAC_SENS)}~{min(cfg.STATIC_FRAC_SENS)} 가정 범위)", fontsize=11)
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(axis="x", visible=False)
    fn = FIG / "bar_annual_savings.png"
    fig.savefig(fn)
    plt.close(fig)
    return fn


def annual_table(res: pd.DataFrame) -> pd.DataFrame:
    g = res.groupby("policy").agg(emis_g=("emis_g", "sum"), energy_kwh=("energy_kwh", "sum"), late=("late", "sum"),
                                  delay_h=("delay_h", "mean"), days=("date", "nunique"),
                                  late_days=("late", lambda s: int((s > 0).sum())))
    base = g.loc["A", "emis_g"]
    g["A 대비 절감률(%)"] = (1 - g["emis_g"] / base) * 100
    g = g.reset_index().rename(columns={"policy": "정책코드"})
    order = POLICIES + [p for p in g["정책코드"] if p not in POLICIES]
    g["정책"] = g["정책코드"].map(lambda p: POLICY_NAME.get(p, p))
    return g.set_index("정책코드").loc[order].reset_index()


def extra_metrics(results: dict) -> dict:
    res, cv = results["res"], results["curve"]
    H = cv.hourly.reshape(-1, 24)
    out = {}
    # 곡선만으로 본 심야(2시)·저녁 → 한낮 절감률
    df = pd.DataFrame(H, index=cv.dates)
    df["season"] = [season(d) for d in cv.dates]
    for key, sub in [("연간", df)] + [(s, df[df["season"] == s]) for s in ("봄", "여름", "가을", "겨울")]:
        m = sub.drop(columns="season").mean()
        noon = m[list(cfg.NOON_SLOTS)].mean()
        night = m[cfg.NIGHT_SLOT]
        eve = m[list(cfg.EVENING_SLOTS)].mean()
        out[f"곡선_{key}"] = {"심야2시": night, "한낮10~14시": noon, "저녁19~23시": eve,
                             "심야→한낮 절감률(%)": (1 - noon / night) * 100,
                             "저녁→한낮 절감률(%)": (1 - noon / eve) * 100}
    # 작업 구분별 배출(연간 합)과 A 대비 절감
    g = res.groupby("policy")[[f"emis_g_{c}" for c in ("당일", "익일", "주간")]].sum()
    out["구분별"] = {c: {p: (1 - g.loc[p, f"emis_g_{c}"] / g.loc["A", f"emis_g_{c}"]) * 100 for p in ("C", "D")}
                   for c in ("당일", "익일", "주간")}
    # 주말 이동 추가 효과: 평일 실험에서 C(7일) vs C7(익일까지만)
    wd = res[res["daykind"] == "평일"]
    gw = wd.groupby("policy")[["emis_g", "emis_g_주간", "weekly_on_weekend"]].sum()
    n_wd = wd["date"].nunique()
    out["주말이동"] = {
        "평일 실험 일수": n_wd,
        "A 대비 C7 절감률(%)": (1 - gw.loc["C7", "emis_g"] / gw.loc["A", "emis_g"]) * 100,
        "A 대비 C 절감률(%)": (1 - gw.loc["C", "emis_g"] / gw.loc["A", "emis_g"]) * 100,
        "주말 이동 추가 절감(%p, 전체 배출 기준)": (gw.loc["C7", "emis_g"] - gw.loc["C", "emis_g"]) / gw.loc["A", "emis_g"] * 100,
        "주간 작업만: C7 대비 C 절감률(%)": (1 - gw.loc["C", "emis_g_주간"] / gw.loc["C7", "emis_g_주간"]) * 100,
        "C에서 주말·공휴일에 시작한 주간 작업 비율(%)": gw.loc["C", "weekly_on_weekend"] / (n_wd * 6) * 100,
    }
    # 예측(E) vs 완전 정보(C)
    a = res.groupby("policy")["emis_g"].sum()
    out["예측"] = {"C 절감률(%)": (1 - a["C"] / a["A"]) * 100, "E 절감률(%)": (1 - a["E"] / a["A"]) * 100,
                 "차이(%p)": ((1 - a["C"] / a["A"]) - (1 - a["E"] / a["A"])) * 100}
    # 계절·요일별 C, D 절감률
    for key in ("season", "daykind"):
        t = res.groupby([key, "policy"])["emis_g"].sum().unstack()
        out[f"{key}별"] = {k: {p: (1 - t.loc[k, p] / t.loc[k, "A"]) * 100 for p in ("B", "C", "D")} for k in t.index}
    # D: 에너지 절감
    e = res.groupby("policy")["energy_kwh"].sum()
    out["DVFS 에너지"] = {p: {"에너지(kWh)": e[p], "C 대비 에너지 절감률(%)": (1 - e[p] / e["C"]) * 100}
                        for p in e.index if p.startswith("D")}
    return out


def main(argv):
    S2.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    plt = setup_matplotlib()
    jobs = make_jobs()
    jdf = pd.DataFrame([asdict(j) for j in jobs])
    jdf.to_csv(S2 / "jobs.csv", index=False, encoding="utf-8-sig")
    print(f"작업 {len(jobs)}개, 총 실행 시간 {jdf['runtime'].sum():.2f}h, 구분별 {jdf.groupby('cls').size().to_dict()}")

    names = argv[1:] or available_curves()
    main_name = main_curve()
    tables, extras, rep_rows, figs = {}, {}, [], {}
    for name in names:
        print(f"--- 곡선 {name}: {CURVES[name][0]}")
        r = run_curve(name, jobs)
        a = r["res"]
        if (a[a["policy"] == "A"]["late"] > 0).any():
            raise SystemExit("[중단] 현재 관행(A)에서 마감 위반이 생김. 작업 세트 설정을 고칠 것.")
        tables[name] = annual_table(a)
        tables[name].to_csv(S2 / f"annual_{name}.csv", index=False, encoding="utf-8-sig", float_format="%.4f")
        extras[name] = extra_metrics(r)
        extras[name]["지연"] = r["delays"]
        figs[f"hist_{name}"] = str(hist(plt, r, name).relative_to(OUT.parent))
        if name == main_name or name == "market":
            valid = set(a["date"])
            reps = pick_representative(r["curve"], valid)
            for label, d in reps.items():
                fn, rows = gantt(plt, jobs, r["curve"], d, label, name)
                figs[f"gantt_{name}_{label}"] = str(fn.relative_to(OUT.parent))
                rep_rows += [{"곡선": name, **x} for x in rows]
            if name == main_name:
                d = reps["봄 맑은 평일"]
                fn, _ = gantt(plt, jobs, r["curve"], d, "봄 맑은 평일", name, pols=("A", "C"), tag="_AC")
                figs[f"gantt_AC_{name}_봄 맑은 평일"] = str(fn.relative_to(OUT.parent))
        print(tables[name][["정책", "emis_g", "A 대비 절감률(%)", "late", "late_days", "delay_h"]].round(2).to_string())
    figs["bar"] = str(bars(plt, tables).relative_to(OUT.parent))
    pd.DataFrame(rep_rows).to_csv(S2 / "representative_days.csv", index=False, encoding="utf-8-sig", float_format="%.3f")
    meta = {"main_curve": main_name, "curves": names, "figures": figs, "extras": extras,
            "experiment_days": {n: int(tables[n]["days"].iloc[0]) for n in names}}
    (S2 / "stage2_results.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    print("완료:", S2)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv)
