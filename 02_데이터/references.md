# 배경 통계와 참고문헌

원문 페이지나 PDF를 직접 열어 확인한 수치만 적는다. 인용문은 원문 그대로 옮겼다. 확인일은 모두 2026-11-06.

## 1. 데이터센터 전력 소비 (IEA "Energy and AI", 2025)

- 문헌: IEA (2025), *Energy and AI*, World Energy Outlook Special Report, IEA, Paris, 2025년 4월, CC BY 4.0
- 공식 페이지: https://www.iea.org/reports/energy-and-ai
- **EC 사이트 게재 PDF로 확인.** PPT에는 IEA 보고서 제목, 연도, 쪽수를 적는다.
- 확인 경위: iea.org 페이지는 자동 접속이 막혀(HTTP 403) 열지 못했다. 대신 보고서 PDF 전문(304쪽, 표지에 IEA 로고, 303쪽 판권면 "Typeset in France by IEA - April 2025")을 유럽연합 집행위원회 사이트 사본에서 열어 확인했다: https://build-up.ec.europa.eu/system/files/2025-04/PChtNmAZVk_11_04_2025_145800.pdf . 쪽수는 보고서에 인쇄된 번호.

| 항목 | 원문 인용 | 위치 |
|---|---|---|
| 2024년 소비량과 비중 | "Data centres accounted for around 1.5% of the world's electricity consumption in 2024, or 415 terawatt-hours (TWh)." | Executive Summary, p.14 |
| 2030년 전망 | "Data centre electricity consumption is set to more than double to around 945 TWh by 2030. This is slightly more than Japan's total electricity consumption today." | Executive Summary, p.14 |
| 2030년 비중 | "Global electricity consumption by data centres is projected to reach around 945 TWh by 2030 in the Base Case, representing just under 3% of total global electricity consumption in 2030." | Chapter 2, p.63 |
| 과거 증가율 | "Globally, data centre electricity consumption has grown by around 12% per year since 2017, more than four times faster than the rate of total electricity consumption." | Executive Summary, p.14 |
| 향후 증가율 | "From 2024 to 2030, data centre electricity consumption grows by around 15% per year, more than four times faster than the growth of total electricity consumption from all other sectors." | Chapter 2, p.63 |
| 국가별 비중 | "The United States accounted for the largest share of global data centre electricity consumption in 2024 (45%), followed by China (25%) and Europe (15%)." | Executive Summary, p.14 |
| AI 가속 서버 | "Electricity consumption in accelerated servers, which is mainly driven by AI technology adoption (Box 2.1), is projected to grow by 30% annually in the Base Case, while conventional server electricity consumption growth is slower at 9% per year." | Chapter 2, p.63 |
| AI 가속 서버 기여 | "Accelerated servers account for almost half of the net increase in global data centre electricity consumption, while conventional servers account for only around 20%." | Chapter 2, pp.63~64 |

- 참고: IEA가 2026년 4월 후속 자료("Key Questions on Energy and AI")를 냈다는 검색 결과가 있으나 원문을 확인하지 않았다. 2025년 보고서 수치와 섞어 쓰지 않는다.


## 2. 발전원별 생애주기 배출계수 (IPCC)

### 2-1. IPCC AR5 WG3 Annex III, Table A.III.2

- 문헌: IPCC (2014), Climate Change 2014: Mitigation of Climate Change, WG3 AR5, Annex III "Technology-specific Cost and Performance Parameters" (Schlömer et al.)
- URL: https://www.ipcc.ch/site/assets/uploads/2018/02/ipcc_wg3_ar5_annex-iii.pdf
- 위치: PDF 7쪽(인쇄 쪽수 1335), "Table A.III.2 | Emissions of selected electricity supply technologies (gCO2eq/kWh)"
- 아래 값은 "Lifecycle emissions (incl. albedo effect)" 열의 최소 / 중앙값 / 최대 (단위 gCO2eq/kWh)

| 발전원 (원문 표기, 대시는 하이픈으로 바꿈) | 최소 | 중앙값 | 최대 |
|---|---|---|---|
| Coal-PC | 740 | 820 | 910 |
| Gas-Combined Cycle | 410 | 490 | 650 |
| Biomass-cofiring | 620 | 740 | 890 |
| Biomass-dedicated | 130 | 230 | 420 |
| Geothermal | 6.0 | 38 | 79 |
| Hydropower | 1.0 | 24 | 2200 |
| Nuclear | 3.7 | 12 | 110 |
| Concentrated Solar Power | 8.8 | 27 | 63 |
| Solar PV-rooftop | 26 | 41 | 60 |
| Solar PV-utility | 18 | 48 | 180 |
| Wind onshore | 7.0 | 11 | 56 |
| Wind offshore | 8.0 | 12 | 35 |
| Ocean (상용화 이전 기술로 분류) | 5.6 | 17 | 28 |

- 이 표에는 석유(유류) 발전 행이 없다. 탄소포집(CCS) 결합 기술 4종도 표에 있으나 국내 거래 데이터에 해당 전원이 없어 생략했다.

### 2-2. 유류 발전: IPCC SRREN Annex II, Table A.II.4

- 문헌: IPCC (2011), Special Report on Renewable Energy Sources and Climate Change Mitigation (SRREN), Annex II "Methodology" (Moomaw et al.)
- URL: https://www.ipcc.ch/site/assets/uploads/2018/03/Annex-II-Methodology-1.pdf
- 위치: PDF 10쪽(인쇄 쪽수 982), "Table A.II.4 | Aggregated results of literature review of LCAs of GHG emissions from electricity generation technologies as displayed in Figure 9.8 (g CO2eq/kWh)."
- Oil 행: 최소 510, 25백분위 722, **중앙값 840**, 75백분위 907, 최대 1170
- 같은 표의 비교값(중앙값): Coal 1001, Natural Gas 469, Nuclear 16, Wind 12, Hydropower 4, Solar PV 46, Ocean 8
- 주의: 같은 Annex의 A.II.5.2절에 "LCA data for hydropower and oil were added at a later stage to the NREL database and have therefore undergone a less comprehensive literature collection process."라고 적혀 있다. 유류 값은 다른 전원보다 근거 문헌이 적다.
- AR5 WG3 Chapter 7(7.8.1절, https://www.ipcc.ch/site/assets/uploads/2018/02/ipcc_wg3_ar5_chapter7.pdf 인쇄 쪽수 538)도 같은 SRREN 범위를 그대로 인용한다: "Corresponding ranges for oil and gas were 510–1170 gCO2eq/kWh and 290–930 gCO2eq/kWh." AR5 자체의 유류 발전 배출계수는 없다.

## 3. 국내 데이터센터 전력 수요 (정부 공식 자료)

### 3-1. 제11차 전력수급기본계획 (산업통상자원부, 2025-02-21 확정)

- 문서: 「제11차 전력수급기본계획 주요내용」(보도자료 별첨), 3쪽 "3 전력수요"
- URL: https://www.motir.go.kr/attach/down/095a2dda9c864e1d90d751f7668a1117/fcb25bf4e6a063fd16f073fb33c181d7/13055e35ba7465cb478c5b4be490c5a8
- 원문 인용:
  - "(추가수요) 첨단산업(1.4), 데이터센터(4.4), 전기화(11.0) 등 16.7GW"
  - "(데이터센터) AI 확산에 따른 대규모 데이터 처리능력 필요, 이로 인한 데이터센터 전력수요 확대 전망 반영"
  - "10차 대비 데이터센터 전력수요 전망 증가 (10차 '36년 1.4GW → 11차 '38년 4.4GW)"
  - "'38년 데이터센터 전력수요 6.2GW = 모형수요(추세) 1.8GW + 추가수요(증분) 4.4GW"
  - "'38년 목표수요는 129.3GW 전망 ('24~'38년 연평균 1.8% 증가)"
- 같은 쪽 기준수요 표의 데이터센터 추가수요(GW): 2025년 0.5, 2030년 2.3, 2036년 3.9, 2038년 4.4
- 보도자료 「｢제11차 전력수급기본계획｣ 확정」(산업통상자원부 전력산업정책과, 2025-02-21): https://www.motir.go.kr/kor/article/ATCL3f49a5a8c/170183/view
  - "추가수요에는 용인 반도체 클러스터 등 첨단산업, AI 확산에 따른 데이터센터 확대, 산업·수송·수소 등 전기화의 영향이 반영되었다."
  - "기준수요는 모형수요와 추가수요를 합산하여 산정되었으며, '38년 145.6GW로 전망된다."

### 3-2. 데이터센터 수도권 집중 완화 방안 (산업통상자원부, 2023-03-09)

- 문서: 제18회 국정현안관계장관회의 안건 「데이터센터 수도권 집중 완화 방안」(보도자료 별첨) 1쪽
- URL(별첨): https://www.motir.go.kr/attach/down/095a2dda9c864e1d90d751f7668a1117/f44086d3d46f975295d5c584675b08ec/778bdbf5db9ced7c8fd52756c00bf0cd
- URL(보도자료): https://www.motir.go.kr/attach/down/095a2dda9c864e1d90d751f7668a1117/f44086d3d46f975295d5c584675b08ec/13055e35ba7465cb478c5b4be490c5a8
- 원문 인용:
  - "'22.12월 기준 국내 147개의 데이터센터 전력수요는 1,762MW, 향후 '29년까지 신규 데이터센터 전력수요는 총 732개, 49,397MW 전망"
  - "데이터센터 입지의 60%, 전력수요의 70%가 수도권에 집중, 이 비율은 '29년까지 80%대로 확대 예상"
  - 표: 신규 49,397MW 중 수도권 39,802MW(80.6%), 601개
  - 보도자료 내 차관 발언: "데이터센터는 디지털경제의 핵심이나, 수도권 집중이 심화됨에 따라 송·배전망 등 전력 인프라 추가 건설이 부담되고, 계통 혼잡 발생이 우려되는 상황"
- 해석 주의: 49,397MW는 신규 데이터센터의 전력 공급 요청 규모를 모은 값이다. 전부 지어진다는 예측이 아니다.

### 3-3. 전력계통영향평가 (산업통상자원부 보도설명자료, 2024-08-12)

- URL: https://www.motir.go.kr/attach/down/095a2dda9c864e1d90d751f7668a1117/5e607e5da1f16e16ee99a05a0768bd5a
- 원문 인용: "전력계통영향평가는 데이터센터뿐만 아니라 공장, 상가 등 10MW 이상 대규모 전력사용시설을 대상으로 사전에 전력계통 여유 등을 검토하도록 하여 수도권에 집중된 전력수요를 분산하고, 전력공급의 안정성, 예측가능성을 높이기 위해 도입되었습니다."
- 참고: 문서 이미지는 산업통상자원부(전력계통혁신과) 명의이나 PDF 텍스트 정보에는 다른 기관명이 남아 있다. 인용할 때는 산업통상자원부로 적는다.

### 3-4. [2차 출처, 자료 인용 보류] 제12차 전력수급기본계획 실무안 보도

- 공식 문서는 아직 없고 뉴스만 확인됨. 발표 자료에 쓰려면 승인 필요.
- 메트로신문, 2026-08-20: https://www.metroseoul.co.kr/article/20260820500464
  - "새로 제시된 2040년 연중 최대 전력수요 전망치는 158.4~165.0GW(목표수요 기준)로"
  - "AI 데이터센터에서 7.9GW의 수요가 추가 반영됐다."


## 4. 탄소 인지 컴퓨팅 운영 사례

### 4-1. Google: 시간 이동 (2020)

- 글: "Our data centers now work harder when the sun shines and wind blows", Ana Radovanovic (Google), Google 공식 블로그, 2020-04-22
- URL: https://blog.google/inside-google/infrastructure/data-centers-work-harder-sun-shines-wind-blows/
- 원문 인용(페이지 원문과 문자열 대조 완료):
  - 옮기는 작업: "non-urgent compute tasks", 예: "creating new filter features on Google Photos, YouTube video processing, or adding new words to Google Translate"
  - 방법: "our carbon-intelligent platform compares two types of forecasts for the following day", 이를 바탕으로 "optimize hour-by-hour guidelines to align compute tasks with times of low-carbon electricity supply"
  - 범위: 첫 버전은 "focuses on shifting tasks to different times of the day, within the same data center", 향후 "Our plan for the future is to shift load in both time and location"
  - 결과: "Early results demonstrate carbon-aware load shifting works", "by shifting compute jobs we can increase the amount of lower-carbon energy we consume" (정량 수치 없음)

### 4-2. Google: 장소 이동 (2021)

- 글: "We now do more computing where there's cleaner energy", Ross Koningstein (Google), 2021-05-18
- URL: https://blog.google/outreach-initiatives/sustainability/carbon-aware-computing-location/
- 원문 인용(문자열 대조 완료): "shift moveable compute tasks between different data centers", "favoring regions where there's more carbon-free electricity", "as much energy consumption as possible to times and places where energy is cleaner" (정량 수치 없음)

### 4-3. Google 논문 (동료 심사)

- Radovanović, A. et al., "Carbon-Aware Computing for Datacenters", *IEEE Transactions on Power Systems*, 38(2), 1270-1280, 2023. DOI: 10.1109/TPWRS.2022.3173250 (서지 정보는 Crossref로 확인)
- 원문 확인: arXiv 사전 공개본 https://arxiv.org/abs/2106.11750
- 초록 인용: "This paper introduces Google's system for Carbon-Intelligent Compute Management, which actively minimizes electricity-based carbon footprint and power infrastructure costs by delaying temporally flexible workloads."
- 초록 인용: "VCCs impose hourly limits on resources available to temporally flexible workloads while preserving overall daily capacity, enabling all such workloads to complete within a day."
- 정량 결과(본문 결론): "Using actual measurements from Google datacenter clusters, we demonstrate a power consumption drop of 1-2% at times with the highest carbon intensity."
- 해석 주의: 탄소 배출 총 절감률은 논문에 없다. 1~2%는 탄소집약도가 가장 높은 시간대의 클러스터 전력 감소폭이다.

### 4-4. 시간 이동 효과 분석 논문 (동료 심사)

- Wiesner, P., Behnke, I., Scheinert, D., Gontarska, K., Thamsen, L., "Let's Wait Awhile: How Temporal Workload Shifting Can Reduce Carbon Emissions in the Cloud", *Middleware '21*, ACM, 260-272, 2021. DOI: 10.1145/3464298.3493399
- 원문 확인: arXiv 사전 공개본 https://arxiv.org/abs/2110.13234 (독일, 영국, 프랑스, 캘리포니아의 2020년 전력 데이터로 분석)
- 원문 인용(결론): "shifting workloads whose results are not needed by the next working day can already reduce emissions by over 5 % across all regions."
- 원문 인용(결론): "shifting delay-tolerant workloads towards weekends can result in more than 20 % savings in most regions."
- 원문 인용(5.1.2절): "in France and Great Britain we can already achieve savings of 3.0 % and 4.3 %, respectively, when increasing the flexibility window by only ±2 hours", "the German scenario emits 11.2 % less carbon for the ±8 hour experiment."
- 해석 주의: 실제 운영 결과가 아니라 전력 데이터 기반 시뮬레이션이다. 우리 프로젝트와 같은 방식이므로 결과 비교 기준으로 쓰기 좋다.

### 4-5. Microsoft Windows Update

- 페이지: "Windows Update is now carbon aware", Microsoft Support (게시일 표기 없음, Windows 11 22H2 이상 적용)
- URL: https://support.microsoft.com/en-us/windows/deployment/updates-lifecycle/windows-update-is-now-carbon-aware
- 원문 인용(문자열 대조 완료): 설치 시각 조정 조건 "When devices are plugged in, turned on, connected to the internet and regional carbon intensity data is available"
- 정량 절감 수치 없음.

### 정리

- 기업이 실제 운영에서 측정해 공개한 수치는 Google 논문의 "탄소가 가장 많은 시간대 전력 1~2% 감소"뿐이다.
- 더 큰 절감률(5%, 11.2%, 20% 이상)은 Wiesner et al.의 시뮬레이션 결과다.


## 5. 한전 계시별 요금제의 경부하 시간대 (요금이 싼 시간)

### 5-1. 한전 기본공급약관 별표3 "계절별·시간대별 구분표"

- URL: https://cyber.kepco.co.kr/ckepco/front/jsp/CY/D/C/CYDCHP00403.jsp (한전 사이버지점, 페이지 인코딩 cp949)
- 적용 종별: "일반용전력(갑)Ⅱ, 산업용전력(갑)Ⅱ, 일반용전력(을), 산업용전력(을), 교육용전력(을)"
- 표(원문): 경부하시간대는 여름철(6월 1일~8월 31일), 봄·가을철(3월 1일~5월 31일, 9월 1일~10월 31일), 겨울철(11월 1일~익년 2월 말일) 모두 "22:00~08:00"
  - 중간부하: 여름·봄·가을 "08:00~11:00 12:00~13:00 18:00~22:00", 겨울 "08:00~09:00 12:00~16:00 19:00~22:00"
  - 최대부하: 여름·봄·가을 "11:00~12:00 13:00~18:00", 겨울 "09:00~12:00 16:00~19:00"
- 원문 인용: "공휴일의 최대수요전력 및 사용전력량은 경부하시간대로 계량하고, 공휴일이 아닌 토요일 최대부하시간대의 사용전력량은 중간부하시간대로 계량합니다."
- 원문 인용: "공휴일이라 함은 "관공서의 공휴일에 관한 규정"에 정한 공휴일을 말합니다. 이 경우 정부에서 수시로 지정하는 임시공휴일은 제외합니다."
- 주의: 이 페이지는 2026년 개편 전 표다(부칙 2022.9). 2025년 데이터를 쓰는 이 프로젝트 기간에는 이 표가 적용됐다.

### 5-2. 2026년 계절·시간대별 요금 개편 (기후에너지환경부, 정부 공식 페이지)

- 정책뉴스 2026-03-13 "4월 16일부터 밤 시간엔 5.1원 인상…'계절·시간대별 전기요금 개편안' 공개": https://www.korea.kr/news/policyNewsView.do?newsId=148960823
  - "먼저 낮 시간대로 요금이 가장 높았던 오전 11시~12시와 오후 1시~3시 구간을 중간요금(중간부하)으로 조정하는 대신, 화석연료 발전 가동이 증가되는 저녁 6시~9시는 중간요금에서 최고요금(최대부하)으로 변경" (인용은 페이지 문장 앞부분)
  - "또한 최저요금(경부하, 주로 밤)은 kWh당 5.1원 인상하고, 최고요금은 여름·겨울철 16.9원 인하하고 봄·가을철에는 13.2원 인하하는 등 평균 15.4원 인하한다."
- 정책뉴스 2026-04-14: https://www.korea.kr/news/policyNewsView.do?newsId=148962675
  - "앞으로 평일 오전 11시~오후 3시에 적용되던 최고요금(최대부하)이 중간요금(중간부하)으로, 저녁 6시~9시였던 중간요금은 최고요금으로 변경된다."
- 부처 브리핑 2026-04-16: https://www.korea.kr/briefing/policyBriefingView.do?newsId=156755866
  - "개편안의 핵심은 낮 시간대로 전력 소비를 유인하는 것입니다."
  - "금번에 시행된 산업용(을) 이외에 일반용·교육용 등 시간대별 요금이 적용되는 다른 종별에 대해서는 6월 1일부터 적용할 예정입니다."
- 정리: 개편 후에도 경부하는 22:00~08:00로 그대로이고, 새벽 2시는 개편 전후 모든 계절 경부하다. 개편은 봄·여름·가을 평일의 중간·최대부하 구간만 바꿨다(겨울 미변경). 원문 보도참고자료(붙임 표)는 정부 사이트에서 원본을 찾지 못해 인용하지 않았다.

### 발표 메시지와의 연결

- 요금이 가장 싼 시간(경부하, 22~08시)과 탄소가 가장 적은 시간(1단계 분석: 한낮 10~14시)이 다르다.
- 정부도 2026년 개편에서 "낮 시간대로 전력 소비를 유인"하고, 저녁 18~21시를 "화석연료 발전 가동이 증가되는" 시간으로 보고 최고요금으로 바꿨다. 1단계에서 저녁 19~23시가 가장 탄소가 많았던 결과와 방향이 같다.
