"""발표에 쓸 그래프를 04_발표자료/figures/로 모은다(원본은 03_분석/에 그대로 둔다).

사용법:  python scripts/06_presentation_figures.py   (02, 04 스크립트를 먼저 실행)
"""
from __future__ import annotations

import json
import shutil
import sys

from common import OUT, ROOT

DEST = ROOT / "04_발표자료" / "figures"


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    meta = json.loads((OUT / "stage2" / "stage2_results.json").read_text(encoding="utf-8"))
    main_name = meta["main_curve"]
    picks = {
        "01_하루곡선_2025_vs_2023.png": OUT / "figures" / "fig1_daily_curve_2025_vs_2023.png",
        "02_계절별_곡선.png": OUT / "figures" / "fig2_seasonal_curves.png",
        "03_월x시각_히트맵_2025.png": OUT / "figures" / "fig5_heatmap_month_hour_2025.png",
        "04_간트_봄맑은평일_A_vs_C.png": OUT.parent / meta["figures"][f"gantt_AC_{main_name}_봄 맑은 평일"],
    }
    for dst, src in picks.items():
        shutil.copy2(src, DEST / dst)
        print(f"{src.relative_to(ROOT)} -> {(DEST / dst).relative_to(ROOT)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
