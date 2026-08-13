# Simpson–Taflove 2004 최종 검증 보고서

> 최종 정량 판정: **FAIL**

프로덕션 재실행은 2026-08-06(Asia/Seoul)에 완료했다.

영문 원본: [English](simpson-taflove-2004.md).

## 요약

이 연구에서는 현재의 측지 FDTD 구현이 Simpson과 Taflove(2004)의 Figure 7 시간 영역 수신 파형과 Figure 8 주파수별 감쇠를 재현하는지 시험했다. 검토한 구현은 예상되는 음의 주 펄스와 그 뒤의 오버슈트, 느린 꼬리를 재현하지만 전체 50–500 Hz 대역에서 논문의 엄격한 지점별 감쇠 허용 오차는 만족하지 못한다.

기준 비교에는 완전한 35,000-step 수신 트레이스와, 논문에 명시되지 않은 NOAA-NGDC Global Relief CD-ROM 입력을 당시 자료인 ETOPO5로 복원한 모델을 사용한다. ETOPO5가 저자들이 선택한 정확한 원자료라고 단정할 수는 없다. 재실행 결과 동서 비대칭이 뚜렷하게 복원되었고 논문의 시간 범위를 따랐다. 음의 주 펄스, 양의 오버슈트, 지속적인 느린 꼬리를 재현했지만 동/서 피크의 상대 순서와 분리는 출판된 패널과 일치하지 않는다.

Figure 8에서 동일한 트레이스로 계산한 평균 절대 감쇠 오차는 A–B에서 1.104 dB/Mm, A′–B′에서 0.242 dB/Mm이다. 최대 절대 오차는 각각 457.764 Hz에서 2.538 dB/Mm, 488.281 Hz에서 3.258 dB/Mm이다. 두 최댓값 모두 논문이 보고한 A–B ±0.5 dB/Mm 및 A′–B′ ±1.0 dB/Mm 범위를 넘는다.

| 검증 대상 | 합격 기준 | 현재 결과 | 판정 |
|---|---|---|---:|
| Figure 7 전체 시간 범위 | 출판 플롯이 약 35,000 steps까지 이어짐 | Samples 0–35,000 | **PASS** |
| Figure 7 파형 형태 | 음의 주 펄스, 양의 오버슈트, 느린 꼬리 | 세 특징 모두 재현 | **PASS** |
| Figure 7 도달 순서 | A/A′가 B/B′보다 먼저 도달 | 7,491/7,721 대 14,803/14,667 steps | **PASS** |
| Figure 7 동서 비동일성 | 두 수신기 쌍이 눈에 띄게 다름 | 상대 RMS 37.90%/30.46% | **PASS** |
| Figure 7 수신기 쌍 상대 진폭 | 동/서 피크 순서와 시각적 분리가 일치 | 두 피크 순서가 모두 반대이며 B′가 B보다 32.4% 큼 | **FAIL** |
| Figure 7 정확한 플롯 재현 | 시간 범위, 형태, 상대 트레이스가 일치 | 형태는 일치하나 상대 트레이스는 불일치 | **FAIL** |
| Figure 8 A–B 감쇠 | 지점별 잔차가 ±0.5 dB/Mm 이내 | 최대 2.538 dB/Mm | **FAIL** |
| Figure 8 A′–B′ 감쇠 | 지점별 잔차가 ±1.0 dB/Mm 이내 | 최대 3.258 dB/Mm | **FAIL** |
| Figures 7–8 전체 재현 | 적용 가능한 모든 기준 통과 | 형태는 통과, 정량 결과는 실패 | **FAIL** |

### 이전 고정 깊이 프로덕션 결과 대비 변화

| 지표 | 고정 깊이, 25,023 steps | ETOPO5, 35,000 steps | 변화 |
|---|---:|---:|---:|
| A/A′ 상대 RMS | 0.545% | 37.895% | 필요한 비대칭이 복원됐지만 과도함 |
| B/B′ 상대 RMS | 0.463% | 30.458% | 필요한 비대칭이 복원됐지만 과도함 |
| A / A′ 피크 step | 7,490 / 7,491 | 7,491 / 7,721 | 거의 겹치던 피크가 230 steps 분리됨 |
| B / B′ 피크 step | 14,449 / 14,450 | 14,803 / 14,667 | 거의 겹치던 피크가 136 steps 분리됨 |
| A–B 감쇠 MAE / 최대 | 0.310 / 2.384 dB/Mm | 1.104 / 2.538 dB/Mm | 악화 |
| A′–B′ 감쇠 MAE / 최대 | 0.286 / 1.092 dB/Mm | 0.242 / 3.258 dB/Mm | 평균은 개선, 최대는 악화 |
| 프로덕션 실행 시간 | 2,002.5 s | 2,677.5 s | steps가 40% 늘고 시간은 33.7% 증가 |

완전한 시간축과 물질에서 비롯한 비대칭은 Figure 7의 실질적인 개선이다. 동시에 복원한 지형과 대표 전도도 프로파일이 수신기 쌍을 지나치게 분리하고 출판된 피크 순서를 반대로 만든다는 점도 드러났다. Figure 8의 전체 판정은 여전히 실패다. 서쪽 경로의 평균은 개선됐지만 두 지점별 최댓값 모두 허용 범위를 벗어난다.

조사해 보니 부동소수점 정밀도, FFT zero-padding, DFT 절단 지점 선택, source-plane 반올림은 주원인이 아니었다. 균일 모델과 방위각 연구에서 공간 분산은 실제로 존재하며 수렴한다. Subdivision 8에서는 평가 대역의 방향 비등방성이 0.0867% 이하로 작다. 남은 절대 잔차에는 등방성 공간 분산과 유한 방사·지각 모델의 차이도 함께 들어 있다.

새 CUDA `float64` 물리 진단으로 Figure 7의 물질 관련 불일치 범위를 더 좁혔다. PyTorch backend, compilation, 진단 기록, 비유한 필드, 동쪽 경로 전체의 더 큰 전도 손실은 원인에서 제외했다. Subdivision 5에서 비정상적으로 약한 B 트레이스는 하나의 수신점 지지 셀에서 발생했다. 정확한 B 좌표는 ETOPO5 기준 해수면 아래 207 m지만, 이 셀의 표면은 해수면 위 30 m다. 원인 분리 목적으로 양의 지형고도만 0으로 제한하자 B/B′ 쌍이 복원됐다. 조격자의 해안선에서 수평·수직 물질 aliasing이 일어난다. 이 결과는 실제 지형을 없애야 한다는 뜻이 아니라 보존적인 물질 적분을 시험해야 한다는 근거다. 이에 dual-cell 면적 평균을 구현하여 subdivisions 5와 8에서 검증했다. 점 표본 민감도는 줄었지만 level-5 B 수신값은 복원되지 않았고 level-8 A–B 최대 감쇠 오차는 2.538에서 5.339 dB/Mm로 악화됐다. Subdivision-8 B 지지점은 보간 가중치 기준으로 이미 88.9%가 해양이므로, 해안선 aliasing은 최종 고주파 Figure 8 잔차의 주원인이 아니다.

방사와 시간 간격을 함께 세분화해 5 km 방사 간격의 영향을 수평 분산과 분리했다. 시간 간격만 절반으로 줄였을 때 균일 level-5 평균 위상속도 오차는 `5.05e-8 c`만 변하므로 시간 적분 오차는 원인에서 제외할 수 있다. 방사 간격을 절반으로 줄인 결과는 일관되지 않았다. Subdivision 5에서는 평균 오차가 5.2% 줄었지만 subdivision 6에서는 8.5% 늘었다. 반면 수평 격자를 subdivision 5에서 6으로 세분화하면 평균 오차가 5 km 방사 격자에서 53.3%, 2.5 km 격자에서 46.5% 감소한다. 비용이 큰 level-8 방사 세분화는 선별 기준을 통과하지 못해 실행하지 않았다. 이 결과에 따라 더 작은 시간 간격이나 균일 방사 세분화 대신 수평 세분화를 다음 선별 실험으로 정했다.

수평 level 7과 8을 직접 실행한 결과, 평균 방위각 spread는 0.1157%에서 0.02422%로 줄어 약 2차 방향 수렴을 확인했다. 그러나 Bannister MAE는 0.01870 c에서 0.01418 c로 더 느리게 감소했다. 세 격자 외삽은 level-9 MAE를 0.01294 c, 수평 연속격자 극한을 0.01247 c로 예측한다. Level 9는 상주 배열의 이론적 하한만 13.40 GiB여서 설치된 12 GiB GPU에 들어가지 않는다. Level-8 실측 피크로부터 예상한 필요량은 약 21.3 GiB다. 격자 세분화는 방향 오차와 위상 불일치를 일부 줄이는 데 효과가 있지만 논문과의 불일치 전체를 설명할 근거는 아직 없다.

같은 revision의 subdivision-8에서 Mesquite ETOPO5 대조 실험을 실행해 지형 voxel 효과를 따로 확인했다. Mesquite 좌표에서는 약한 B 피크의 크기가 11.5% 커지고 1/2 경로의 동서 RMS 차이가 30.46%에서 21.20%로 줄었다. A–B 감쇠 MAE와 최댓값도 각각 17.2%와 13.3% 감소했다. 그러나 A′–B′ 값은 각각 1.9%와 2.9% 악화됐다. 두 그림 모두 합격 기준을 충족하지 못했고 두 동서 피크 크기의 순서도 여전히 반대다. 최적화 좌표는 프로덕션 결과에 적용하지 않고 재현 가능한 대조 조건으로 남긴다.

## 범위와 합격 기준

대상 연구는 다음과 같다.

J. J. Simpson and A. Taflove, “Three-dimensional FDTD modeling of impulsive ELF propagation about the entire Earth-sphere,” *IEEE Transactions on Antennas and Propagation*, 52(2), 443–451, 2004, [doi:10.1109/TAP.2004.823953](https://doi.org/10.1109/TAP.2004.823953).

검증 범위는 다음과 같다.

- A, A′, B, B′에서의 Figure 7 파형 형태와 수신 도달 거동
- A–B 및 A′–B′ 스펙트럼 비로 계산한 Figure 8 감쇠
- 횡방향으로 균일한 모델에서의 위상 속도와 도달 시간 수렴
- 정밀도, FFT 길이, DFT 절단, 표면 기복, 지각 프로파일, 소스 stagger, 수평 격자 방향에 대한 민감도
- 표면 셀 40,962개부터 655,362개까지인 subdivisions 6–8

엄격한 정량 판정은 Figure 8의 지점별 잔차를 기준으로 한다.

| 경로 | 평가 주파수에서 요구되는 일치 범위 |
|---|---:|
| A–B | ±0.5 dB/Mm 이내 |
| A′–B′ | ±1.0 dB/Mm 이내 |

논문이 소스 전류 진폭을 명시하지 않으므로 Figure 7은 정성적으로 평가한다. 계산 트레이스에는 1 A 정규화를 사용하며 스펙트럼 감쇠 비는 이 진폭에 의존하지 않는다.

## 기준 방정식과 평가 주파수

Figure 8의 “Previous Results” 곡선은 P. R. Bannister, “ELF Propagation Update,” *IEEE Journal of Oceanic Engineering*, OE-9(3), 179–188, 1984, [doi:10.1109/JOE.1984.1145609](https://doi.org/10.1109/JOE.1984.1145609)의 주간 모델이다.

최종 감쇠 기준은 `H = 70 km`, `ξ₀ = ξ₁ = 1 / 0.3 km`로 Bannister 식 (5), (7), (8)을 평가한다. 그 결과 Bannister가 보고한 것처럼 약 75 Hz에서 1.5 dB/Mm, 1000 Hz에서 16.6 dB/Mm가 나온다. 이전에 수동 피팅한 `0.0265 f^0.938` 곡선은 과거 맥락으로만 남기며 최종 판정에는 사용하지 않는다.

비교에는 `Δt = 3 μs`인 논문 호환 32,768-point DFT의 bins 5–49, 즉 50.862630–498.453776 Hz의 고정 주파수 45개를 사용한다. 65,536-point zero-padded 변환 결과도 같은 주파수로 재표본화한다. 위상 속도는 Bannister 식 (4)와 비교한다.

## 시뮬레이션 구성

| 항목 | 값 |
|---|---:|
| 방사 영역 | 해수면 기준 −100~+100 km |
| 방사 셀 | 5 km 간격 40개 |
| 시간 간격 | 3.0 μs |
| 프로덕션 steps / samples | 35,000 / 35,001 |
| 소스 위치 | 적도, 47° W |
| 소스 길이 | 5 km 수직 전류 요소 |
| 소스 중심 | 2.5 km, 0과 5 km `Er` 평면 사이 선형 stagger |
| Gaussian `1/e` 전체 폭 | `480 Δt` |
| Gaussian 중심 | `960 Δt` |
| A / A′ 거리 | 소스에서 동 / 서로 45° |
| B / B′ 거리 | 소스에서 동 / 서로 90° |
| 전리층 기준 높이 | 70 km |
| 전리층 scale height | `1/0.3 km` (3.333… km) |
| 표면 격자 | subdivision 8, polar orientation, 655,362 cells |
| 물질 | ETOPO5 기복 복원 + Figure 6 해양/대륙 프로파일 |
| 심부 암석권 비저항 | 500 Ω·m |
| DFT window | 오버슈트 뒤 적응형 zero crossing |
| 프로덕션 backend | CUDA의 PyTorch compiled update |
| 프로덕션 정밀도 | float64 |
| ETOPO5 SHA-256 | `471d3dd534144aa9a6551fe3e76320a06a45dade6fd8d45f7d6ad981d59f93c3` |
| 프로덕션 구현 revision | `ec9583a` |
| 트레이스 SHA-256 | `147b4756b11c25f11b63825a381afe9fc17e747dbc2a33910c7a36060946d5e1` |
| 실행 시간 | 2,677.5 s |

표면 셀 수는 subdivisions 6, 7, 8에서 각각 40,962, 163,842, 655,362개이다. Subdivision 7은 논문의 방사 평면당 163,842개 셀과 일치한다.

## 수신점 배치

요청한 수신점은 서경 47°의 소스를 기준으로 동쪽과 서쪽 45° 및 90°에 해당하는 적도 위에 놓인다. 셀을 식별할 수 있도록 같은 polar orientation과 recursive dual-grid 구조를 지닌 subdivision 4 격자 위에 정확한 좌표를 표시했다. 프로덕션 subdivision 8 격자는 셀이 655,362개여서 이 축척에서는 내부가 채워진 것처럼 보인다. 마커는 표시용 격자의 셀 중심으로 옮기지 않았다.

![측지 dual grid 위의 소스와 수신점](images/simpson-taflove-2004-receiver-grid.png)

## 출판 플롯 비교

아래 왼쪽 패널은 [저자 제공 논문 PDF](https://my.ece.utah.edu/~simpson/Papers/Paper2.pdf)의 450쪽에서 잘라냈다. 출판 패널의 저작권은 © 2004 IEEE에 있으며 출처를 밝힌 기술 비교 목적으로 인용했다. 오른쪽 패널은 인용문헌 23의 심부 암석값과 인용문헌 24의 전리층 프로파일을 명시적으로 적용한 2026-08-06 subdivision-8 CUDA `float64` ETOPO5 수신 트레이스에서 현재 분석 코드로 다시 생성했다. Figure 8 재현에는 더 이상 쓰지 않는 plot-fit 기준이 아니라 Bannister의 원 방정식과 최종 고정 비교 주파수를 사용했다.

![출판된 Figure 7과 재현한 Figure 7 시간 응답](images/simpson-taflove-2004-fig-7-comparison.png)

재현한 Figure 7 파형은 출판 플롯과 같은 주된 순서, 즉 도달 전 정적 구간, 날카로운 음의 주 펄스, 양의 오버슈트, 전체 35,000-step 축에 걸쳐 감소하는 느린 꼬리를 보인다. Level-8 음의 피크는 A/A′에서 7,491/7,721 steps, B/B′에서 14,803/14,667 steps에 발생한다. Step 35,000에서도 각각 −0.02408/−0.02560 μV/m 및 −0.03277/−0.03189 μV/m로 음수이며 상대 스케일링 후 꼬리 크기는 출판 패널과 비슷하다. 논문이 소스 전류 진폭을 밝히지 않았으므로 절대 진폭은 합격 기준이 아니며 재현에는 1 A 정규화를 사용한다.

ETOPO5는 사라졌던 동서 분리를 복원하지만 정량적인 양상은 맞지 않는다. 재현한 서쪽 피크는 1/4 경로와 1/2 경로에서 동쪽 피크보다 각각 3.7%, 32.4% 더 크지만, 출판 플롯에서는 실선 동쪽 곡선이 점선 서쪽 곡선보다 육안상 약간 더 깊다. Figure 7은 정성적 형태는 통과하지만 정확한 플롯 재현은 실패다.

![출판된 Figure 8과 재현한 Figure 8 감쇠 곡선](images/simpson-taflove-2004-fig-8-comparison.png)

재현한 Figure 8 점들은 전체 감쇠 추세를 따르지만 ETOPO5 동쪽 경로는 Bannister 주간 곡선보다 체계적으로 감쇠가 크다. 상위 대역 진동으로 인해 subdivision-8의 최종 최대 잔차는 2.538 및 3.258 dB/Mm이다. 나란히 배치한 플롯도 스칼라 지표와 같은 결론을 뒷받침한다. 두 엄격한 지점별 기준 모두 실패다.

## 조사 이력

### 기준 실행과 정밀도 점검

초기 level-7 Apple MPS `float32` 실행은 이전의 74 km 기준 높이, 6 km scale height, 논문의 고정 절단 지점, Natural Earth 육지 마스크를 사용했다. 넓은 펄스와 느린 꼬리 형태는 재현했지만 도달이 늦었으며 감쇠 MAE가 A–B에서 6.146 dB/Mm, A′–B′에서 5.991 dB/Mm였다.

그 외 조건을 맞춘 CUDA `float64` 실행 결과는 6.148 및 5.992 dB/Mm였다. 0.002 및 0.001 dB/Mm 변화는 잔차에 비해 무시할 수 있으므로 부동소수점 정밀도 부족은 원인에서 제외했다.

### 전리층과 DFT window 보정

이전 전리층은 지나치게 완만하여 주 펄스를 지연시키고 논문의 DFT 절차에 필요한 양의 오버슈트와 zero crossing을 없앴다. 70 km 기준 높이와 3.33 km scale height를 사용하자 해당 파형 구조가 복원됐다. 이제 계산한 각 트레이스는 도달 시간이 다른 파형에서 복사한 절단 지점이 아니라 자체 오버슈트 이후 zero crossing에서 잘린다.

보정한 level 7에서 A와 B의 음의 피크는 steps 8,760 및 18,222에서 약 7,513 및 14,459로 이동했다. 기준 고정 주파수 감쇠 MAE는 약 6 dB/Mm에서 0.387 및 0.399 dB/Mm로 감소했다. 이는 전체 검증 과정에서 가장 큰 개선이었다.

### 기준 감쇠 수렴

다음 표는 더 이상 쓰지 않는 plot-fit 기준을 사용한 이전 자동 생성 보고서의 감쇠 지표를 대체한다. 아래 모든 값은 Bannister 원 방정식과 같은 고정 주파수 45개를 사용한다.

| Subdivision | 표면 셀 | A–B MAE / 최대 | 최대 주파수 | A′–B′ MAE / 최대 | 최대 주파수 |
|---:|---:|---:|---:|---:|---:|
| 6 | 40,962 | 0.681 / 2.282 dB/Mm | 396.729 Hz | 0.696 / 2.420 dB/Mm | 447.591 Hz |
| 7 | 163,842 | 0.387 / 2.708 dB/Mm | 488.281 Hz | 0.399 / 2.753 dB/Mm | 488.281 Hz |
| 8, 이전 | 655,362 | 0.274 / 1.218 dB/Mm | 478.109 Hz | 0.275 / 1.225 dB/Mm | 478.109 Hz |
| 8, 고정 깊이 polar 대조군 | 655,362 | 0.310 / 2.384 dB/Mm | 488.281 Hz | 0.286 / 1.092 dB/Mm | 478.109 Hz |
| 8, ETOPO5 프로덕션 | 655,362 | 1.104 / 2.538 dB/Mm | 457.764 Hz | 0.242 / 3.258 dB/Mm | 488.281 Hz |

현재 ETOPO5 서쪽 경로의 평균은 이전 두 level-8 결과보다 낮지만 지점별 최댓값은 더 크다. 동쪽 경로는 체계적으로 이동했고 level-8 사례 중 평균이 가장 크다. 물질 충실도는 시간 영역 비대칭을 개선하지만 Figure 8 전체를 개선하지는 않는다. 어느 경로의 판정도 바뀌지 않는다.

검토한 level-8 ETOPO5 실행은 NVIDIA GeForce RTX 3060에서 35,000 steps를 2,677.5초에 완료했다. 정렬된 dual-circulation kernel의 낮은 peak memory 덕분에 이전 10.1 GB compiled-preflight 할당을 피했다. 적응형 절단 길이는 A, A′, B, B′에 대해 각각 23,462, 22,676, 24,491, 24,550 samples였다.

## 균일 모델 위상 및 도달 수렴

격자 분산을 자연적인 동서 비대칭과 분리하기 위해 횡방향으로 변하는 표면 물질을 제거했다. 복소 스펙트럼은 `A·conj(B)`와 `A′·conj(B′)`로 만들고 DC부터 unwrap한 뒤, 추가 45° 대원 거리의 위상 속도로 변환했다.

| Subdivision | A–B 위상 MAE / 최대 | A′–B′ 위상 MAE / 최대 | 피크 속도 A–B / A′–B′ | 1/4 호 동서 RMS |
|---:|---:|---:|---:|---:|
| 6 | 0.0357 / 0.0941 c | 0.0388 / 0.1034 c | 0.8040 / 0.8025 c | 1.500e-2 |
| 7 | 0.0189 / 0.0504 c | 0.0195 / 0.0521 c | 0.8007 / 0.8003 c | 3.892e-3 |
| 8 | 0.0142 / 0.0276 c | 0.0143 / 0.0280 c | 0.7994 / 0.7993 c | 1.014e-3 |

Level 6→7 및 7→8에서 최대 위상 속도 오차의 관측 차수는 A–B가 0.90과 0.87, A′–B′가 0.99와 0.90이다. 1/4 호 동서 RMS 차이는 1.95와 1.94 차수로 수렴한다. 절대 고주파 위상 오차는 약 1차로 수렴하고 균일 모델의 방향 대칭성은 약 2차로 복원된다. 평균 위상 오차 차수는 아직 점근 영역이 아니다. Level 6→7에서 약 1이던 값이 level 7→8에서 약 0.4로 낮아진다.

## NOAA ETOPO5와 지각 프로파일 점검

논문은 Reference 22의 NOAA-NGDC “Global Relief CD-ROM”만 기복 자료로 식별한다. ETOPO5라는 이름, 원자료 파일명, 판본, 전처리 규약은 명시하지 않는다. ETOPO5는 해당 시기의 1993 NOAA-NGDC 전 지구 기복 자료이므로 재현 가능한 복원 자료로 사용했지만 동일한 원자료로 확인되지는 않았다.

보관한 big-endian NOAA-NGDC `ETOPO5.DAT` 입력은 2,160×4,320 cell-centered 5-arc-minute 고도·수심 격자이다. Loader는 18,662,400-byte 크기와 SHA-256 digest `471d3dd534144aa9a6551fe3e76320a06a45dade6fd8d45f7d6ad981d59f93c3`를 확인한 뒤 각 측지 물질 지점에서 bilinear sampling한다.

[Hermance(1995)](https://doi.org/10.1029/RF001p0190)는 논문 Figure 6에서 재사용한 제한된 개념 단면의 출처이지 배포 가능한 전 지구 3-D 전도도 데이터셋은 아니다. 그림은 0.3 Ω·m 해수, ≥500 Ω·m 상부 암반, ≤200 Ω·m 해양 중간층, ≤500 Ω·m 심부 암반을 제시한다. 구현은 표시된 경계값을 취해 500/200/500 Ω·m 대표 프로파일을 사용한다. 위치가 수치로 주어지지 않은 국소 ≤5/≤10 Ω·m 전도체는 전 지구 층으로 확장하지 않는다.

첨부한 원문을 대조하면서 기존 프로파일의 오류를 확인했다. 기존 50 Ω·m가 Figure 6의 전 지구 영역 어디에도 해당하지 않는데 60 km 아래 전체 격자에 적용돼 있었다. 이 값을 500 Ω·m로 고친 뒤 subdivision-5 CUDA `float64` 수신 트레이스의 상대 RMS 변화는 `2.34e-16`에 그쳤다. 보정한 영역이 표면에서 ELF skin depth의 수십 배 아래에 있어 보고 정밀도에서 감쇠 지표는 같다.

같은 보정값으로 최종 subdivision-8, 35,000-step CUDA `float64` 실행을 다시 수행했다. 새 수신 전계와 기존 프로덕션 트레이스의 상대 RMS 차이는 `7.69e-16`, 최대 절대 차이는 `8.74e-22 V/m`이다. 피크 step, 적응형 DFT 절단점, Figure 8 지표와 모든 PASS/FAIL 판정은 그대로다. 이 트레이스에서 Figure 7과 8을 다시 그렸으며 기존 raw plot과 픽셀 단위로 같다.

| 심부 값 | A–B / A′–B′ MAE | A–B / A′–B′ 최댓값 | B / B′ 정규화 피크 |
|---:|---:|---:|---:|
| 기존 50 Ω·m | 5.04682 / 2.19317 dB/Mm | 7.34090 / 6.21746 dB/Mm | 0.040361 / 0.407856 |
| 보정 500 Ω·m | 5.04682 / 2.19317 dB/Mm | 7.34090 / 6.21746 dB/Mm | 0.040361 / 0.407856 |

[Bannister(1985)](https://doi.org/10.1029/RS020i004p00977)의 주간 단일 scale-height 프로파일은 `σ(z)/ε0 = 2.5×10⁵ exp[(z−H)/ζ₀]`이다. 구현은 이제 `ζ₀ = 1/0.3 km`를 3.33 km로 반올림하지 않고 그대로 사용하며 `σ(H) = 2.5×10⁵ ε0`를 확인하는 회귀 테스트도 추가했다. 최종 프로덕션 명령은 이미 정확한 값을 명시했다. 이번 subdivision-8 전체 재실행에서도 기본값 보정이 프로덕션 곡선을 바꾸지 않음을 확인했다.

| Level-7 물질 | 1/4 호 동서 RMS | A / A′ 피크 steps | A–B / A′–B′ 감쇠 MAE | A–B / A′–B′ 최대 오차 |
|---|---:|---:|---:|---:|
| 균일 | 0.00389 | 7,514 / 7,510 | 0.412 / 0.427 dB/Mm | 1.838 / 1.890 dB/Mm |
| ETOPO5 + Figure 6 프로파일 | 0.08220 | 7,546 / 7,589 | 0.387 / 0.590 dB/Mm | 1.747 / 2.020 dB/Mm |

표본화한 level-7 기복은 −9.69~+6.30 km이며 육지는 28.9%다. 실제 기복과 별도의 해양/대륙 프로파일은 A/A′ 피크를 43 steps 분리하고 1/4 호 동서 RMS를 약 21배 높인다. 이는 물질이 만드는 방향 비대칭을 재현하지만 지점별 감쇠 잔차를 논문의 범위 안으로 넣지는 못한다.

## TensorBoard 물리 진단

진단 실행은 검증 workflow와 같은 solver update를 사용하며 CUDA device에서 reduction을 수행한다. Field norm, finite flag, 양수인 이산 staggered-field energy, 방사 영역별 및 동·서 적도 회랑별 전도 전력, 소스 timing, 수신값, 처리량, CUDA memory를 기록한다. 정확한 표본값은 `physics-diagnostics.npz`에도 저장하며 TensorBoard는 대화형 표시 수단일 뿐이다. Recorder는 TensorBoardX를 사용해 backend와 무관한 event file을 기록한다. Staggered energy는 비교용 진단값이며 동일 시각의 정확한 보존 Hamiltonian이라고 주장하지 않는다.

### Backend 및 관측기 대조 실험

Backend 대조 실험에는 subdivision-3 균일 모델을 15,000 steps 실행했다. 기록 중립성 대조 실험에서는 실제 TensorBoard recorder를 512 steps마다 호출했다.

| 점검 | 수치 결과 | 결론 |
|---|---:|---|
| NumPy CPU 대 CUDA eager | 최종 `Er`, `Et`, `Hr`, `Ht` 배열이 정확히 같고 트레이스 상대 L2는 `4.15e-17` | CUDA eager 연산은 원인이 아님 |
| NumPy CPU 대 CUDA compiled | 트레이스 상대 L2 `6.52e-15`, `Er`/`Et`/`Ht` 상대 L2 약 `1e-14` | Compilation은 반올림 수준의 값만 바꿈 |
| Compiled `Hr` 대조군 | 최대 절대 차이 `1.84e-24 A/m`, 기준 norm `1.26e-23 A/m` | 이상적으로 없어야 할 mode의 큰 상대비는 수치적으로 무의미함 |
| 기록한 실행 대 기록하지 않은 CUDA compiled 실행 | 수신 트레이스와 최종 필드 네 개가 bitwise equal | TensorBoard 관측은 시뮬레이션을 바꾸지 않음 |
| Finite-field flag | 모든 35,000-step 물질 실행의 표본 필드가 유한함 | 불안정성과 NaN/Inf 전파를 제외함 |

### 에너지 및 전도 손실 위치 추적

물질 대조 실험은 subdivision 5, CUDA `float64`, 35,000 steps를 사용했고 소스, 전리층, 방사 격자, solver 설정은 모두 같게 유지했다. 전 지구 적분값은 256 steps마다 표본화했다. 회랑 비율은 별도의 512-step 간격 재실행에서 구했다. 회랑은 소스 공통 근방을 제외하고 소스에서 동쪽 또는 서쪽 5°–90°와 위도 ±10° 범위를 포함한다.

| 물질 | 전 지구 전도 손실 | 대기 영역 비율 | 동/서 회랑 손실비 | B / B′ 음의 피크 |
|---|---:|---:|---:|---:|
| 균일 | 0.62843 mJ | 88.43% | 1.0452 | −0.404 / −0.403 μV/m |
| Natural Earth | 0.62819 mJ | 88.69% | 1.0450 | −0.414 / −0.415 μV/m |
| ETOPO5 + Figure 6 프로파일 | 0.62714 mJ | 88.88% | 1.0279 | −0.040 / −0.407 μV/m |

세 전 지구 손실은 0.21% 안에서 일치한다. ETOPO5는 B가 10분의 1로 약해졌는데도 회랑 손실비가 가장 대칭적이다. B 도달 시점과 가까운 step 15,360에서 ETOPO5 동쪽 회랑의 표본 field energy는 `5.28e-8 J`로, 서쪽의 `4.12e-8 J`보다 28% 많다. 약한 B 값은 동쪽 경로의 과도한 누적 손실로 펄스가 사라진 결과가 아니다.

### 수신점 지지 자유도와 해안선 aliasing

적도 동경 43°의 정확한 B 좌표에서 ETOPO5 고도는 −207 m다. 그런데 subdivision-5 barycentric receiver는 가중치의 88.8869%를 동경 42.75°의 인접 dual vertex에 할당하며 이 vertex의 표면고도는 +30 m다. B 피크에서 이 육지 vertex의 값은 거의 0인 반면 두 해양 지지 vertex는 모두 약 −0.36 μV/m다. 이 이상은 보간값의 상쇄가 아니다. 지배적인 지지 자유도의 해수면 `Er` 평면 전체에 암석 물질이 할당된 결과다.

| Subdivision | B 보간 가중치 중 육지에 할당된 비율 | 지배적인 지지점의 표면 |
|---:|---:|---:|
| 5 | 88.8869% | +30.00 m, 육지 |
| 6 | 77.7772% | +30.00 m, 육지 |
| 7 | 55.5555% | +30.00 m, 육지 |
| 8 | 11.1111% | −246.75 m, 해양 |

격자를 세분화할수록 지배적인 지지점이 해양으로 이동하고 육지 가중치는 단조롭게 감소한다. Subdivision-5 민감도 실행에서는 모든 수심을 유지하고 양의 표면고도만 0으로 바꿨다. B/B′는 −0.040/−0.407에서 −0.414/−0.414 μV/m로 바뀌었고 1/2 경로 동서 RMS는 8.649에서 0.00556으로 감소했다. 이 의도적으로 비물리적인 제한은 원인 분리용 대조 실험이지 제안하는 지형 모델이 아니다.

Subdivision 8에서 5°–90° 회랑을 면적 가중 방식으로 정적 점검한 결과, 소스 동쪽은 44.96%, 서쪽은 30.27%가 육지다. 얕은 바다는 동쪽 5.02%, 서쪽 6.05%이므로 얕은 해양 표본화만으로는 동쪽의 더 큰 감쇠 방향을 설명할 수 없다. 남은 효과는 둘로 갈린다. 점 표본화한 지형은 5 km 방사 셀에서 해안 육지의 영향을 과장할 수 있다. 한편 400–500 Hz 잔차에는 별도로 측정한 등방성 공간 분산과 논문의 격자·물질 자료와의 차이도 들어 있다.

### 보존적 dual-cell 물질 실험

새 `dual-cell` 옵션은 각 방사 전계 자유도에 대응하는 실제 다각형 영역에서 `Er` 물질값을 면적 평균한다. Dual cell을 겹치지 않는 구면 wedge 5개 또는 6개로 나누고 정규화한 각 wedge 중심에서 기복을 한 번 표본화한다. 가중치에는 정확한 wedge solid angle을 사용한다. 가중치 합은 `2e-12` 이내에서 1이며, 균일 물질 회귀 결과는 point support와 같다. 이 방법은 보존적인 1차 quadrature이지 해안에서 전계 자유도를 나누는 conformal 기법은 아니다.

Subdivision 5에서 B 지배 셀의 wedge 면적 중 해수면보다 엄밀히 높은 부분은 15.72%다. 면적 평균을 적용하면 해수면 물질값이 순수 암석(`0.002 S/m`, `εr = 10`)에서 `3.143e-4 S/m`, `εr = 2.415`로 바뀐다. 실제 기복은 그대로다. 하지만 이 값도 3 μs 시간 간격에서는 강한 도체이며 하나의 `Er` 자유도로 육지와 해양의 서로 다른 전계를 나타낼 수 없다.

| Subdivision-5 support | B / B′ 음의 피크 | 1/2 경로 동서 RMS | 전 지구 표본 손실 | 동/서 회랑 손실비 |
|---|---:|---:|---:|---:|
| Point `Er`, point `Et` | −0.0402 / −0.4065 μV/m | 8.649 | 0.61005 mJ | 1.0279 |
| Dual-cell `Er`, point `Et` | −0.0397 / −0.4043 μV/m | 8.716 | 0.60968 mJ | 1.0009 |
| Dual-cell `Er`, fractional edge-diamond `Et` | −0.0343 / −0.3347 μV/m | 8.637 | 1.54744 mJ | 1.0760 |

`Er` 면적 평균은 경로 손실을 더 대칭적으로 만들지만 B 억제는 그대로다. 기존 방사 경계 분율 평균과 edge-diamond `Et` 평균까지 추가하면 1/2 경로의 두 진폭이 모두 줄고 전 지구 표본 손실은 두 배 이상 증가한다. 이 조합도 Figure 7 보정안에서 제외했다.

전체 subdivision-8 CUDA `float64` 대조 실험에서는 point `Et`를 유지하고 `Er`만 point에서 dual-cell 평균으로 바꿨다. B 수신 가중치의 88.8889%를 차지하는 지배 셀은 wedge 표본 6개가 모두 해양이다. 나머지 11.1111% 가중치의 셀은 wedge 면적 기준 육지 68.11%다. 35,000-step 실행은 모든 필드가 유한한 상태로 2,713.7초에 끝났다.

| Subdivision-8 지표 | Point `Er` 프로덕션 | Dual-cell `Er` 대조군 | 변화 |
|---|---:|---:|---:|
| A/A′ 상대 RMS | 37.895% | 38.247% | 악화 |
| B/B′ 상대 RMS | 30.458% | 30.369% | 미미한 개선 |
| A / A′ 피크 step | 7,491 / 7,721 | 7,492 / 7,724 | +1 / +3 steps |
| B / B′ 피크 step | 14,803 / 14,667 | 14,806 / 14,672 | +3 / +5 steps |
| A–B 감쇠 MAE / 최대 | 1.104 / 2.538 dB/Mm | 1.160 / 5.339 dB/Mm | 악화 |
| A′–B′ 감쇠 MAE / 최대 | 0.242 / 3.258 dB/Mm | 0.235 / 1.591 dB/Mm | 개선됐지만 여전히 FAIL |

서쪽 최대 감쇠 오차는 줄었지만 1.0 dB/Mm 한계를 넘고 동쪽 최댓값은 두 배 이상 커졌다. Figure 7 분리도 사실상 그대로다. dual-cell 방식은 명시적인 물질 적분 옵션으로 유지하되 프로덕션 검증 기본값으로 채택하지 않는다. 이 부정적 결과로 point-to-area 계수 평균을 누락된 Figures 7–8 보정안에서 제외할 수 있다. 실제 해안 subcell 기법을 쓰려면 해안 양쪽에 별도의 전계 자유도가 필요하다. 최종 level-8 주파수 잔차에 대해서는 B 지배 셀이 이미 전부 해양이므로, 별도로 관측한 등방성 공간 분산을 줄이는 작업의 우선순위가 더 높다.

## Staggered 소스 배치 점검

논문의 5 km 수직 소스 중심은 2.5 km로, 이 solver의 staggered `Er` 평면 0과 5 km의 중간이다. 보정한 구현은 수평 barycentric weight 3개와 방사 0.5/0.5 cloud-in-cell weight를 결합하여 `Er` 자유도 6개에서 정확한 2,500 m 중심과 총전류를 모두 보존한다.

| 배치 | 표현된 중심 | 트레이스 RMS 변화 | 1/4 호 동서 RMS | A–B / A′–B′ MAE | A–B / A′–B′ 최대 |
|---|---:|---:|---:|---:|---:|
| 최근접 평면 | 0 m | 기준 | 0.082197 | 0.387016 / 0.589615 | 1.7465 / 2.0198 dB/Mm |
| 선형 staggered | 2,500 m | 5.496e-4 | 0.082151 | 0.386878 / 0.589475 | 1.7458 / 2.0160 dB/Mm |

모든 주 펄스 피크 step은 그대로다. 올바른 소스 배치는 실제 기하 오차를 제거하지만 남은 검증 잔차에는 거의 영향을 주지 않는다.

## 측지 격자의 방향 분산

기존 측지 dual grid는 유지했다. 횡방향으로 균일한 모델에서 30° 간격의 방위각 12개를 따라 서로 대응하는 45° 및 90° 수신기 사이의 위상 속도를 측정했다. 연속체 해는 방위각에 무관하므로 방위각 평균으로부터의 편차가 격자 방향성을 분리한다.

네 실행 모두 25,023 steps, 같은 고정 DFT 주파수 45개, CUDA의 compiled PyTorch와 `float64`를 사용했다. Levels 5–6은 방사 선별 실험의 기준 실행이다. Levels 7–8은 수정한 solver의 revision `85d311e`에서 다시 실행하여 원시 트레이스와 주파수별 값을 확보했다. 방위각 spread는 최대·최소 위상속도 차이를 방위각 평균으로 나눈 값이다. Bannister 열은 이 평균을 식 (4)와 비교하므로 수평 공간 분산뿐 아니라 유한 방사 격자와 모델 오차도 포함한다. 실행시간은 당시 사용 가능한 RTX 3060과 RTX 2060 SUPER에서 측정했으므로 서로 다른 GPU의 성능 비교에는 쓸 수 없다.

| Subdivision | 표면 셀 | 실행 시간 | DFT 절단 범위 | 평균 spread | 최대 spread (주파수) | 상대 RMS | Bannister MAE / 최대 (최대 주파수) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 10,242 | 33.0 s | 21,407–21,657 | 5.0419% | 13.7591% (498.454 Hz) | 2.0896% | 0.07537 / 0.17966 c (366.211 Hz) |
| 6 | 40,962 | 118.3 s | 21,491–21,581 | 0.4671% | 1.3342% (498.454 Hz) | 0.1766% | 0.03523 / 0.09466 c (498.454 Hz) |
| 7 | 163,842 | 467.8 s | 21,508–21,561 | 0.1157% | 0.4789% (498.454 Hz) | 0.04700% | 0.01870 / 0.04920 c (498.454 Hz) |
| 8 | 655,362 | 1,580.6 s | 21,513–21,556 | 0.02422% | 0.08662% (488.281 Hz) | 0.01001% | 0.01418 / 0.02804 c (488.281 Hz) |

각 subdivision에서 대표 수평 간격이 절반으로 줄어든다고 가정하면 평균 spread의 관측 차수는 levels 5→6, 6→7, 7→8에서 각각 3.43, 2.01, 2.26이다. 최대 spread의 차수는 3.37, 1.48, 2.47이고 상대 RMS 차수는 3.56, 1.91, 2.23이다. Level 5는 고주파 점근 영역에 들어가지 못했다. Levels 6–8에서는 후기 파형 창에 민감한 최댓값에 변동이 있지만 전체적으로 약 2차 방향 수렴을 보인다.

대역별 평균 및 최대 spread를 보면 해상도 부족이 시작되는 지점을 더 분명히 알 수 있다.

| Subdivision | 50–200 Hz 평균 / 최대 | 200–375 Hz 평균 / 최대 | 375–500 Hz 평균 / 최대 |
|---:|---:|---:|---:|
| 5 | 0.4518 / 1.1312% | 3.3448 / 7.1391% | 12.5575 / 13.7591% |
| 6 | 0.09297 / 0.20978% | 0.42829 / 0.70535% | 0.94942 / 1.33419% |
| 7 | 0.02420 / 0.05126% | 0.09707 / 0.15903% | 0.24561 / 0.47887% |
| 8 | 0.004879 / 0.01104% | 0.02096 / 0.03658% | 0.05081 / 0.08662% |

375 Hz 이상에서 평균/최대 spread는 level 6의 0.949%/1.334%에서 level 8의 0.0508%/0.0866%로 줄었다. 약 400 Hz 이상에서 나타난 급격한 level-5 분기는 해상도 부족 효과이며 일반적인 격자 세분화만으로 방향 오차는 사실상 없앨 수 있다.

모든 방위각에 공통인 최소, 중앙, 최대 적응형 절단 지점을 적용하면 levels 6, 7, 8의 평균 spread 범위는 각각 0.4678–0.4680%, 0.1154–0.1162%, 0.02422–0.02452%다. 최대 spread 범위도 1.288–1.334%, 0.4617–0.4969%, 0.08621–0.08724%다. 방향별 DFT window 선택 때문에 수렴하는 것처럼 보이는 현상은 아니다.

방향 수렴과 Bannister 기준으로의 수렴은 서로 다르다. Levels 5→6→7→8에서 Bannister MAE로 계산한 차수는 1.10, 0.91, 0.40으로 계속 낮아진다. 세 격자에 `E(h) = E∞ + C h^p`를 맞춰 수평 이산화 오차와 남는 극한값을 분리하면 다음과 같다.

| 주파수 대역 | Level 6 MAE | Level 7 MAE | Level 8 MAE | 추정 `p` | `E∞` | Level 9 예상 MAE |
|---|---:|---:|---:|---:|---:|---:|
| 50–500 Hz | 0.03523 c | 0.01870 c | 0.01418 c | 1.87 | 0.01247 c | 0.01294 c |
| 375–500 Hz | 0.06190 c | 0.02771 c | 0.01766 c | 1.77 | 0.01349 c | 0.01471 c |
| 400–500 Hz | 0.06463 c | 0.02921 c | 0.01797 c | 1.66 | 0.01275 c | 0.01441 c |

이 외삽은 수평 해상도 세 개만 사용했으며 level 9를 직접 계산한 결과가 아니다. 다만 현재의 5 km 방사 격자와 해석적 물질 모델을 유지하면 개선 폭이 줄어들고 약 0.0125–0.0135 c의 오차가 남을 것으로 예측한다. 격자 세분화는 방향 오차를 거의 모두 없애고 위상 불일치의 상당 부분을 줄일 수 있다. 그러나 현재 결과만으로 세분화만 하면 논문과 정확히 일치한다고 판단할 수는 없다.

Level-9 CUDA `float64` 실행은 메모리 부족을 일으키기 전에 선별 단계에서 제외했다. 이론적 하한은 네 필드와 전기장 갱신 계수 배열 네 개를 포함한다. 실측 피크에는 topology, Hodge 계수, 수신 표본, compilation 임시 배열도 들어간다.

| Subdivision | 표면 셀 | 상주 메모리 이론 하한 | CUDA 피크 실측/예상 | 상태 |
|---:|---:|---:|---:|---|
| 7 | 163,842 | 0.84 GiB | 1.44 GiB 실측 | 직접 실행 완료 |
| 8 | 655,362 | 3.35 GiB | 5.33 GiB 실측 | 직접 실행 완료 |
| 9 | 2,621,442 | 13.40 GiB | 약 21.3 GiB 예상 | 실행하지 않음: 설치된 GPU는 최대 12 GiB |

추후 약 24 GiB 이상의 CUDA GPU에서 외삽값을 직접 검증할 수 있도록 방향 분산 CLI가 subdivision 9를 받도록 확장했다. 측지 격자와 merged latitude–longitude 격자는 유한 해상도에서 분산 관계가 다를 수 있지만 세분화하면 각각의 연속체 모델에 접근해야 한다.

## 동일 해상도 Mesquite 대조 실험

Subdivision-8 polar grid의 셀 655,362개, connectivity, 방사 격자, 두 극점의 오각형 중심을 유지하면서 좌표만 최적화했다. 고정한 Sandia Mesquite 2.99 adapter는 2006 검증과 같은 구면 uniform size-and-shape 목적함수를 사용한다. `TShapeSizeB1`을 `PMeanP(1)`로 aggregate하고 `TrustRegion`으로 최소화했다. 최적화에는 667.3초가 걸렸고 최대 vertex 이동은 0.015512 rad였다. 좌표 SHA-256은 `4128445eff7255239ac8a300ea325e77332b091aba93fca774362ba3cc3f4e22`다.

| Subdivision-8 격자 지표 | 원래 polar mesh | Mesquite | 감소 |
|---|---:|---:|---:|
| Primal-edge length CV | 0.065027 | 0.042253 | 35.0% |
| Primal-face area CV | 0.086445 | 0.062416 | 27.8% |
| Dual-cell area CV | 0.085796 | 0.062410 | 27.3% |
| Adjacent dual-area jump RMS | 0.012193 | 0.001874 | 84.6% |
| 최대 adjacent dual-area jump | 0.121132 | 0.075813 | 37.4% |
| 실수 `l=1` 조화함수의 상대 Laplace 오차 | `2.4784e-5` | `2.7100e-6` | 89.1% |
| 실수 `l=2` 조화함수의 상대 Laplace 오차 | `2.6779e-4` | `1.0758e-4` | 59.8% |

균일 모델 CUDA `float64` 대조 실험에서는 이 좌표만 바꿨다. 적응형 절단 범위는 21,514–21,555로 원래 격자의 21,513–21,556과 거의 같다.

| Subdivision-8 균일 모델 지표 | 원래 polar mesh | Mesquite | 변화 |
|---|---:|---:|---:|
| Bannister MAE, 50–500 Hz | 0.01417971 c | 0.01417758 c | −0.0150% |
| Bannister 최대 오차 | 0.02803688 c | 0.02798620 c | −0.181% |
| Bannister MAE, 400–500 Hz | 0.01797263 c | 0.01796371 c | −0.0496% |
| 평균 방위각 spread | 0.024223% | 0.027638% | +14.1% |
| 최대 방위각 spread | 0.086622% | 0.088630% | +2.32% |

모든 방위각에 공통인 최소, 중앙, 최대 절단 지점을 쓰면 원래 격자의 MAE는 0.0141710–0.0141796 c, Mesquite 격자는 0.0141694–0.0141775 c다. 평균 spread 범위는 각각 0.02422–0.02451%, 0.02751–0.02764%다. 미미한 위상 개선과 spread 증가는 적응형 window에서 생긴 현상이 아니다. Mesquite는 정적 격자 및 Laplace 지표를 크게 개선하지만 이미 해상도가 높은 현재 격자에서는 균일 Maxwell 분산을 의미 있게 개선하지 못했다. 다만 같은 vertex 이동이 지형과 해안 voxelization도 바꾸므로 균일 실험에 없는 이 효과를 확인하려면 ETOPO5 프로덕션 대조 실험이 필요하다.

ETOPO5 대조 실험은 현재 revision에서 같은 GPU로 두 번 실행했으며 mesh 좌표만 바꿨다. Native trace SHA-256 `147b4756b11c25f11b63825a381afe9fc17e747dbc2a33910c7a36060946d5e1`은 보관한 프로덕션 trace와 정확히 일치했다. 중간 solver 변경은 이 비교에 영향을 주지 않는다. Mesquite trace SHA-256은 `33df8aed8721676e9dc9ed7ad444182715e49174b7646499b067e1f162ac502a`다.

| Subdivision-8 ETOPO5 지표 | Native polar mesh | Mesquite | 변화 |
|---|---:|---:|---:|
| A/A′ 상대 RMS | 37.895% | 37.826% | 상대 −0.18% |
| B/B′ 상대 RMS | 30.458% | 21.196% | 상대 −30.4% |
| A / A′ 피크 step | 7,491 / 7,721 | 7,491 / 7,720 | 0 / −1 steps |
| B / B′ 피크 step | 14,803 / 14,667 | 14,797 / 14,666 | −6 / −1 steps |
| A / A′ 피크 | −1.1431 / −1.1852 μV/m | −1.1435 / −1.1840 μV/m | 거의 같음 |
| B / B′ 피크 | −0.3162 / −0.4186 μV/m | −0.3524 / −0.4186 μV/m | B 크기 +11.5% |
| A–B 감쇠 MAE / 최대 | 1.104 / 2.538 dB/Mm | 0.914 / 2.201 dB/Mm | −17.2% / −13.3% |
| A′–B′ 감쇠 MAE / 최대 | 0.242 / 3.258 dB/Mm | 0.247 / 3.351 dB/Mm | +1.9% / +2.9% |
| FDTD 실행 시간 | 2,134.6 s | 2,136.3 s | 비슷함 |

네 trace 전체의 상대 RMS 변화는 2.94%지만 변화는 B에 집중된다. A, A′, B′는 각각 0.073%, 0.154%, 0.052%만 달라졌지만 B는 11.46% 변했다. 균일 모델에서 차이가 거의 없었다는 사실까지 고려하면, 이 개선은 Maxwell 분산 감소가 아니라 동쪽 1/2 경로 수신점 부근의 ETOPO5 지형·해안 voxelization 변화에서 나왔다. 동서 피크 크기 순서가 두 쌍 모두 여전히 반대이므로 Figure 7은 FAIL이다. Mesquite의 Figure 8 최대오차도 2.201 및 3.351 dB/Mm로 0.5 및 1.0 dB/Mm 한계를 넘으므로 FAIL이다. 한 경로는 개선되고 다른 경로는 악화됐기 때문에 native polar grid를 기준 프로덕션 결과로 유지하며 출판 플롯 비교 이미지도 교체하지 않는다.

## 방사 및 등방 분산 분리

구현 감사 이후의 선별 실험에는 횡방향 균일 모델과 같은 방위각 12개를 사용했다. 방사 refinement factor 2는 5 km 셀 40개를 2.5 km 셀 80개로 바꾼다. CFL 조건을 지키기 위해 `Δt`도 3 μs에서 1.5 μs로 줄였다. 관측 물리시간 75.069 ms와 변환 창 98.304 ms를 유지하도록 steps와 DFT 크기를 함께 두 배로 늘렸다. 소스 중심과 폭은 물리시간 기준으로 고정했고 모든 실행을 같은 주파수 45개에서 평가했다.

| Subdivision | 방사 간격 | `Δt` | 평균 / 최대 위상 오차 | 평균 / 최대 방위각 spread | 피크 도달속도 spread |
|---:|---:|---:|---:|---:|---:|
| 5 | 5 km | 3 μs | 0.07537 / 0.17966 c | 5.0419% / 13.7591% | 0.5294% |
| 5, 시간 대조군 | 5 km | 1.5 μs | 0.07537 / 0.17966 c | 5.0419% / 13.7591% | 0.5294% |
| 5 | 2.5 km | 1.5 μs | 0.07145 / 0.16188 c | 7.1384% / 19.0672% | 0.5477% |
| 6 | 5 km | 3 μs | 0.03523 / 0.09466 c | 0.4671% / 1.3342% | 0.2454% |
| 6 | 2.5 km | 1.5 μs | 0.03821 / 0.09096 c | 1.4074% / 10.8257% | 0.2367% |

시간 대조군의 평균 오차는 level-5 기준과 `5.05e-8 c`, 최대 오차는 `8.48e-7 c`만 다르다. 방위각 spread도 상대 약 `3e-7`까지 일치한다. 따라서 이 대역에서 3 μs 시간 간격의 시간 분산은 무시할 수 있다.

| Subdivision / 방사 간격 | 50–200 Hz MAE / 최대 | 200–375 Hz MAE / 최대 | 375–500 Hz MAE / 최대 |
|---|---:|---:|---:|
| 5 / 5 km | 0.02707 / 0.04914 c | 0.11099 / 0.17966 c | 0.08451 / 0.17792 c |
| 5 / 2.5 km | 0.03034 / 0.05189 c | 0.10700 / 0.16188 c | 0.07241 / 0.15571 c |
| 6 / 5 km | 0.01442 / 0.02084 c | 0.03319 / 0.04498 c | 0.06190 / 0.09466 c |
| 6 / 2.5 km | 0.01764 / 0.02316 c | 0.03546 / 0.04825 c | 0.06555 / 0.09096 c |

방사 세분화는 level-5 상위 대역을 개선하지만 level 6에서는 같은 추세가 이어지지 않는다. Adaptive DFT 절단 범위도 3 μs에서 21,491–21,581 samples이던 값이 1.5 μs에서 40,918–43,305 samples로 넓어진다. 물리시간으로는 64.47–64.74 ms와 61.38–64.96 ms다. 모든 방향에 공통인 64 ms 절단점을 적용해도 level-6 평균/최대 spread는 0.522%/2.818%에서 2.228%/12.346%로 증가한다. 주 펄스 도달 spread는 약 0.24%를 유지하므로, 큰 스펙트럼 spread는 주 도달속도의 같은 크기 변화가 아니라 방향에 따라 달라진 후기 파형과 mode 성분에서 나온다.

일관된 효과는 수평 세분화에서 나타난다. Subdivision 5→6은 5 km에서 평균 및 최대 위상오차를 53.3%, 47.3% 줄이고 2.5 km에서는 46.5%, 43.8% 줄인다. 균일 방사 세분화는 level-8 프로덕션 실행으로 올리지 않았다. 비용이 약 네 배이고 논문의 5 km 이산화와도 달라지며, 저해상도 개선 기준도 통과하지 못했다. levels 7–8 선별에서는 수평 방향 오차가 계속 수렴했지만 Bannister 잔차가 0이 아닌 값에 접근했다. 고차 또는 분산 최적화 Hodge/curl 구성은 격자 topology를 유지하면서 남은 수평 오차를 더 효율적으로 줄일 수 있지만, 이것만으로 전체 불일치를 고친다고 볼 근거는 없어졌다. 주파수 의존성이 있으므로 하나의 상수로 파동속도를 재조정하는 방법도 맞지 않는다.

## 강건성 점검

| 점검 | 결과 | 해석 |
|---|---:|---|
| float32 MPS 대 float64 CUDA 기준 MAE | ≤0.002 dB/Mm 변화 | 정밀도는 원인이 아님 |
| 고정 주파수에서 32,768 대 65,536 FFT | 약 `1e-12` 상대 일치 | Zero-padding은 원인이 아님 |
| 적응형 절단을 ±16 samples 이동 | 최대 오차 약 0.01 dB/Mm 변화 | 절단 선택은 원인이 아님 |
| 최근접 평면 대 staggered 소스 | 5.496e-4 트레이스 상대 RMS | 소스 반올림은 원인이 아님 |
| 세분화에 따른 균일 대칭성 | 약 2차 수렴 | 격자 방향성은 해상도로 제어됨 |
| NumPy 대 CUDA eager/compiled | 정확히 같거나 상대 약 `1e-14` 이내 | PyTorch backend와 compilation은 원인이 아님 |
| 기록한 실행 대 기록하지 않은 CUDA compiled 실행 | 필드와 트레이스가 bitwise identical | TensorBoard 관측은 계산을 바꾸지 않음 |
| ETOPO5 동/서 회랑 손실 | B가 10분의 1로 약하지만 비율은 1.0279 | 동쪽 경로 전체의 전도 손실은 원인이 아님 |
| Level 5 양의 기복 제한 | B/B′가 −0.414/−0.414 μV/m로 복원됨 | 조격자 해안선 물질 aliasing을 확인함 |
| Level 5 dual-cell `Er` | B/B′가 −0.040/−0.404 μV/m로 유지됨 | 면적 평균으로 해안 양쪽 전계를 분리할 수 없음 |
| Level 8 dual-cell `Er` | 동/서 최댓값 5.339/1.591 dB/Mm | Figure 8 전체 보정안에서 제외함 |
| Level 5에서 `Δt` 3 대 1.5 μs | 평균 위상오차 변화 `5.05e-8 c` | 시간 분산은 원인이 아님 |
| 방사 간격 5 대 2.5 km | Level 5/6 위상오차가 일관되게 개선되지 않음 | 균일 방사 세분화를 제외함 |
| 수평 subdivision 5→6 | 두 방사 격자에서 평균 오차 53.3% / 46.5% 감소 | 조격자에서 수평 오차가 가장 크게 줄일 수 있는 항임 |
| 수평 levels 6→8 | 평균 spread 0.4671%→0.02422%, Bannister MAE 0.03523→0.01418 c | 방향 오차는 수렴하지만 절대 불일치는 0이 아닌 극한에 접근함 |
| Level-8 Mesquite 좌표 | Laplace `l=1` 오차 −89.1%, Bannister MAE −0.0150%, 평균 spread +14.1% | 정적 품질은 개선되지만 균일 Maxwell 분산은 의미 있게 개선되지 않음 |
| Level-8 Mesquite ETOPO5 | B 크기 +11.5%, 동쪽 최대 −13.3%, 서쪽 최대 +2.9% | 국소 voxelization은 개선되지만 Figure 7–8 전체 보정안에서는 제외함 |

## 재현 명령

CUDA `float64`로 기준 complete-time ETOPO5 복원을 실행한다.

```bash
uv run --extra pytorch --extra visualization python -m \
  verification.simpson_taflove_2004 \
  --subdivision 8 --mesh-orientation polar --steps 35000 \
  --material etopo5 --etopo5-path data/ETOPO5.DAT \
  --deep-lithosphere-resistivity-ohm-m 500 \
  --backend torch --device cuda:0 --dtype float64 --torch-compile \
  --dft-window adaptive \
  --ionosphere-reference-height-km 70 \
  --ionosphere-scale-height-km 3.3333333333333335 \
  --synchronize-every 1024 \
  --output-dir /tmp/ionosphere-verification-20260806/st2004-fig7-l8-etopo5-35000
```

물질과 출력 디렉터리만 바꾸어 고정 깊이 Natural Earth 대조군을 실행한다.

```bash
uv run --extra pytorch --extra visualization python -m \
  verification.simpson_taflove_2004 \
  --subdivision 8 --mesh-orientation polar --steps 35000 \
  --material natural-earth \
  --deep-lithosphere-resistivity-ohm-m 500 \
  --backend torch --device cuda:0 --dtype float64 --torch-compile \
  --dft-window adaptive \
  --ionosphere-reference-height-km 70 \
  --ionosphere-scale-height-km 3.3333333333333335 \
  --synchronize-every 1024 \
  --output-dir /tmp/ionosphere-verification-20260806/st2004-l8-fixed-depth-control
```

정확한 표본 archive를 남기면서 subdivision-5 ETOPO5 물리 대조 실험을 TensorBoard에 기록한다.

```bash
uv run --extra tensorboard --extra pytorch --extra visualization python -m \
  verification.simpson_taflove_2004 \
  --subdivision 5 --mesh-orientation polar --steps 35000 \
  --material etopo5 --etopo5-path data/ETOPO5.DAT \
  --radial-support dual-cell \
  --deep-lithosphere-resistivity-ohm-m 500 \
  --backend torch --device cuda:0 --dtype float64 --torch-compile \
  --dft-window adaptive \
  --ionosphere-reference-height-km 70 \
  --ionosphere-scale-height-km 3.3333333333333335 \
  --diagnostics-every 512 \
  --tensorboard-log-dir /tmp/ionosphere-diagnostics/st2004-l5-etopo5/events \
  --output-dir /tmp/ionosphere-diagnostics/st2004-l5-etopo5

uv run --extra tensorboard tensorboard \
  --logdir /tmp/ionosphere-diagnostics
```

Subdivision, 표본 간격, 출력 위치를 바꾸어 전체 subdivision-8 dual-cell 대조 실험을 실행한다.

```bash
uv run --extra tensorboard --extra pytorch --extra visualization python -m \
  verification.simpson_taflove_2004 \
  --subdivision 8 --mesh-orientation polar --steps 35000 \
  --material etopo5 --etopo5-path data/ETOPO5.DAT \
  --radial-support dual-cell \
  --deep-lithosphere-resistivity-ohm-m 500 \
  --backend torch --device cuda:0 --dtype float64 --torch-compile \
  --dft-window adaptive \
  --ionosphere-reference-height-km 70 \
  --ionosphere-scale-height-km 3.3333333333333335 \
  --diagnostics-every 1024 --synchronize-every 1024 \
  --tensorboard-log-dir /tmp/ionosphere-diagnostics/st2004-l8-dual/events \
  --output-dir /tmp/ionosphere-diagnostics/st2004-l8-dual
```

측지 격자를 바꾸지 않고 방향 분산 sweep을 다시 생성한다.

```bash
for subdivision in 5 6 7 8; do
  uv run --extra pytorch --extra visualization python -m \
    verification.directional_dispersion \
    --subdivision "${subdivision}" --steps 25023 \
    --azimuth-step-deg 30 \
    --backend torch --device cuda:0 --dtype float64 --torch-compile \
    --synchronize-every 1024 \
    --output-dir \
      "/tmp/horizontal-dispersion-level-${subdivision}-float64-cuda"
done
```

고정된 Mesquite adapter를 build하고 subdivision-8 좌표를 최적화한 뒤, 같은 해상도의 균일 대조 실험을 실행한다.

```bash
python verification/mesh_optimization/tools/build.py \
  --build-dir build/mesquite

python -m verification.mesh_optimization \
  --subdivision 8 --orientation polar --fixed-vertices poles \
  --executable build/mesquite/bin/ionosphere-mesquite-optimize \
  --movement-tolerance 1e-10 --max-iterations 200 --timeout 1800 \
  --output /tmp/ionosphere-mesquite-level-8.npz

uv run --extra pytorch --extra visualization python -m \
  verification.directional_dispersion \
  --subdivision 8 --steps 25023 --azimuth-step-deg 30 \
  --mesh-coordinates /tmp/ionosphere-mesquite-level-8.npz \
  --backend torch --device cuda:0 --dtype float64 --torch-compile \
  --synchronize-every 1024 \
  --output-dir /tmp/horizontal-dispersion-level-8-mesquite
```

같은 좌표로 ETOPO5 프로덕션 대조 실험을 실행한다.

```bash
uv run --extra pytorch --extra visualization python -m \
  verification.simpson_taflove_2004 \
  --subdivision 8 --mesh-orientation polar --steps 35000 \
  --mesh-coordinates /tmp/ionosphere-mesquite-level-8.npz \
  --material etopo5 --etopo5-path data/ETOPO5.DAT \
  --deep-lithosphere-resistivity-ohm-m 500 \
  --backend torch --device cuda:0 --dtype float64 --torch-compile \
  --dft-window adaptive \
  --ionosphere-reference-height-km 70 \
  --ionosphere-scale-height-km 3.3333333333333335 \
  --synchronize-every 1024 \
  --output-dir /tmp/st2004-level-8-mesquite-etopo5-35000
```

방향 분산 CLI는 subdivision 9를 지원한다. 이 CUDA `float64` 구성으로 실행하려면 여유 메모리가 약 24 GiB 이상인 GPU가 필요하다.

```bash
uv run --extra pytorch --extra visualization python -m \
  verification.directional_dispersion \
  --subdivision 9 --steps 25023 \
  --azimuth-step-deg 30 \
  --backend torch --device cuda:0 --dtype float64 --torch-compile \
  --synchronize-every 1024 \
  --output-dir /tmp/horizontal-dispersion-level-9-float64-cuda
```

물리 관측시간을 맞춘 상태에서 방사, 시간, 수평 분산을 분리한다.

```bash
for subdivision in 5 6; do
  for radial_refinement in 1 2; do
    time_refinement="${radial_refinement}"
    steps=$((25023 * time_refinement))
    uv run --extra pytorch --extra visualization python -m \
      verification.directional_dispersion \
      --subdivision "${subdivision}" --steps "${steps}" \
      --radial-refinement "${radial_refinement}" \
      --azimuth-step-deg 30 \
      --backend torch --device cuda:0 --dtype float64 --torch-compile \
      --synchronize-every 1024 \
      --output-dir "/tmp/radial-dispersion-l${subdivision}-r${radial_refinement}"
  done
done

uv run --extra pytorch --extra visualization python -m \
  verification.directional_dispersion \
  --subdivision 5 --steps 50046 \
  --radial-refinement 1 --time-refinement 2 \
  --azimuth-step-deg 30 \
  --backend torch --device cuda:0 --dtype float64 --torch-compile \
  --synchronize-every 1024 \
  --output-dir /tmp/radial-dispersion-l5-r1-t2
```

이 명령들은 실행별 그림, 압축 트레이스, 지표, Markdown 보고서를 다시 생성한다. 위의 통합 스칼라 결과가 보관 기록이며 생성한 Simpson–Taflove 및 directional-dispersion artifacts는 저장소에 보존하지 않는다.

## 최종 평가

구현은 다음 구조 및 정성 점검을 통과한다.

- 예상한 전 지구 ELF 펄스를 발생시키고 전파한다.
- 보정한 전리층 매개변수로 예상 펄스 순서가 복원된다.
- 감쇠, 위상 속도, 도달 시간, 대칭성은 모두 세분화에 따라 개선된다.
- ETOPO5 기복과 제한된 지각 프로파일이 물리적으로 타당한 동서 비대칭을 만든다.
- 소스는 전류를 보존하면서 정확한 staggered 중심에 배치된다.
- 방향 격자 오차가 정량화되며 약 2차로 수렴한다.
- Backend 간 일치와 비침습 진단을 확인하여 PyTorch 구현 경로를 관측된 불일치의 원인에서 제외했다.
- Field energy와 전도 손실의 위치를 추적하여 수치 불안정성과 동쪽 경로 전체의 과도한 흡수를 제외했다.
- 지형 대조 실험에서 조격자 B 억제의 직접 원인이 해안선 물질 aliasing임을 확인했다.
- 보존적 dual-cell `Er` 평균은 점 표본 민감도를 줄이지만 조격자 수신값과 최종 level-8 감쇠 잔차를 고치지 못한다.
- 방사·시간 대조 실험에서 시간 적분과 균일 방사 세분화는 효과적인 보정안에서 제외했고 수평 세분화가 일관되게 가장 큰 위상오차 감소를 보였다.
- Levels 7–8 직접 실행에서 방향 오차가 약 2차로 수렴했지만 세 격자 외삽에서는 수평 연속격자 극한에도 Bannister 오차가 약 0.0125 c 남았다.
- 같은 해상도의 Mesquite 좌표는 정적 격자 품질과 동쪽 경로의 국소 ETOPO5 수신값을 개선하지만 균일 Maxwell 분산과 양쪽 감쇠 경로를 함께 개선하지는 못한다.

복원한 동/서 피크 순서가 반대이고 1/2 경로 분리가 과도하므로 Figure 7의 정확한 재현에는 실패한다. 또한 subdivision 8의 최대 감쇠 오차가 2.538 및 3.258 dB/Mm로 요구 한계 0.5 및 1.0 dB/Mm를 넘으므로 Figure 8도 실패한다. 잔차는 400–500 Hz에서 지배적이다. 가능한 원인은 등방성 고주파 공간 분산, 유한한 5 km 방사 이산화, 점 표본화한 해안 물질 체적, Hermance 개념 단면에서 사용할 수 없는 국소 지각 구조, 그리고 논문의 adaptive merged latitude–longitude grid와 현재 구현의 geodesic dual grid 사이의 불가피한 차이다. 조격자 수신점 이상은 이제 위치를 특정했다. Subdivision-8 지지 기하와 완료한 dual-cell 대조 실험을 함께 보면, 단순한 물질 계수 평균으로는 고주파 감쇠 잔차 전체를 설명할 수 없다. 방사 선별 실험에서도 5 km 간격을 절반으로 줄인 결과가 Bannister 기준으로 일관되게 수렴하지 않았고 후기 파형 스펙트럼의 강건성도 낮아졌다. 수평 세분화는 공간 분산을 크게 줄이지만 Bannister 기준의 개선 폭은 점차 작아진다. 따라서 남은 불일치를 모두 격자 해상도 탓으로 돌릴 수 없으며, 유한 방사 격자와 전리층 및 기준 모델의 가정도 함께 점검해야 한다.

Mesquite 대조 실험은 좌표 최적화가 국소적으로 aliasing된 지형 voxel을 개선할 수 있지만 분산이나 감쇠를 전반적으로 보정하지는 못한다는 점도 확인했다.

이 결과는 Figure 7의 전체 시간 범위를 포괄하고 형태도 올바르지만 상대 트레이스 일치에는 실패한 복원, 그리고 Figure 8의 엄격한 지점별 재현 실패로 기술해야 한다. Figures 7과 8의 정확한 재현에 성공했다고 기술해서는 안 된다.
