"""0단계: 공공데이터포털(data.go.kr) 파일데이터 원본 다운로드.

공공데이터포털 웹페이지의 [다운로드] 버튼과 같은 절차를 그대로 따른다.
  1) POST /tcs/dss/selectFileDataDownload.do  -> 첨부파일 ID 확인
  2) POST /cmm/cmm/check-limit.json           -> 다운로드 횟수 제한(캡차) 확인
  3) GET  /cmm/cmm/fileDownload.do             -> 원본 파일 저장
캡차가 요구되면 우회하지 않고 중단한다(README의 수동 다운로드 방법 참고).

[수동으로 받는 파일] 전력거래소 5분 단위 태양광(PPA·BTM 추정) 자료
  자동 다운로드 요청이 전력거래소 웹 방화벽에 차단되어(2026-11-06 확인) 이 스크립트는 받지 않는다.
  URL      https://www.kpx.or.kr/powerSource.es?mid=a10606030000&device=chart
  메뉴     전력거래소 홈페이지 > 부가메뉴 > 전력관련정보 > 발전원별 실시간 전력수급현황
  조회조건 전원 선택 없음. 오른쪽 위 기간(최대 31일)을 한 달씩 넣고 [엑셀다운로드]
  저장     02_데이터/raw/kpx_solar_5min/2025-01.xlsx ~ 2025-12.xlsx
  아래 main()은 이 파일 12개가 있는지 확인만 하고 없으면 안내를 출력한다.

사용법:  python scripts/00_download_data.py            (전체)
         python scripts/00_download_data.py 15127395   (특정 데이터셋만)
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import quote, unquote

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "02_데이터" / "raw"
META = RAW / "_meta"
BASE = "https://www.data.go.kr"
UA = "Mozilla/5.0 (ESD-contest data collection script)"

# (publicDataPk, 구분, 설명)
DATASETS = [
    ("15127395", "필수", "한국전력거래소_연료원별 시간대별 설비용량 및 전력거래량 (연간 갱신, 최신판)"),
    ("15081098", "필수", "한국전력거래소_연료원별 전력거래량 (2023년까지, 1회성)"),
    ("15065269", "선택", "한국전력거래소_지역별 시간별 태양광 및 풍력 발전량"),
    ("15065266", "선택", "한국전력거래소_시간별 전국 전력수요량"),
]


# 페이지의 "주기성 과거 데이터" 목록에서 과거 연도판도 받을 데이터셋
WITH_HISTORY = {"15127395"}


class NeedManualDownload(RuntimeError):
    pass


def page_buttons(sess: requests.Session, pk: str) -> list[tuple[str, str, str, str]]:
    """데이터셋 페이지에서 fn_fileDataDown(...) 인자를 읽는다."""
    html = sess.get(f"{BASE}/data/{pk}/fileData.do", timeout=60).text
    found = re.findall(
        r"fn_fileDataDown\('(\d+)',\s*'([^']+)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'\)", html
    )
    if not found:
        raise NeedManualDownload(f"{pk}: 다운로드 버튼을 찾지 못함(로그인/활용신청 필요 가능성)")
    # (detailPk, atchFileId, fileDetailSn, histSn) 중복 제거
    return list(dict.fromkeys((d, a, s, h) for _, d, a, s, h in found))


def history_buttons(sess: requests.Session, pk: str, detail_pk: str) -> list[tuple[str, str, str, str]]:
    """'주기성 과거 데이터' 목록의 각 과거판에 대해 CSV 다운로드 버튼 인자를 읽는다."""
    xhr = {"Referer": f"{BASE}/data/{pk}/fileData.do", "X-Requested-With": "XMLHttpRequest"}
    frag = sess.post(
        f"{BASE}/tcs/dss/selectHistAndCsvData.do",
        data={"publicDataPk": pk, "publicDataDetailPk": detail_pk},
        headers=xhr,
        timeout=60,
    ).text
    out = []
    for hist_pk, hist_sn in re.findall(r'data-public-pk="([^"]+)"\s*data-public-detail-sn="(\d+)"', frag):
        pop = sess.post(
            f"{BASE}/tcs/dss/selectDpkDetailInfo.do",
            data={"publicDataDetailPk": hist_pk, "publicDataHistSn": hist_sn},
            headers=xhr,
            timeout=60,
        ).text
        for d, a, sn, ext in re.findall(
            r"fn_fileDataDown\('\d+',\s*'([^']+)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'\)", pop
        ):
            if ext.lower() == "csv":
                out.append((d, a, sn, hist_sn))
    return out


def download(sess: requests.Session, pk: str) -> list[Path]:
    saved = []
    buttons = page_buttons(sess, pk)
    if pk in WITH_HISTORY:
        buttons += history_buttons(sess, pk, buttons[0][0])
    for detail_pk, atch, sn, _hist in buttons:
        ref = {"Referer": f"{BASE}/data/{pk}/fileData.do", "X-Requested-With": "XMLHttpRequest"}
        r = sess.post(
            f"{BASE}/tcs/dss/selectFileDataDownload.do",
            data={
                "publicDataDetailPk": detail_pk,
                "publicDataPk": pk,
                "atchFileId": atch,
                "fileDetailSn": sn,
                "publicDataTyCode": "PR0051",
            },
            headers=ref,
            timeout=60,
        )
        info = json.loads(r.text)
        if not info.get("status"):
            raise NeedManualDownload(f"{pk}: 다운로드 정보 요청 실패: {info.get('error')}")
        atch_id, file_sn = info["atchFileId"], info["fileDetailSn"]
        detail = info["dataSetFileDetailInfo"]
        data_nm = detail["publicDataSj"] if detail.get("publicDataTyDetailCode") == "DATY05" else detail["dataNm"]

        lim = sess.post(
            f"{BASE}/cmm/cmm/check-limit.json",
            data={"atchFileId": atch_id, "fileDetailSn": file_sn},
            headers=ref,
            timeout=60,
        ).json()
        if lim.get("needCaptcha"):
            raise NeedManualDownload(f"{pk}: 다운로드 횟수 제한으로 캡차 입력이 필요함")

        f = sess.get(
            f"{BASE}/cmm/cmm/fileDownload.do",
            params={"atchFileId": atch_id, "fileDetailSn": file_sn, "dataNm": data_nm},
            headers={"Referer": ref["Referer"]},
            timeout=300,
        )
        f.raise_for_status()
        cd = f.headers.get("Content-Disposition", "")
        m = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", cd)
        name = unquote(m.group(1)) if m else f"{data_nm}.csv"
        try:  # 일부 서버는 파일명을 latin-1로 인코딩해서 보낸다
            name = name.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
        name = re.sub(r'[\\/:*?"<>|]', "_", name)
        if len(f.content) < 200 and b"<html" in f.content.lower():
            raise NeedManualDownload(f"{pk}: 파일 대신 HTML 응답을 받음")
        out = RAW / name
        out.write_bytes(f.content)
        saved.append(out)

        META.mkdir(parents=True, exist_ok=True)
        keep = {k: v for k, v in detail.items() if v not in (None, "")}
        keep.update(
            {
                "_saved_file": name,
                "_downloaded_on": date.today().isoformat(),
                "_page_url": f"{BASE}/data/{pk}/fileData.do",
                "_bytes": len(f.content),
            }
        )
        meta_name = pk if detail_pk == buttons[0][0] else f"{pk}_{detail.get('stdrDe', detail_pk).replace('/', '-')}"
        (META / f"{meta_name}.json").write_text(json.dumps(keep, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] {pk} -> {name} ({len(f.content):,} bytes)")
        time.sleep(2)
    return saved


EPSIS_SOLAR_URL = "https://epsis.kpx.or.kr/epsisnew/selectEkgeEpsEstGrid.do?menuId=030400"
EPSIS_SOLAR_FILE = "EPSIS_태양광발전량추계_월별_030400.html"


def download_epsis_solar(sess: requests.Session) -> Path:
    """EPSIS 전력수급 > 추계정보(월별 태양광: 전력시장 참여 / 한전PPA / 자가용 추계). 로그인 불필요.
    표 값이 페이지 HTML 안에 들어 있어 페이지 원본을 그대로 저장한다(파싱은 분석 스크립트에서)."""
    r = sess.get(EPSIS_SOLAR_URL, timeout=60)
    r.raise_for_status()
    if "자가용태양광" not in r.text:
        raise NeedManualDownload("EPSIS 추계정보 페이지 구조가 바뀜")
    out = RAW / EPSIS_SOLAR_FILE
    out.write_bytes(r.content)
    META.mkdir(parents=True, exist_ok=True)
    (META / "EPSIS_030400.json").write_text(json.dumps({
        "name": "EPSIS 전력수급 > 추계정보 (태양광 발전량 월별: 전력시장 참여(실적), 한전PPA(실적), 자가용태양광(추계))",
        "provider": "한국전력거래소 전력통계정보시스템(EPSIS)", "_page_url": EPSIS_SOLAR_URL,
        "_saved_file": EPSIS_SOLAR_FILE, "_downloaded_on": date.today().isoformat(), "_bytes": len(r.content),
        "related_data_go_kr": "https://www.data.go.kr/data/15094989/fileData.do",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] EPSIS 030400 -> {EPSIS_SOLAR_FILE} ({len(r.content):,} bytes)")
    return out


def main(argv: list[str]) -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    want = set(argv[1:])
    sess = requests.Session()
    sess.headers["User-Agent"] = UA
    failed = []
    for pk, kind, desc in DATASETS:
        if want and pk not in want:
            continue
        print(f"--- [{kind}] {pk} {desc}")
        try:
            download(sess, pk)
        except NeedManualDownload as e:
            print(f"[수동 다운로드 필요] {e}\n    -> {BASE}/data/{pk}/fileData.do 에서 직접 받아 {RAW} 에 넣으세요.")
            failed.append(pk)
    if not want or "epsis" in want:
        print("--- [보조] EPSIS 태양광 발전량 추계(월별)")
        try:
            download_epsis_solar(sess)
        except (NeedManualDownload, requests.RequestException) as e:
            print(f"[수동 다운로드 필요] {e}")
            print(f"    -> {EPSIS_SOLAR_URL} 페이지를 '다른 이름으로 저장'(HTML)해 {RAW / EPSIS_SOLAR_FILE} 로 넣으세요.")
            failed.append("epsis")
    check_manual_kpx()
    return 1 if failed else 0


KPX_DIR = RAW / "kpx_solar_5min"
KPX_URL = "https://www.kpx.or.kr/powerSource.es?mid=a10606030000&device=chart"


def check_manual_kpx() -> None:
    """수동 다운로드 파일(전력거래소 5분 단위 태양광) 확인."""
    want = [KPX_DIR / f"2025-{m:02d}.xlsx" for m in range(1, 13)]
    missing = [p.name for p in want if not p.exists()]
    print("--- [수동] 전력거래소 발전원별 실시간 전력수급현황 5분 자료(2025년 12개월)")
    if not missing:
        print(f"[OK] {KPX_DIR} 에 12개 파일 있음")
        return
    print(f"[수동 다운로드 필요] 없는 파일 {len(missing)}개: {', '.join(missing)}")
    print(f"    -> {KPX_URL} 에서 오른쪽 위 기간을 한 달씩(최대 31일) 넣고 [엑셀다운로드],")
    print(f"       {KPX_DIR} 에 2025-MM.xlsx 이름으로 저장하세요. 없으면 시장 거래량 기준(A안)으로만 분석됩니다.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv))
