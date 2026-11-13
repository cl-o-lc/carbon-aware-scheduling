"""발표 대본 전문을 slides_draft.md에서 뽑아 04_발표자료/대본.md로 저장한다(영상 녹화용).

장마다 제목, 대본, 음절 수와 예상 시간(초당 5음절 ~ 4.5음절)을 적는다.
사용법:  python scripts/10_export_script.py
"""
from __future__ import annotations

import re
import sys

from common import ROOT

DECK = ROOT / "04_발표자료"


def syllables(text: str) -> int:
    return len(re.findall(r"[가-힣]", text))


def main():
    draft = (DECK / "slides_draft.md").read_text(encoding="utf-8")
    titles = re.findall(r"^## (\d+)\. (.+)$", draft, re.M)
    scripts = [b.strip() for b in re.findall(r"\*\*대본 \(약 \d+초\):\*\*\n\s+(.+?)\n\n", draft, re.S)]
    if len(titles) != len(scripts):
        raise SystemExit(f"[중단] 장 제목 {len(titles)}개와 대본 {len(scripts)}개가 다름")
    total = sum(syllables(t) for t in scripts)
    L = ["# 발표 대본", "",
         "`scripts/10_export_script.py`가 `04_발표자료/slides_draft.md`에서 자동으로 뽑은 문서다. 대본을 고칠 때는 원고를 고치고 다시 실행한다.", "",
         f"- 전체 {len(scripts)}장, {total:,}음절, 예상 {total / 5 / 60:.1f}~{total / 4.5 / 60:.1f}분(초당 5~4.5음절)", ""]
    for (no, title), text in zip(titles, scripts):
        n = syllables(text)
        L += ["---", "", f"## {no}. {title}", "", f"*{n}음절, 약 {n / 5:.0f}~{n / 4.5:.0f}초*", "", text, ""]
    out = DECK / "대본.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(out, total)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
