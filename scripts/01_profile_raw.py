"""0단계: 받은 원본 CSV의 인코딩, 컬럼, 행 수, 기간, 범주 값 점검.

결과는 화면과 02_데이터/raw_profile.md에 함께 기록한다.
사용법:  python scripts/01_profile_raw.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "02_데이터" / "raw"
OUT = ROOT / "02_데이터" / "raw_profile.md"


def detect_encoding(path: Path) -> str:
    b = path.read_bytes()
    for enc in ("utf-8-sig", "cp949"):
        try:
            b.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "unknown"


def profile(path: Path) -> list[str]:
    enc = detect_encoding(path)
    df = pd.read_csv(path, encoding=enc, dtype=str)
    raw_cols = list(df.columns)
    df.columns = [c.strip() for c in df.columns]
    blank = df.isna().all(axis=1)
    df = df[~blank]
    L = [f"## {path.name}", ""]
    L.append(f"- 인코딩: `{enc}`")
    L.append(f"- 크기: {path.stat().st_size:,} bytes")
    L.append(f"- 행 수(헤더 제외): {len(df):,}" + (f" (완전 빈 행 {int(blank.sum())}개 제외)" if blank.any() else ""))
    L.append(f"- 컬럼({len(raw_cols)}, 원본 표기 그대로): {', '.join(f'`{c}`' for c in raw_cols)}")

    date_col = next((c for c in df.columns if c in ("거래일자", "거래일", "날짜")), None)
    if date_col:
        d = pd.to_datetime(df[date_col], errors="coerce")
        L.append(f"- 기간(`{date_col}`): {d.min().date()} ~ {d.max().date()} ({d.dt.normalize().nunique()}일)")
        bad = d.isna().sum()
        if bad:
            L.append(f"- 날짜 변환 실패 행: {bad}")
    hour_col = next((c for c in df.columns if c in ("거래시간", "거래시각", "시간")), None)
    if hour_col:
        hrs = sorted(df[hour_col].dropna().astype(int).unique())
        L.append(f"- 시간 값(`{hour_col}`): {hrs[0]} ~ {hrs[-1]} ({len(hrs)}개)")

    for c in df.columns:
        if c in (date_col, hour_col):
            continue
        num = pd.to_numeric(df[c], errors="coerce")
        if num.notna().mean() > 0.95:
            L.append(f"- `{c}` 수치: 최소 {num.min():,.3f}, 최대 {num.max():,.3f}, 결측 {int(num.isna().sum())}, 음수 {int((num < 0).sum())}")
        else:
            vc = df[c].value_counts(dropna=False)
            L.append(f"- `{c}` 구분 값({len(vc)}개):")
            for k, v in vc.items():
                L.append(f"    - {k}: {v:,}행")

    # 연료원별 연간 거래량 합계(연료원 컬럼이 있는 경우)
    fuel_col = next((c for c in df.columns if c in ("연료원별", "연료원", "원료원")), None)
    vol_col = next((c for c in df.columns if c.startswith("전력거래량")), None)
    if fuel_col and vol_col:
        s = pd.to_numeric(df[vol_col], errors="coerce").groupby(df[fuel_col]).sum().sort_values(ascending=False)
        tot = s.sum()
        L.append(f"- 연료원별 거래량 합계(`{vol_col}`), 총 {tot:,.0f} MWh:")
        for k, v in s.items():
            L.append(f"    - {k}: {v:,.0f} MWh ({v / tot * 100:.2f}%)")
        if date_col and hour_col:
            per_hour = df.groupby([date_col, hour_col])[fuel_col].nunique()
            L.append(f"- 시각(일자·시간)당 연료원 수: 최소 {per_hour.min()}, 최대 {per_hour.max()}, 시각 수 {len(per_hour):,}")
            dup = df.duplicated([date_col, hour_col, fuel_col]).sum()
            L.append(f"- (일자, 시간, 연료원) 중복 행: {dup}")
    L.append("")
    L.append("앞 3행:")
    L.append("")
    L.append("```")
    L.append(df.head(3).to_csv(index=False).strip())
    L.append("```")
    L.append("")
    return L


def load_fuel(path: Path) -> pd.DataFrame:
    """연료원별 파일을 (일자, 시간, 연료원, 거래량) 공통 형식으로 읽는다."""
    df = pd.read_csv(path, encoding=detect_encoding(path), dtype=str)
    df.columns = [c.strip() for c in df.columns]
    ren = {"거래일자": "date", "거래일": "date", "거래시간": "hour", "시간": "hour",
           "연료원별": "fuel", "연료원": "fuel", "원료원": "fuel", "전력거래량(MWh)": "mwh"}
    df = df.rename(columns=ren)[["date", "hour", "fuel", "mwh"]].dropna(how="all")
    df["hour"] = df["hour"].astype(int)
    df["mwh"] = pd.to_numeric(df["mwh"])
    return df


def crosscheck() -> list[str]:
    """2023년 11~12월: 두 데이터셋(15127395 2023년판, 15081098)의 값이 같은지 확인."""
    a = RAW / "한국전력거래소_연료원별 시간대별 설비용량 및 전력거래량_20231231.csv"
    b = RAW / "한국전력거래소_연료원별 전력거래량_20231231.csv"
    if not (a.exists() and b.exists()):
        return []
    A, B = load_fuel(a), load_fuel(b)
    A = A[A["date"] >= "2023-11-01"]
    m = A.merge(B, on=["date", "hour", "fuel"], how="outer", suffixes=("_new", "_old"), indicator=True)
    both = m[m["_merge"] == "both"]
    diff = (both["mwh_new"] - both["mwh_old"]).abs()
    L = ["## 교차 점검: 2023년 11~12월 두 데이터셋 비교", ""]
    L.append(f"- 비교 파일: `{a.name}` vs `{b.name}`")
    L.append(f"- 양쪽 모두 있는 (일자, 시간, 연료원) 행: {len(both):,}")
    L.append(f"- 한쪽에만 있는 연료원: 새 목록만 {sorted(m.loc[m['_merge']=='left_only','fuel'].unique())}, "
             f"옛 목록만 {sorted(m.loc[m['_merge']=='right_only','fuel'].unique())}")
    L.append(f"- 값이 일치하는 행 비율(차이 1 MWh 미만): {(diff < 1).mean() * 100:.2f}%, 최대 차이 {diff.max():,.1f} MWh")
    tn, to = both["mwh_new"].sum(), both["mwh_old"].sum()
    L.append(f"- 공통 행 합계: 새 목록 {tn:,.0f} MWh, 옛 목록 {to:,.0f} MWh (차이 {(tn - to) / to * 100:+.3f}%)")
    L.append("")
    return L


def main() -> None:
    lines = ["# 원본 데이터 점검 결과", "", "`scripts/01_profile_raw.py`가 자동 생성. 직접 수정하지 말 것.", ""]
    for p in sorted(RAW.glob("*.csv")):
        lines += profile(p)
    lines += crosscheck()
    text = "\n".join(lines) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
