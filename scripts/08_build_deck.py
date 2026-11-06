"""3단계: 발표 자료(16:9 PPTX) 생성. python-pptx 사용.

- 슬라이드 내용은 04_발표자료/slides_draft.md를 바탕으로 줄였고, 숫자는 분석 출력에서 읽는다.
- 발표 대본은 slides_draft.md의 '대본' 블록을 읽어 발표자 노트에 넣는다.
- 결과: 04_발표자료/_build/deck_raw.pptx (이후 09_export_deck.ps1이 PowerPoint로 글꼴 포함 저장 + PDF)

사용법:  python scripts/08_build_deck.py
"""
from __future__ import annotations

import json
import re
import sys

import pandas as pd
from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

from common import OUT, ROOT, main_curve, weekend_compare

DECK = ROOT / "04_발표자료"
FIGS = DECK / "figures"
BUILD = DECK / "_build"
FONT = "Pretendard"

INK, INK2 = "1F2D2A", "5F6B66"
SDG13, SDG7, SDG9 = "3F7E44", "FCC30B", "FD6925"  # SDG 공식 색
LIGHT, WHITE = "E6F0E7", "FFFFFF"
SW, SH = 13.333, 7.5


# ---------------------------------------------------------------- 숫자 읽기
def numbers() -> dict:
    name = main_curve()
    s2 = json.loads((OUT / "stage2" / "stage2_results.json").read_text(encoding="utf-8"))
    e = s2["extras"][name]
    t = pd.read_csv(OUT / "stage2" / f"annual_{name}.csv").set_index("정책코드")
    tm = pd.read_csv(OUT / "stage2" / "annual_monthly.csv").set_index("정책코드")
    s1 = json.loads((OUT / "ci_summary.json").read_text(encoding="utf-8"))
    m25, m23 = s1["metrics"]["2025"], s1["metrics"]["2023"]
    wk = weekend_compare(name)["전체"]
    import config_simulation as cfg
    lo, hi = min(cfg.STATIC_FRAC_SENS), max(cfg.STATIC_FRAC_SENS)
    return {
        "C": t.loc["C", "A 대비 절감률(%)"], "D": t.loc["D", "A 대비 절감률(%)"],
        "D_lo": t.loc[f"D(정적 {hi:.2f})", "A 대비 절감률(%)"], "D_hi": t.loc[f"D(정적 {lo:.2f})", "A 대비 절감률(%)"],
        "C_monthly": tm.loc["C", "A 대비 절감률(%)"], "B_late": int(t.loc["B", "late"]),
        "E": e["예측"]["E 절감률(%)"], "E_diff": e["예측"]["차이(%p)"],
        "night_noon": e["곡선_연간"]["심야→한낮 절감률(%)"], "night_noon_spring": e["곡선_봄"]["심야→한낮 절감률(%)"],
        "night_noon_winter": e["곡선_겨울"]["심야→한낮 절감률(%)"],
        "same_day": e["구분별"]["당일"]["C"],
        "C7": wk["C7"], "weekly_weekend": wk["주말시작비율_C"], "days": wk["일수"],
        "delay_A": e["지연"]["A"]["당일"]["중앙값"], "delay_C": e["지연"]["C"]["당일"]["중앙값"],
        "emis_A": t.loc["A", "emis_g"] / 1000, "emis_C": t.loc["C", "emis_g"] / 1000,
        "ci_min": m25["연간"]["최소"], "ci_min_h": int(m25["연간"]["최소시각"]),
        "ci_max": m25["연간"]["최대"], "ci_max_h": int(m25["연간"]["최대시각"]),
        "wd": m25["평일"]["평균"], "we": m25["주말·공휴일"]["평균"],
        "static": cfg.STATIC_FRAC, "s_lo": lo, "s_hi": hi,
    }


def scripts_from_draft() -> list[str]:
    s = (DECK / "slides_draft.md").read_text(encoding="utf-8")
    blocks = re.findall(r"\*\*대본 \(약 \d+초\):\*\*\n\s+(.+?)\n\n", s, re.S)
    return [b.strip() for b in blocks]


# ---------------------------------------------------------------- 그리기 도우미
def rgb(h: str) -> RGBColor:
    return RGBColor.from_string(h)


def no_word_split(p):
    """한글 단어가 줄 끝에서 잘리지 않게(공백에서만 줄바꿈)."""
    p._p.get_or_add_pPr().set("eaLnBrk", "0")


NB = " "  # 숫자와 단위를 붙여 두는 줄바꿈 없는 공백


def style_run(run, size, bold=False, color=INK):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.color.rgb = rgb(color)
    rpr = run._r.get_or_add_rPr()
    rpr.set("lang", "ko-KR")  # 한국어로 지정해야 PowerPoint가 한글 줄바꿈 규칙(단어 단위)을 적용
    rpr.set("altLang", "en-US")
    for tag in ("a:latin", "a:ea", "a:cs"):  # 한글(ea)까지 같은 글꼴
        el = rpr.find(qn(tag))
        if el is None:
            el = etree.SubElement(rpr, qn(tag))
        el.set("typeface", FONT)


def text_box(slide, x, y, w, h, paras, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, name=None):
    """paras: [(text, size, bold, color)] 또는 [[(text, size, bold, color), ...] 한 문단의 여러 조각]"""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, side, 0)
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        no_word_split(p)
        pieces = para if isinstance(para, list) else [para]
        for txt, size, bold, color in pieces:
            r = p.add_run()
            r.text = txt
            style_run(r, size, bold, color)
    return tb


def bullets(slide, x, y, w, h, items, size=19, color=INK, gap=10, name="bullets", bullet_color=SDG13):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, side, 0)
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        no_word_split(p)
        ppr = p._p.get_or_add_pPr()
        ppr.set("marL", str(Emu(Inches(0.28))))
        ppr.set("indent", str(-Emu(Inches(0.28))))
        bu_clr = etree.SubElement(ppr, qn("a:buClr"))
        etree.SubElement(bu_clr, qn("a:srgbClr")).set("val", bullet_color)
        etree.SubElement(ppr, qn("a:buFont")).set("typeface", "Arial")
        etree.SubElement(ppr, qn("a:buChar")).set("char", "•")
        pieces = item if isinstance(item, list) else [(item, False)]
        for txt, bold in pieces:
            r = p.add_run()
            r.text = txt
            style_run(r, size, bold, color)
    return tb


def box(slide, x, y, w, h, fill, line=None, radius=True, name=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                                 Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        shp.adjustments[0] = 0.08
    shp.fill.solid()
    shp.fill.fore_color.rgb = rgb(fill)
    if line:
        shp.line.color.rgb = rgb(line)
        shp.line.width = Pt(1)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    if name:
        shp.name = name
    return shp


def picture(slide, path, x, y, w, name):
    pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), width=Inches(w))
    pic.name = name
    return pic


def header(slide, title, message, n, dark=False):
    tc, mc = (WHITE, SDG7) if dark else (INK, SDG13)
    text_box(slide, 0.6, 0.38, 12.1, 0.62, [(title, 30, True, tc)], name="title")
    text_box(slide, 0.6, 1.06, 12.1, 0.55, [(message, 22, True, mc)], name="key_message")
    text_box(slide, 12.2, 7.02, 0.55, 0.3, [(str(n), 11, False, WHITE if dark else INK2)], align=PP_ALIGN.RIGHT,
             name="page_number")


def footnote(slide, text, dark=False):
    text_box(slide, 0.6, 7.0, 11.4, 0.35, [(text, 11, False, "B9C4BF" if dark else INK2)], name="source_note")


def background(slide, color):
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = rgb(color)


def term_card(slide, x, y, w, h, lines):
    box(slide, x, y, w, h, LIGHT, name="term_card")
    paras = [[(k, 18, True, SDG13), (v, 18, False, INK)] for k, v in lines]
    text_box(slide, x + 0.2, y + 0.15, w - 0.4, h - 0.3, paras, anchor=MSO_ANCHOR.MIDDLE, name="term_text")


def sdg_chip(slide, x, y, label, color, w=1.25, h=0.5, size=18):
    box(slide, x, y, w, h, color, name=f"chip_{label}")
    text_box(slide, x, y, w, h, [(label, size, True, INK if color == SDG7 else WHITE)], align=PP_ALIGN.CENTER,
             anchor=MSO_ANCHOR.MIDDLE, name=f"chip_text_{label}")


# ---------------------------------------------------------------- 슬라이드
FIG_X, FIG_Y, FIG_W = 0.6, 1.85, 8.2      # 그림 폭 8.2인치 = 슬라이드 폭의 61.5%
COL_X, COL_W = 9.15, 3.6                  # 오른쪽 글 칸


def build():
    N = numbers()
    notes = scripts_from_draft()
    if len(notes) != 11:
        raise SystemExit(f"[중단] 원고의 대본 블록이 11개가 아님: {len(notes)}")
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(SW), Inches(SH)
    blank = prs.slide_layouts[6]
    slides = []

    def new(dark=False):
        s = prs.slides.add_slide(blank)
        background(s, INK if dark else WHITE)
        slides.append(s)
        return s

    # 1 표지
    s = new(dark=True)
    text_box(s, 0.9, 1.5, 12.0, 1.0, [("서버 작업, 언제 돌려야 탄소가 가장 적을까", 38, True, WHITE)], name="title")
    text_box(s, 0.9, 2.55, 11.5, 0.7, [("탄소 인지 작업 스케줄링", 32, True, SDG7)], name="subtitle")
    text_box(s, 0.9, 3.6, 11.0, 0.9, [("미뤄도 되는 컴퓨터 일을 전기가 깨끗한 시간으로 옮기면,", 22, False, "DDE5E1"),
                                      ("같은 일을 더 적은 탄소로 할 수 있다", 22, False, "DDE5E1")], name="key_message")
    for i, (lab, col) in enumerate((("SDG 7.3", SDG7), ("SDG 9.4", SDG9), ("SDG 13.3", SDG13))):
        sdg_chip(s, 0.9 + i * 1.45, 4.95, lab, col)
    text_box(s, 0.9, 6.25, 11.0, 0.5, [("2026학년도 ESD 비교과 공모전  |  박수진", 20, False, WHITE)], name="author")

    # 2 문제
    s = new()
    header(s, "데이터센터 전기 사용이 빠르게 늘고 있다", "AI 시대, 데이터센터가 쓰는 전기가 몇 년 안에 두 배가 된다", 2)
    cards = [("415 TWh", "2024년 전 세계 데이터센터 전력\n세계 전력의 약 1.5%", INK),
             ("945 TWh", "2030년 전망, 두 배 이상\n일본 한 나라 소비보다 조금 많음", SDG9),
             ("6.2 GW", "2038년 한국 데이터센터 전력수요 전망\n(2022년 말 147개, 1,762 MW)", SDG13)]
    for i, (num, lab, col) in enumerate(cards):
        x = 0.6 + i * 4.1
        box(s, x, 1.95, 3.85, 2.75, "F4F7F5", name=f"stat_card_{i + 1}")
        text_box(s, x + 0.3, 2.15, 3.3, 1.0, [(num, 50, True, col)], name=f"stat_num_{i + 1}")
        text_box(s, x + 0.3, 3.25, 3.35, 1.3, [(line, 18, False, INK) for line in lab.split("\n")], name=f"stat_label_{i + 1}")
    sdg_chip(s, 0.6, 5.1, "SDG 7", SDG7, w=1.1)
    sdg_chip(s, 1.85, 5.1, "SDG 13", SDG13, w=1.2)
    text_box(s, 3.25, 5.08, 9.4, 0.55, [("이 문제는 SDG 7(에너지 효율)과 SDG 13(기후행동)에 직결된다", 22, True, INK)],
             anchor=MSO_ANCHOR.MIDDLE, name="sdg_line")
    text_box(s, 0.6, 5.95, 12.0, 0.45, [[("TWh(테라와트시) ", 18, True, SDG13), ("= 10억 kWh.  ", 18, False, INK),
                                         ("GW·MW ", 18, True, SDG13), ("= 한 순간에 필요한 전력의 크기", 18, False, INK)]],
             name="term_line")
    footnote(s, "자료: IEA(2025) Energy and AI, p.14 / 산업통상자원부(2025) 제11차 전력수급기본계획 / 산업통상자원부(2023) 데이터센터 수도권 집중 완화 방안")

    # 3 탄소 곡선
    s = new()
    header(s, "한국 전기는 한낮에 가장 깨끗하고, 저녁에 가장 더럽다", "같은 1kWh라도 몇 시에 쓰느냐에 따라 탄소가 다르다", 3)
    picture(s, FIGS / "09_슬라이드3_탄소곡선_히트맵.png", FIG_X, FIG_Y, FIG_W, "figure")
    bullets(s, COL_X, 1.95, COL_W, 3.2, [
        [(f"{N['ci_min_h']}~{N['ci_min_h'] + 1}시", True), (f"가 가장 깨끗 ({N['ci_min']:.0f}{NB}g/kWh)", False)],
        [(f"{N['ci_max_h']}~{N['ci_max_h'] + 1}시", True), (f"가 가장 더러움 ({N['ci_max']:.0f}{NB}g/kWh)", False)],
        "2023년도 같은 모양, 태양광이 많은 봄 한낮이 특히 깨끗"])
    term_card(s, COL_X, 5.0, COL_W, 1.45, [("탄소집약도 ", "전기 1kWh를 만들 때 나오는 온실가스(g)")])
    footnote(s, "자료: 전력거래소 연료원별 시간대별 전력거래량(2025·2023년), IPCC AR5 생애주기 배출계수. 2025년 평균, g = gCO2eq")

    # 4 아이디어
    s = new()
    header(s, "아이디어: 빨래는 해 좋은 한낮에 널듯이", "미뤄도 되는 컴퓨터 일은 태양광이 많은 한낮에", 4)
    picture(s, FIGS / "05_탄소곡선_요금시간대.png", FIG_X, FIG_Y, FIG_W, "figure")
    bullets(s, COL_X, 1.95, COL_W, 3.3, [
        "백업·통계·모델 학습처럼 급하지 않은 일은 마감 안에서 옮길 수 있다",
        [("평일에 가장 싼 시간은 심야, 가장 깨끗한 시간은 한낮", True)],
        "정부도 2026년 개편에서 출력제어가 잦은 낮 시간 요금을 낮추기 시작했다"])
    term_card(s, COL_X, 4.95, COL_W, 1.5, [("경부하 ", "요금이 가장 싼 시간(22~8시)"),
                                           ("출력제어 ", "남는 태양광 발전을 멈추는 것")])
    footnote(s, "자료: 한전 기본공급약관 별표3, 기후에너지환경부·정책브리핑(2026.3.13, 4.14) 계절·시간대별 요금 개편")

    # 5 과목 매핑
    s = new()
    header(s, "이번 학기 전공 수업으로 풀었다", "과목별로 배운 개념이 스케줄러의 각 부분이 되었다", 5)
    rows = [("과목", "배운 개념", "이 프로젝트에서의 적용"),
            ("운영체제", "EDF·에이징·가능성 검사", "탄소 인지 스케줄러"),
            ("컴퓨터구조", "P ∝ CV²f, DVFS", "주파수별 에너지 모델"),
            ("클라우드네트워킹", "가상화·작업 이동", "시간 이동 구현"),
            ("확률과통계", "분포·예측", "예측 오차 3%p 측정")]
    tbl = s.shapes.add_table(len(rows), 3, Inches(0.6), Inches(1.95), Inches(12.1), Inches(4.2)).table
    for j, wdt in enumerate((3.2, 4.5, 4.4)):
        tbl.columns[j].width = Inches(wdt)
    for i, row in enumerate(rows):
        tbl.rows[i].height = Inches(0.84)
        for j, val in enumerate(row):
            cell = tbl.cell(i, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(INK if i == 0 else (LIGHT if j == 0 else WHITE))
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = Inches(0.25)
            tf = cell.text_frame
            tf.paragraphs[0].text = ""
            no_word_split(tf.paragraphs[0])
            r = tf.paragraphs[0].add_run()
            r.text = val
            style_run(r, 22 if i else 20, i == 0 or j == 0, WHITE if i == 0 else (SDG13 if j == 0 else INK))
    text_box(s, 0.6, 6.35, 12.1, 0.45, [("운영체제 개념이 설계의 뼈대, 컴퓨터구조가 전력 모델, 확률과통계가 검증을 맡았다", 18, False, INK2)],
             name="table_note")

    # 6 설계
    s = new()
    header(s, "스케줄러 설계: 탄소는 아끼고, 마감은 지킨다", "탄소만 쫓으면 마감을 놓친다. 그래서 15분마다 마감을 검사한다", 6)
    picture(s, FIGS / "06_스케줄러_흐름도.png", FIG_X, FIG_Y, FIG_W, "figure")
    bullets(s, COL_X, 1.95, COL_W, 3.4, [
        "탄소 비용 = 전력 × 시간 × 그 시간의 탄소집약도",
        [("마감 위반 0건은 15분마다 하는 가능성 검사 덕분", True), (f" (탄소만 쫓으면 1년 {N['B_late']:,}건 위반)", False)],
        "에이징: 오래 기다릴수록 기준을 넓혀 기아를 막는다. 절감률만 조절"])
    term_card(s, COL_X, 5.3, COL_W, 1.15, [("EDF ", "마감이 빠른 작업부터 처리하는 방식")])
    footnote(s, "가능성 검사(schedulability test): 지금 아무것도 안 돌려도 모든 작업을 마감 안에 끝낼 수 있는지 미리 따지는 것")

    # 7 결과
    s = new()
    header(s, f"결과: 스케줄링만으로 {N['C']:.1f}%", f"새벽 2시 일괄 실행보다 연간 {N['C']:.1f}% 적은 탄소, 마감 위반 0건", 7)
    picture(s, FIGS / "10_슬라이드7_간트_A_vs_C.png", FIG_X, FIG_Y, FIG_W, "figure")
    text_box(s, COL_X, 1.85, COL_W, 1.0, [(f"{N['C']:.1f}%", 60, True, SDG13)], name="big_number")
    text_box(s, COL_X, 2.9, COL_W, 0.4, [("연간 탄소 절감 · 마감 위반 0건", 18, True, INK)], name="big_number_label")
    bullets(s, COL_X, 3.5, COL_W, 2.4, [
        f"심야 2시 → 한낮: {N['night_noon']:.1f}% (봄{NB}{N['night_noon_spring']:.1f}%, 겨울{NB}{N['night_noon_winter']:.1f}%)",
        f"대가: 당일 작업 완료가 중앙값 {N['delay_A']:.1f}시간{NB}→{NB}{N['delay_C']:.1f}시간"])
    text_box(s, COL_X, 5.75, COL_W, 0.75, [(f"시장 밖 태양광을 월별 비율로 반영하면 약 {N['C_monthly']:.1f}%(가정)", 18, False, INK2)],
             name="range_note")
    footnote(s, f"가상 대학 서버 작업 30개 × 2025년 {N['days']}일 시뮬레이션, 전력시장 거래량 기준 탄소 곡선. 심야→한낮은 곡선 값 기준")

    # 8 핵심 발견
    s = new()
    header(s, "핵심 발견: 얼마나 기다릴 수 있느냐가 절감을 정한다", "마감 유연성이 절감을 결정한다", 8)
    picture(s, FIGS / "07_주말이동_비교.png", FIG_X, FIG_Y, FIG_W, "figure")
    bullets(s, COL_X, 1.95, COL_W, 4.6, [
        f"당일 마감 작업만 보면 {N['same_day']:.1f}%",
        [(f"주간 작업이 주말까지 못 기다리면 {N['C7']:.1f}%, 기다리면 {N['C']:.1f}%", True)],
        f"주말·공휴일 전기가 더 깨끗하다 (평균 {N['we']:.0f}{NB}g/kWh, 평일 {N['wd']:.0f}{NB}g/kWh)",
        ])
    text_box(s, COL_X, 5.35, COL_W, 1.1, [("독일 연구(Wiesner 외, 2021)도 주말로 옮기면 대부분 지역에서 20% 이상 절감", 18, False, INK2)],
             name="external_note")
    footnote(s, "자료: Wiesner et al.(2021) Let's Wait Awhile, Middleware '21. 같은 스케줄러(C)에서 주간 작업의 마감만 바꿔 비교")

    # 9 DVFS
    s = new()
    header(s, "더 줄일 수 있을까: 필요 이상으로 빠르게 돌리지 않기", "CPU 속도를 조금 낮추면 전체 절감이 커지지만, 크기는 가정에 달렸다", 9)
    picture(s, FIGS / "08_정책별_절감률_ACD.png", FIG_X, FIG_Y, FIG_W, "figure")
    bullets(s, COL_X, 1.95, COL_W, 3.2, [
        [("DVFS를 더하면 전체 절감이 ", False), (f"{N['D_lo']:.0f}~{N['D_hi']:.0f}%", True),
         (f", 기본 가정 {N['D']:.0f}%", False)],
        "메모리를 기다리는 작업은 속도를 0.6으로 낮춰도 실행 시간이 약 1.13배",
        f"헤드라인은 스케줄링만의 {N['C']:.1f}%로 둔다"])
    term_card(s, COL_X, 5.05, COL_W, 1.4, [("DVFS ", "급하지 않을 때 CPU 속도·전압을 낮춰 전기를 아끼는 기술")])
    footnote(s, f"정적 전력 비율 가정 {N['s_lo']}~{N['s_hi']}(기본 {N['static']}): SPECpower 2023~2026년 결과 중앙값, Barroso 외(2018, 2007). 메모리 바운드 비율 0.8 기준")

    # 10 SDG
    s = new()
    header(s, "SDG 타깃과 기대 효과", "설비를 새로 사지 않고, 운영 방식만 바꿔 기여한다", 10)
    sdgs = [("SDG 7.3", "에너지 효율 개선", "같은 일을 더 적은 탄소로,\nDVFS를 더하면 더 적은 에너지로", SDG7),
            ("SDG 9.4", "청정기술로 산업·인프라 개선", "소프트웨어만 바꿔 깨끗한 전기를\n더 많이 쓴다", SDG9),
            ("SDG 13.3", "기후 대응 역량·인식", "대학 서버 운영 관행을 바꾸는 사례.\n코드·데이터 공개로 누구나 재현", SDG13)]
    for i, (code, goal, body, col) in enumerate(sdgs):
        x = 0.6 + i * 4.1
        box(s, x, 1.95, 3.85, 2.85, "F4F7F5", name=f"sdg_card_{i + 1}")
        sdg_chip(s, x + 0.3, 2.2, code, col, w=1.6, h=0.55, size=20)
        text_box(s, x + 0.3, 2.95, 3.3, 0.5, [(goal, 20, True, INK)], name=f"sdg_goal_{i + 1}")
        text_box(s, x + 0.3, 3.55, 3.35, 1.5, [(line, 18, False, INK) for line in body.split("\n")], name=f"sdg_body_{i + 1}")
    text_box(s, 0.6, 5.2, 12.1, 0.5, [[("가상 대학 서버(작업 30개) 1년: ", 20, False, INK),
                                        (f"{N['emis_A']:,.1f} → {N['emis_C']:,.1f} kgCO2eq", 20, True, SDG13),
                                        ("  (새 설비 없이)", 20, False, INK)]], name="effect_line")
    text_box(s, 0.6, 5.85, 12.1, 0.45, [("구글도 2020년부터 실제 데이터센터에서 비슷한 방식을 쓰기 시작했다", 18, False, INK2)],
             name="google_line")
    footnote(s, "자료: 유엔 SDGs 세부 타깃(sdgs.un.org), Google 공식 블로그(2020.4.22), Radovanović et al.(2023) IEEE Trans. Power Systems")

    # 11 한계와 결론
    s = new(dark=True)
    header(s, "한계와 결론", "보수적으로 계산했고, 더 검증할 부분이 남아 있다", 11, dark=True)
    bullets(s, 0.6, 1.95, 12.1, 2.8, [
        f"시장 거래량 기준이라 시장 밖 태양광이 빠졌다. 반영하면 약 {N['C_monthly']:.1f}%(가정)",
        f"탄소 곡선을 미리 안다고 가정했다. 지난주 값으로 예측하면 {N['E_diff']:.1f}%p 줄어든다({N['C']:.1f}% → {N['E']:.1f}%)",
        "평균 배출계수를 썼고, 작업 세트는 가상이다. 실제 대학 서버 로그로 검증하는 것이 다음 과제"],
        size=20, color=WHITE, gap=16, bullet_color=SDG7)
    box(s, 0.6, 4.1, 12.1, 1.9, "2C3F3A", name="conclusion_box")
    text_box(s, 0.95, 4.25, 11.4, 1.6, [("언제 돌리느냐만 바꿔도 탄소는 줄고,", 28, True, SDG7),
                                         ("얼마나 기다릴 수 있느냐가 그 크기를 정한다", 28, True, SDG7)],
             anchor=MSO_ANCHOR.MIDDLE, name="conclusion")
    footnote(s, "평균 배출계수: 그 시각에 돌던 발전기 전체의 평균 탄소. 작업 하나 때문에 더 돌거나 덜 도는 발전기의 탄소와는 다를 수 있다", dark=True)

    for s, note in zip(slides, notes):
        s.notes_slide.notes_text_frame.text = note
    BUILD.mkdir(parents=True, exist_ok=True)
    out = BUILD / "deck_raw.pptx"
    prs.save(out)
    print(out)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    build()
