"""여러 스크립트가 함께 쓰는 경로, 데이터 읽기, 그래프 설정."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "02_데이터" / "raw"
OUT = ROOT / "03_분석"

FUEL_FILE = "한국전력거래소_연료원별 시간대별 설비용량 및 전력거래량_{year}1231.csv"
MAIN_YEAR = 2025      # 주 분석 연도
COMPARE_YEAR = 2023   # 비교·검증 연도 (2024년판은 원자력·석탄·LNG가 빠져 있어 쓰지 않음)

# 그래프 색: dataviz 기본 팔레트(categorical slot 1~4, 고정 순서)
C_BLUE, C_ORANGE, C_AQUA, C_YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
C_INK, C_INK2, C_GRID = "#0b0b0b", "#52514e", "#e4e3df"
YEAR_COLOR = {MAIN_YEAR: C_BLUE, COMPARE_YEAR: C_ORANGE}


def detect_encoding(path: Path) -> str:
    b = path.read_bytes()
    for enc in ("utf-8-sig", "cp949"):
        try:
            b.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    raise ValueError(f"인코딩을 알 수 없음: {path}")


def load_fuel(path: Path) -> pd.DataFrame:
    """연료원별 파일을 (date, hour, fuel, mwh) 공통 형식으로 읽는다. 연도마다 다른 컬럼 이름을 통일한다."""
    df = pd.read_csv(path, encoding=detect_encoding(path), dtype=str)
    df.columns = [c.strip() for c in df.columns]
    ren = {"거래일자": "date", "거래일": "date", "거래시간": "hour", "시간": "hour",
           "연료원별": "fuel", "연료원": "fuel", "원료원": "fuel", "전력거래량(MWh)": "mwh"}
    df = df.rename(columns=ren)[["date", "hour", "fuel", "mwh"]].dropna(how="all")
    df["fuel"] = df["fuel"].str.strip()
    df["hour"] = df["hour"].astype(int)
    df["mwh"] = pd.to_numeric(df["mwh"])
    return df


def load_year(year: int) -> pd.DataFrame:
    return load_fuel(RAW / FUEL_FILE.format(year=year))


# 시간별 탄소 곡선(2025년). 2단계 시뮬레이션은 곡선 이름만 바꿔 다시 돌린다.
CURVES = {
    "grid": ("실제 전력망 기준(시장 + 비계량 태양광 5분 추정 집계)", "ci_hourly_2025_grid5min.csv"),
    "market": ("보수적 하한(전력시장 거래량만)", "ci_hourly_2025.csv"),
    "monthly": ("비계량 태양광 월별 배수 가정", "ci_hourly_2025_with_nonmarket_solar.csv"),
}


def available_curves() -> list[str]:
    return [k for k, (_, f) in CURVES.items() if (OUT / f).exists()]


def main_curve() -> str:
    """주 결과 곡선: 5분 실측 집계(grid)가 있으면 그것, 없으면 시장 거래량만(market)."""
    return "grid" if "grid" in available_curves() else "market"


def load_curve(name: str) -> pd.DataFrame:
    df = pd.read_csv(OUT / CURVES[name][1], parse_dates=["date"])
    df = df.sort_values(["date", "slot"]).reset_index(drop=True)
    if len(df) != 8760:
        raise ValueError(f"{name} 곡선 길이가 8760이 아님: {len(df)}")
    return df[["date", "slot", "ci"]]


EPSIS_SOLAR_FILE = "EPSIS_태양광발전량추계_월별_030400.html"


def load_epsis_solar() -> pd.DataFrame:
    """EPSIS 추계정보 페이지 원본에서 월별 태양광 발전량(MWh)을 읽는다.
    c1=전력시장 참여(실적), c2=한전PPA(실적), c3=자가용태양광(추계). 페이지 스크립트의 '전체' 목록을 쓴다."""
    import re

    t = (RAW / EPSIS_SOLAR_FILE).read_text(encoding="utf-8", errors="replace")
    blk = t[t.index('=="전체"'):]
    blk = blk[: blk.index("gridApp.setData")]
    rows = re.findall(r'period = "(\d{4})\.(\d{2})";.*?c1 = "([\d.]*)";\s*c2 = "([\d.]*)";\s*c3 = "([\d.]*)";', blk, re.S)
    df = pd.DataFrame(rows, columns=["year", "month", "market", "ppa", "btm"]).astype(
        {"year": int, "month": int, "market": float, "ppa": float, "btm": float})
    df = df.drop_duplicates(["year", "month"]).sort_values(["year", "month"]).reset_index(drop=True)
    df["total"] = df[["market", "ppa", "btm"]].sum(axis=1)
    df["factor"] = df["total"] / df["market"]
    return df


def setup_matplotlib():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager

    names = {f.name for f in font_manager.fontManager.ttflist}
    for cand in ("Malgun Gothic", "NanumGothic", "AppleGothic", "Noto Sans CJK KR", "Noto Sans KR"):
        if cand in names:
            plt.rcParams["font.family"] = cand
            break
    plt.rcParams.update({
        "axes.unicode_minus": False,
        "figure.dpi": 110, "savefig.dpi": 200, "savefig.bbox": "tight",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": C_INK2, "axes.labelcolor": C_INK, "xtick.color": C_INK2, "ytick.color": C_INK2,
        "axes.grid": True, "grid.color": C_GRID, "grid.linewidth": 0.8,
        "lines.linewidth": 2, "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "bold",
        "legend.frameon": False,
    })
    return plt
