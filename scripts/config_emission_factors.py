"""연료원별 생애주기 배출계수 (gCO2eq/kWh = kgCO2eq/MWh = tCO2eq/GWh).

상태: 확정 (2026-11-06 사용자 승인).

출처 약어 (원문 위치는 02_데이터/references.md 2장)
  AR5    IPCC AR5 WG3 Annex III, Table A.III.2, "Lifecycle emissions (incl. albedo effect)" 중앙값
  SRREN  IPCC SRREN Annex II, Table A.II.4, 50번째 백분위(중앙값)

ASSUMED=True 인 항목은 IPCC 표에 해당 전원이 없어 비슷한 전원 값을 빌려 쓴 "가정"이다.
민감도 분석에서 이 항목들의 계수를 +-50% 바꿔 결과가 얼마나 흔들리는지 확인한다.

STORAGE 항목(양수, 전기저장장치)은 계수를 고정하지 않는다. 발전할 때 충전 당시 전력의 탄소를
넘겨받는다고 보고, 단순화해서 "저장장치를 뺀 나머지 전원의 연간 평균 탄소집약도"를 적용한다(가정).
"""

# 이름: (배출계수 또는 None, 출처, 가정 여부, 메모)
FACTORS: dict[str, tuple[float | None, str, bool, str]] = {
    # 석탄 계열
    "유연탄": (820, "AR5 Coal-PC", False, ""),
    "무연탄": (820, "AR5 Coal-PC", False, ""),
    "국내탄": (820, "AR5 Coal-PC", False, "현재 데이터에는 없음"),
    "부생가스": (820, "AR5 Coal-PC 대체", True, "제철 공정 부생가스, 석탄 대체값"),
    "IGCC": (820, "AR5 Coal-PC 대체", True, "석탄가스화복합발전, CCS 없음"),
    # 가스 계열
    "LNG": (490, "AR5 Gas-Combined Cycle", False, ""),
    "연료전지": (490, "AR5 Gas-Combined Cycle 대체", True, "LNG 개질 기반으로 가정"),
    # 유류 계열
    "중유": (840, "SRREN Oil", False, ""),
    "경유": (840, "SRREN Oil", False, ""),
    "등유": (840, "SRREN Oil", False, "현재 데이터에는 없음"),
    "LPG": (840, "SRREN Oil 대체", True, ""),
    # 무탄소/저탄소
    "원자력": (12, "AR5 Nuclear", False, ""),
    "수력": (24, "AR5 Hydropower", False, ""),
    "소수력": (24, "AR5 Hydropower", False, "기본 방침 외 항목, 사용자 확정"),
    "풍력": (11, "AR5 Wind onshore", False, ""),
    "태양광": (48, "AR5 Solar PV-utility", False, ""),
    "해양에너지": (17, "AR5 Ocean", False, ""),
    "지열": (38, "AR5 Geothermal", False, "현재 데이터에는 없음"),
    "급전가능 재생에너지": (48, "AR5 Solar PV-utility 대체", True, "구성 미상, 태양광으로 가정"),
    "가스압": (0, "연소 없음", True, "가스 감압 차압발전"),
    # 바이오/폐기물
    "바이오매스": (230, "AR5 Biomass-dedicated", False, ""),
    "바이오가스": (230, "AR5 Biomass-dedicated", False, ""),
    "목재펠릿": (230, "AR5 Biomass-dedicated", False, "현재 데이터에는 없음"),
    "폐기물": (230, "AR5 Biomass-dedicated 대체", True, "소각 폐기물에는 플라스틱 등 화석 유래 성분이 포함되어 실제 배출은 이보다 높을 수 있으나 비중 0.19%로 결과에 영향 없음"),
    "바이오중유": (230, "AR5 Biomass-dedicated 대체", True, "기본 방침 외 항목, 사용자 확정"),
    "바이오SRF": (230, "AR5 Biomass-dedicated 대체", True, "기본 방침 외 항목, 사용자 확정"),
    "매립가스": (230, "AR5 Biomass-dedicated 대체", True, "기본 방침 외 항목, 사용자 확정"),
    "바이오기타": (230, "AR5 Biomass-dedicated 대체", True, "15081098에만 있음, 이번 분석에는 미사용"),
    # 저장장치: 계수 None -> 연간 평균 적용
    "양수": (None, "연간 평균 탄소집약도", True, "STORAGE"),
    "전기저장장치(비중앙)": (None, "연간 평균 탄소집약도", True, "STORAGE"),
    # 구성 미상
    "기타": (None, "연간 평균 탄소집약도", True, "구성 미상, 결과에 중립인 연간 평균 적용(사용자 확정)"),
}

STORAGE_OR_NEUTRAL = [k for k, v in FACTORS.items() if v[0] is None]
ASSUMED = [k for k, v in FACTORS.items() if v[2]]

# 음수 거래량은 0으로 바꾸고 처리 행 수를 로그에 남긴다.
CLIP_NEGATIVE_TO_ZERO = True
