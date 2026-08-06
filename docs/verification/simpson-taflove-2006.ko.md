# Simpson–Heikes–Taflove 2006 Figures 5–7 검증

> 최종 재현 판정: **FAIL**

프로덕션 재실행은 2026-08-05(Asia/Seoul)에 수행했다.

영문 원본: [English](simpson-taflove-2006.md).

## 요약

이 연구에서는 현재의 3차원 측지 FDTD 구현이 Simpson, Heikes, Taflove(2006)의 Figures 5, 6, 7을 재현하는지 시험한다. 프로덕션 계산은 NVIDIA CUDA GPU의 PyTorch와 `float64` field를 사용한다.

Figure 5는 출판된 도달 순서, 시점, 오버슈트, 느린 꼬리 형태를 재현하지만 네 상대 진폭을 모두 재현하지는 못한다. 보정한 지리 위치 탐색기는 이전에 겹쳤던 B/B′ 관측을 분리한다. 최종 level-7 polar ETOPO5 실행은 구면에서 Sandia Mesquite의 균일 size-and-shape 목적함수를 사용하며, 약 0.39/0.39 대신 정규화된 원거리 피크 0.31141/0.35571을 얻는다. 이전 one-step smoother의 원거리 경로 상대 RMS 134.5%를 18.5%로 줄였고 두 원거리 꼬리도 서로 일치하지만, 공통 크기는 출판 플롯의 육안 추정치보다 약 40% 낮다. CUDA `float64` 분리 실험에서 고정 깊이 표면은 두 원거리 피크와 동서 대칭을 복원하는 반면 얕은 모든 해양 column에 5-km 해수 셀을 강제해도 영향이 거의 없다. 따라서 남은 불일치는 얕은 수신기 수심만이 아니라 전체 기복/암석권 voxelization과 공개되지 않은 논문의 정확한 Mesquite 구성 및 좌표와 관련된다. Figure 6은 이제 Figure 5와 동일하게 검토된 polar Mesquite 트레이스에서 계산한다. 동/서 평균 절대 오차는 0.921/0.284 dB/Mm, 최대 절대 오차는 3.020/2.125 dB/Mm이다. 두 경로 모두 50–500 Hz에서 논문의 지점별 ±0.5 dB/Mm 주장을 만족하지 못한다.

Figure 7 역시 송신기 위치를 반대 반구에서 Clam Lake로 보정한 뒤 주장된 민감도의 방향만 유지한다. `ΔHtan` 중앙값은 −43.25 dB이고 특이하지 않은 sample의 92.47%가 −25 dB 미만이지만, `ΔHr` 중앙값은 +20 dB 부근의 곡선이 아니라 +126.00 dB다. 계산한 방사/접선 중앙 민감도 이점 165.90 dB도 논문의 약 45 dB와 다르다. 정확한 방사 소스 stagger와 지리적 `Hr` 보간은 관측 연산자를 바로잡지만, 거의 0인 기준 `Hr`에서 비롯되는 실패를 해결하지 못한다. 따라서 세 Figure를 하나의 완전한 정량 세트로 재현하지 못했다.

## 대상 논문과 원자료 기록

대상은 J. J. Simpson, R. P. Heikes, and A. Taflove, “FDTD Modeling of a Novel ELF Radar for Major Oil Deposits Using a Three-Dimensional Geodesic Grid of the Earth-Ionosphere Waveguide,” *IEEE Transactions on Antennas and Propagation*, 54(6), 1734–1741, 2006, [doi:10.1109/TAP.2006.875504](https://doi.org/10.1109/TAP.2006.875504)이다.

제공된 8쪽 PDF `/home/kwchun/simpson.pdf`의 SHA-256 digest는 `b33632d3eb8c004c69f8d5100792966583206cb62374df298651ce9560f31952`다. 아래 비교에 사용한 출판 패널은 제공 파일의 5, 6, 7쪽에서 잘라냈다. 저작권은 © 2006 IEEE에 있으며 출처를 명시한 기술 발췌로만 포함했다.

## 합격 기준

논문이 세 Figure에 서로 다른 수준의 정량 정보를 제공하므로 기준을 분리한다.

| Figure | 기준 |
|---|---|
| 5 | 정성적 파형 형태, 도달 순서, 근거리/원거리 진폭 비. 논문의 절대 진폭은 임의 단위임. |
| 6 | 두 계산 경로가 50–500 Hz에서 Bannister 주간 결과의 약 ±0.5 dB/Mm 이내임. |
| 7 | 특이하지 않은 거의 모든 시점에서 `ΔHtan`이 기준보다 25 dB 이상 낮고, `ΔHr`이 약 +20 dB에 도달하며, 방사 감지가 약 45 dB 더 민감함. |

| 검증 대상 | 현재 결과 | 판정 |
|---|---|---:|
| Figure 5 형태와 도달 순서 | 재현 | **PASS** |
| Figure 5 상대 진폭과 경로 유사성 | 원거리 피크 0.31141/0.35571, RMS 37.41%/18.47% | **FAIL** |
| Figure 6 A–B 지점별 감쇠 | 최대 잔차 3.020 dB/Mm | **FAIL** |
| Figure 6 A′–B′ 지점별 감쇠 | 최대 잔차 2.125 dB/Mm | **FAIL** |
| Figure 7 전체 레이더 민감도 | 아래에 전체 검토 재실행 결과를 보고 | **FAIL** |
| Figures 5–7 전체 재현 | 모든 Figure에서 하나 이상의 기준 실패 | **FAIL** |

Figure 7 본문과 caption은 정규화 설명이 서로 모순된다. 본문은 차이를 Model-A field의 peak로 나눈다고 하지만, caption은 플롯의 spike가 기준 파형의 zero crossing 때문에 생긴다고 한다. Peak-normalized difference에는 그런 pole이 생길 수 없다. 따라서 검증에서는 caption과 실제 플롯을 따른다.

```text
ΔH(t) = |H_B(t) - H_A(t)| / |H_A(t)|
```

스칼라 요약에서는 기준 peak의 `1e-6` 이내 값을 제외하고, 렌더링 곡선에는 zero-crossing spike로 접근하는 부분을 남긴다. “almost every time”의 재현 가능한 스칼라 해석으로, 이 보고서는 특이하지 않은 sample 중 최소 95%가 −25 dB 미만이어야 한다고 정한다.

## 수치 모델

### Figure 5

| 항목 | 구현 값 |
|---|---:|
| 표면 격자 | subdivision 7, 163,842 geodesic dual cells |
| 방향 | polar, 두 극점에 pentagonal cell center 배치 |
| 격자 품질 | unit sphere에서 Mesquite 2.99 uniform size-and-shape optimization, polar pentagons 고정 |
| 방사 영역 | −100~+100 km |
| 방사 셀 | 5 km 간격 40개 |
| 시간 간격 | 3.0 μs |
| 기록 steps / 시간 | 40,000 / 0.120 s |
| 소스 | 0° N, 47° W의 5 km 수직 전류 |
| Gaussian `1/e` 전체 폭 / 중심 | `480 Δt` / `960 Δt` |
| 수신기 | 적도를 따라 A/A′는 ±45°, B/B′는 ±90° |
| 표면 자료 | NOAA-NGDC ETOPO5, bilinear sampling |
| 전리층 | 70 km 기준 높이, 3.33 km scale height |
| Backend | compiled PyTorch, CUDA, float64 |
| Optimizer | `TShapeSizeB1`, `PMeanP(1)`, `TrustRegion` |
| Mesquite source revision | `7ae51c8e8617c67e63018c8a7effc0f5455f58b4` |
| 프로덕션 구현 revision | `e916119` |
| Mesh-coordinate SHA-256 | `221052c8a2bb109f4ee0142d19b4e181c31fd04e508074495f5ff7923cede75f` |
| Vertex-coordinate SHA-256 | `c5736acfb24f1e9e7c97e5ade78c5f4c9ddeb30859aba6ead1502781091cac47` |
| 트레이스 SHA-256 | `34a8f94a329035cebdcd9b56aef8f14f23782754f888ead9bfdaba0e97c86372` |
| 격자 최적화 / FDTD 실행 시간 | 165.7 / 627.1 s |

소스는 수평 평면에서 barycentric distribution하고 0과 5 km `Er` 평면 사이에서 선형 stagger하여 정확한 2.5 km 중심과 총전류를 보존한다.

현재 Figure 5와 Figure 6 결과에는 이 단일 구성을 기준으로 사용한다. v2 archive의 vertex byte는 이전 v1 Mesquite archive와 정확히 같고 검증한 provenance metadata만 변경됐다.

### Figure 7

| 항목 | 구현 값 |
|---|---:|
| 표면 격자 | subdivision 7, 163,842 geodesic dual cells |
| 명목 방사 격자 | −100~+100 km에서 5 km |
| 표면 근처 암석권 subgrid | −5~0 km에서 1.25 km |
| 실제 방사 셀 | 43 |
| 안정 시간 간격 | Courant factor 1.0에서 2.083689715 μs |
| 시뮬레이션 시간 / steps | 0.1616 s / 77,542 |
| 송신기 | Clam Lake, Wisconsin, 46.5° N, 90.9° W |
| 지상선 | 남북 및 동서 22.5 km, 각각 300 A |
| 펄스 | 20 Hz carrier, 42.5 ms Gaussian-envelope FWHM |
| 유전 중심 | 69° N, 156° W |
| 유전 면적 | 4,800 km²와 같은 면적의 원, 반지름 39.088 km |
| 유전 깊이 | 중앙 깊이 1.2 km에서 두께 1.25 km |
| 전도도 대비 | 주변 지층의 0.1배 |
| Backend | compiled PyTorch, CUDA GPU 2개, float64 |
| 프로덕션 revision | `e916119` |
| 실행 시간 | 기준 1,087.776 s / 이상체 1,302.219 s |
| 기준 트레이스 SHA-256 | `227813f66db8c49e43680f37ddcfc12c3c3a533c19b7b74029f381d1a5b983d7` |
| 이상체 트레이스 SHA-256 | `ed25d2311a6a51de107b677a0e7eec37c6a282211d34ce5c1fbaa8d4fa763fc6` |

이 보고서의 트레이스 hash와 Figure 7 지표는 위의 완전하게 검토된 terrain-relative, conservative-area 프로덕션 쌍을 나타낸다. Revision, mesh, material, source, observation operator, precision, time grid를 포함한 run signature가 정확히 일치한다.

보정한 구현은 다음 프로덕션 구성 초기화 gate를 통과한다.

| Gate | 현재 subdivision-7 결과 | 판정 |
|---|---:|---:|
| Clam Lake 소스 수직 기준 | ETOPO5 terrain, +236.8 m | **PASS** |
| Alaska 수신기 수직 기준 | ETOPO5 terrain, +305.0 m | **PASS** |
| 유전 body 수직 구간 | −1,520~−270 m MSL | **PASS** |
| TM dual-cell 유전 면적 | 4,800.0 km² | **PASS** |
| TE edge-diamond 유전 면적 | 4,800.0 km² | **PASS** |
| CUDA float64 compiled smoke | Courant 1.0에서 유한한 10 steps | **PASS** |
| Persistent / peak compiled GPU memory | 985 MiB / 1.59 GiB | **PASS** |

지상선 소스는 포함 face의 방향을 가진 primal edge 세 개 모두에 projection된다. 각 기여에는 `L/Δl`을 곱하여 표면 edge 하나보다 짧은 선에서도 지정한 `I·L` 전류 모멘트를 보존한다. 세 edge 길이는 55.59, 64.78, 55.59 km이므로 22.5 km 소스가 전체 edge로 조용히 확장되지 않고 실제 subcell로 표현된다. 소스는 −625 m 및 +2,500 m의 tangential-field 평면 사이에서도 0.8/0.2 weight로 adjoint-linear stagger한다. 표면 `Hr` sample은 두 staggered 방사 평면 사이에서 선형 보간하고, 포함 face와 이웃 세 개로 정확한 유전 좌표에서 복원한다. East와 north `Htan`은 주변의 방향을 가진 dual-edge sample을 local least-squares inverse하여 복원하며, 고정된 주 reference polarization을 signed tangential waveform에 사용한다.

논문은 Canadian Shield 전도도를 `2.4e-4 S/m`로 제시하지만 정확한 격자 mask는 공개하지 않는다. 따라서 두 모델 모두 Canada 중심의 문서화된 2,500 km cap 근사를 사용한다. 이 선택은 기준/이상체 차이에서 일부 상쇄되지만 재현성 한계로 남는다.

## Figure 5: 시간 응답

![출판된 Figure 5와 재현한 Figure 5](images/simpson-taflove-2006-fig-5-comparison.png)

네 수신기 기록을 하나의 공통 정규화로 각각 표시했다. 검토한 Mesquite-optimized ETOPO5 실행에서 A/A′ 피크 시점은 22.548/23.232 ms, B/B′는 44.415/44.037 ms다. 계산 파형은 출판된 도달 순서, 주 펄스, 반대 부호 오버슈트, 뒤따르는 느린 꼬리를 유지한다. 원시 펄스는 음수이며, 비교 패널에서는 출판 플롯에 맞추기 위해 공통 부호 반전을 한 번 적용한다. 그러나 진폭은 여전히 작다. 정규화된 B/B′ 피크는 0.31141/0.35571이고 출판된 두 원거리 기록의 육안 추정치는 약 0.39다.

| Figure 5 기준 | 출판 결과 | 재현 | 판정 |
|---|---|---|---:|
| 도달 순서 | 1/4 대척점 응답이 1/2 대척점 응답보다 먼저 도달 | A/A′ 22.548/23.232 ms, B/B′ 44.415/44.037 ms | **PASS** |
| 주 펄스 시점 | 출판 패널의 대응 위치에서 피크 발생 | 네 피크 모두 출판 트레이스와 육안상 정렬 | **PASS** |
| 파형 형태 | 음의 주 펄스, 반대 부호 오버슈트, 느린 꼬리 | 세 특징 모두 존재 | **PASS** |
| A/A′ 경로 유사성 | 근거리 기록은 유사하지만 같지는 않음 | 상대 RMS 차이 37.41% | **FAIL** |
| B/B′ 경로 유사성 | 원거리 기록은 유사하지만 같지는 않음 | 상대 RMS 차이 18.47% | **FAIL** |
| 원거리 피크 크기 | 두 원거리 피크 모두 약 0.39 | B/B′ 0.31141/0.35571 | **FAIL** |
| 0.12 s 원거리 느린 꼬리 | 두 원거리 꼬리 모두 약 0.10 | B/B′ 0.06085/0.05911 | **FAIL** |
| 전체 정성 형태 | 순서와 특징적 파형 형태 | 필요한 정성 특징 존재 | **PASS** |
| 정확한 플롯 재현 | 시점, 상대 진폭, 경로 유사성 일치 | 시점은 일치, 진폭과 대칭성은 불일치 | **FAIL** |

따라서 Figure 5는 **형태는 통과하지만 정량적으로 실패**한다. 논문의 세로축이 임의 단위이고 전류 진폭을 제시하지 않으므로 절대 진폭 기준은 사용하지 않는다. 위 실패 기준은 모두 하나의 공통 정규화 이후 상대량만 사용한다.

### 이전 Figure 5 프로덕션 트레이스 대비 변화

| 지표 | 이전 | 검토 재실행 | 변화 |
|---|---:|---:|---:|
| A/A′ 상대 RMS | 37.435% | 37.408% | **0.027 percentage points 개선** |
| B/B′ 상대 RMS | 18.484% | 18.474% | **0.010 percentage points 개선** |
| B 정규화 피크 | 0.31148 | 0.31141 | 사실상 동일 |
| B′ 정규화 피크 | 0.35580 | 0.35571 | 사실상 동일 |
| 0.12 s B/B′ 꼬리 | 0.06093 / 0.05922 | 0.06085 / 0.05911 | 사실상 동일 |

아주 작은 대칭성 개선은 수치로 측정할 수 있지만 Figure 5 판정을 바꿀 정도는 아니다.

### Figure 5 불일치 후속 진단

#### 지리 위치 탐색 보정과 물질 분리

최초 프로덕션 실행에는 지리적 face 선택 결함이 있었다. 한 방향과 그 대척 방향이 모두 unsigned spherical-triangle test를 만족했고 첫 후보를 선택했다. 그 결과 요청한 소스와 수신기 경도는 다음처럼 표현됐다.

| 위치 | 요청 경도 | 이전 표현 경도 |
|---|---:|---:|
| Source | −47° | +133° |
| A | −2° | +178° |
| A′ | −92° | +88° |
| B | +43° | −137° |
| B′ | −137° | −137° |

공통 180° 이동은 source-to-A/A′/B 거리를 보존하여 도달 시간 오류를 숨겼고 B와 B′를 한 관측으로 겹쳤다. 이제 face 후보는 요청 방향과의 양의 alignment로 선택한다. 회귀 테스트는 논문의 소스와 네 수신기를 모두 포함하며 대척 B/B′ 관측이 서로 다른 face를 사용하도록 요구한다. 이 보고서의 프로덕션 지표는 보정된 level-7 계산 결과다.

비용이 큰 실행을 반복하기 전에 보정 위치 subdivision-5 세 사례로 물질 영향을 분리했다. 모두 40,000 steps, CUDA `float64`, 네 개별 기록의 공통 정규화를 사용했다.

| 물질 | B / B′ 피크 | 0.12 s B / B′ 꼬리 | 1/4 / 1/2 동서 RMS |
|---|---:|---:|---:|
| 균일 암석권 | 0.37691 / 0.37855 | 0.07200 / 0.07194 | 5.2% / 1.9% |
| 고정 깊이 Natural Earth 육지/해양 | 0.38240 / 0.38539 | 0.07481 / 0.07466 | 5.2% / 1.9% |
| ETOPO5 기복 및 대표 암석 프로파일 | 0.11120 / 0.39237 | 0.02238 / 0.06673 | 30.8% / 235.9% |

균일 및 고정 깊이 육지/해양 모델은 출판된 약 0.39의 원거리 피크를 복원하고 동/서 경로를 유사하게 유지한다. ETOPO5와 대표 500/200/50 Ω·m 프로파일을 추가하면 동쪽 B 경로가 강하게 억제되고 B′는 출판 피크 부근에 남는다. 이는 core FDTD update가 아니라 현재 기복/암석권 이산화가 보정 위치 경로 비대칭의 주원인임을 나타낸다. 논문에서 사용한 정확한 Hermance 기반 cellwise conductivity는 구할 수 없다.

프로덕션 해상도 비교에서도 같은 결과를 확인한다.

| Level-7 구성 | A / A′ 피크 | B / B′ 피크 | A/A′ / B/B′ 상대 RMS |
|---|---:|---:|---:|
| Native 고정 깊이 진단 | 1.00000 / 0.99476 | 0.33907 / 0.33993 | 0.6% / 0.5% |
| 이전 native ETOPO5 | 0.97920 / 1.00000 | 0.16425 / 0.35813 | 37.3% / 105.0% |
| 이전 polar projected-step ETOPO5 | 0.96355 / 1.00000 | 0.14159 / 0.35471 | 37.6% / 134.5% |

요청한 source, A, A′, B, B′ 위치의 ETOPO5 고도는 각각 −24, −5,014, −3,041, −207, −4,538 m이다. 5-km 방사 간격에서 해수면 아래 첫 tangential material sample은 −2.5 km다. 따라서 얕은 207-m B 해양 아래는 암석, 깊은 B′ 해양 아래는 물로 표본화한다. 처음에는 이것이 얕은 물 point sampling이 지배적임을 시사했다. 그러나 이후 conservative test에서 4,258개 edge column을 바꾸어 5-km 표면 물 셀 하나를 보존했어도 B/B′는 0.04585/0.40613에서 0.04580/0.40605로만 변했다. 고정 깊이 대조군은 양의 육지 기복도 평탄화하고 다른 해안선을 사용했다. 그러므로 전체 표면 기하 표현을 propagation update와 분리하지만 실패를 수신기 수심만으로 돌릴 수는 없다.

#### 방사 결합은 논문의 의도적인 thin-shell 근사

Taflove and Hagness Chapter 3 Section 3.6.8과 제공된 2006 논문을 검토하여 방사 update의 해석을 수정했다. Chapter 3은 integral Ampere 및 Faraday contour에서 Yee scheme을 유도한다. Cartesian Yee cell에서는 마주 보는 contour segment 길이가 같으므로 circulation은 단순 field difference를 cell increment로 나눈 형태가 된다. Simpson, Heikes, Taflove는 교차하는 측지 TE 및 TM 평면을 방사 방향으로 “regular Yee-type updates”로 결합한다고 명시한다. 식 (5)–(7), (10)–(12)는 radius-weighted field 없이 `Δt/(μ0 Δr) [E(k+1/2) - E(k-1/2)]` 및 `Δt/(ε0 Δr) [H(k+1) - H(k)]`를 사용한다.

구현도 같은 단순 방사 차분을 사용한다. 두꺼운 shell의 완전한 spherical curl에는 `(1/r) ∂(rEt)/∂r`와 `(1/r) ∂(rHt)/∂r`가 들어가지만 이를 추가하면 대상 알고리즘과 달라진다. 논문은 약 6,371 km의 Earth radius 주변 200-km 영역을 locally prismatic Yee cell stack으로 취급한다. 이는 재현에서 실수로 누락한 것이 아니라 의도적인 thin-shell 근사다.

수치 점검으로 subdivision-5 ETOPO5 쌍에서 방사 차분만 radius-weighted 형태로 교체했다. 두 실행 모두 CUDA `float64`, 40,000 steps를 사용했다. 정규화한 4-trace RMS 변화는 `3.39e-6`, 공통 절대 피크 변화는 0.053%뿐이었고 피크 시점은 그대로였으며 far/near ratio는 0.386870128에서 0.386869895로 변했다. 따라서 다른 응용에서 연속체 구면 형식을 선호하더라도 radial metric weighting은 Figure 5 불일치를 설명할 수 없다.

#### 보정한 polar orientation 기준선

논문은 각 지리 극점에 pentagonal cell 하나를 두지만 원래 native mesh orientation은 극점에 hexagonal cell을 뒀다. 프로덕션 기본값은 이제 subdivision 전에 rigid `polar` rotation을 적용한다. Topology와 모든 intrinsic metric term을 보존하면서 두 polar cell center를 지리 극점과 일치시킨다. 원래 `native` orientation은 명시적 진단으로만 남아 있다.

첫 보정 위치 polar 기준 실행은 subdivision 5, ETOPO5, 40,000 steps, CUDA `float64`, point material sampling, 이전 screen과 같은 공통 4-trace normalization을 사용했다. Propagation 또는 material equation은 바꾸지 않았다.

| Orientation | A / A′ 피크 | B / B′ 피크 | 0.12 s B / B′ 꼬리 | A/A′ / B/B′ 상대 RMS |
|---|---:|---:|---:|---:|
| Native 진단 | 0.94981 / 1.00000 | 0.11120 / 0.39237 | 0.02238 / 0.06673 | 30.8% / 235.9% |
| Polar 논문 기하 | 0.97600 / 1.00000 | 0.04036 / 0.40786 | 0.00854 / 0.06923 | 34.5% / 855.1% |

필수 polar alignment만으로 Figure 5는 개선되지 않는다. 이 해상도에서 동쪽 원거리 경로 억제를 키우고 B′는 출판 피크 부근에 남긴다. Rigid rotation은 횡방향 균일 구면의 수치 분산을 바꿀 수 없으므로, 이 결과는 변화가 ETOPO5 column과 회전된 edge가 이를 표본화하는 경로에 있음을 더 명확히 한다. Polar geometry는 fit parameter가 아니라 정확성을 위해 유지한다. 이후 mesh-quality 및 material-isolation 실험은 이 polar baseline을 사용한다.

#### 제약된 격자 품질과 고정 깊이 gate

Reference 13은 세분화한 측지 격자 smoothing에 Mesquite를 사용했다고 하지만 목적함수 weight나 최종 좌표를 공개하지 않는다. 따라서 결정론적 근사를 opt-in 실험으로 추가했다. 두 극점을 포함한 pentagonal anchor 12개를 고정하고 unit sphere에 projected step을 적용하여 great-circle edge-length variance를 최소화한다. Subdivision 5의 한 step은 edge-length CV를 0.06503에서 0.06082, triangle-area CV를 0.08644에서 0.07911, dual-cell-area CV를 0.08133에서 0.07714, adjacent dual-area-jump RMS를 0.03235에서 0.02524로 줄인다. 최악의 상대 adjacent jump도 0.11071에서 0.08294로 감소한다.

첫 propagation gate는 고정 5-km Natural Earth 해양 모델을 사용하여 이웃 수평 sample 사이에서 수심이 바뀌지 않게 했다. 두 계산 모두 보정 polar orientation, subdivision 5, 40,000 steps, CUDA `float64`, 공통 4-trace normalization을 사용했다.

| Mesh optimization | A / A′ 피크 | B / B′ 피크 | 0.12 s B / B′ 꼬리 | A/A′ / B/B′ 상대 RMS |
|---|---:|---:|---:|---:|
| 0 steps | 1.00000 / 0.99338 | 0.39728 / 0.39777 | 0.07752 / 0.07737 | 0.9% / 0.6% |
| 1 projected step | 1.00000 / 0.99660 | 0.39700 / 0.39769 | 0.07732 / 0.07717 | 0.7% / 0.6% |

두 격자 모두 출판된 원거리 피크 크기를 복원하며 동/서 경로가 거의 같다. 품질 step은 근거리 경로 일치를 약간 개선하지만 원거리 응답에는 실질적 영향이 없다. 따라서 고정 깊이 gate를 통과한다. Polar geodesic FDTD propagation 자체는 Figure 5 진폭과 대칭을 만들 수 있고 mesh smoothing만으로 ETOPO5 실패를 맞출 수는 없다.

대응하는 ETOPO5 재실행은 다음 gate를 통과하지 못한다.

| Polar subdivision-5 물질 | A / A′ 피크 | B / B′ 피크 | 0.12 s B / B′ 꼬리 | A/A′ / B/B′ 상대 RMS |
|---|---:|---:|---:|---:|
| ETOPO5, optimization 0 steps | 0.97600 / 1.00000 | 0.04036 / 0.40786 | 0.00854 / 0.06923 | 34.5% / 855.1% |
| ETOPO5, 1 projected step | 0.97231 / 1.00000 | 0.04585 / 0.40613 | 0.00964 / 0.06858 | 34.0% / 734.0% |
| 고정 깊이, 1 projected step | 1.00000 / 0.99660 | 0.39700 / 0.39769 | 0.07732 / 0.07717 | 0.7% / 0.6% |

더 매끄러운 격자는 매우 작은 기준값에 비해 B를 13.6% 높이지만, B는 여전히 B′보다 88.7%, 출판된 약 0.39 피크보다 88.2% 낮다. 도달 이동은 0.192 ms에 불과하다. 이 근사를 subdivision 7로 승격할 근거가 부족하다. 제어된 고정 깊이 대 ETOPO5 대비는 전체 표면 기하 voxelization을 더 분리해 조사할 필요를 보여준다.

#### 보존적 얕은 해양 voxelization

Opt-in conservative rasterization은 실제 해안선, 더 깊은 수심, 양의 육지 지형을 보존하면서 모든 ETOPO5 해양 column에 최소 하나의 5-km 해수 셀을 강제했다. Subdivision 5의 tangential material column 30,720개 중 4,258개 최상부 지하 셀을 암석에서 해수로 바꾸었으므로 metadata만 변경한 것이 아니라 누락된 얕은 물 사례를 실제로 시험했다.

| Polar optimized ETOPO5 | A / A′ 피크 | B / B′ 피크 | 0.12 s B / B′ 꼬리 | A/A′ / B/B′ 상대 RMS |
|---|---:|---:|---:|---:|
| 정확한 기복 | 0.97231 / 1.00000 | 0.04585 / 0.40613 | 0.00964 / 0.06858 | 34.0% / 734.0% |
| 최소 5-km 해양 column | 0.97081 / 1.00000 | 0.04580 / 0.40605 | 0.00966 / 0.06863 | 34.1% / 734.5% |

파형은 사실상 동일하다. 이전 고정 깊이 비교는 얕은 물 깊이만 분리한 것이 아니며, 양의 육지 기복을 해수면으로 평탄화하고 다른 Natural Earth 해안선도 사용했다. 강한 대비는 207-m 수신기 수심만이 아니라 전체 표면 기하 voxelization 때문에 생긴다. Conservative ocean occupancy는 Figure 5 보정으로 채택하지 않고 명시적 진단으로만 남긴다.

#### 표면 해상도 수렴 screen

다른 모델 입력을 바꾸지 않고 정확한 기복 polar 계산을 subdivision 5에서 6으로 높였다. 두 사례 모두 projected mesh-quality step 하나, 40,000 steps, CUDA `float64`, point material sampling을 사용했다.

| Subdivision | 표면 셀 | A / A′ 피크 | B / B′ 피크 | 0.12 s B / B′ 꼬리 | A/A′ / B/B′ 상대 RMS |
|---:|---:|---:|---:|---:|---:|
| 5 | 10,242 | 0.97231 / 1.00000 | 0.04585 / 0.40613 | 0.00964 / 0.06858 | 34.0% / 734.0% |
| 6 | 40,962 | 0.96277 / 1.00000 | 0.07607 / 0.36672 | 0.01533 / 0.06053 | 36.8% / 347.7% |
| 7 | 163,842 | 0.96355 / 1.00000 | 0.14159 / 0.35471 | 0.02820 / 0.05904 | 37.6% / 134.5% |

표면 셀 수가 4배씩 증가할 때 B 피크는 단조 증가하고 원거리 경로 불일치는 크게 줄어든다. 그러나 논문 해상도에서도 B는 출판된 약 0.39 피크보다 63.7%, B′보다 60.1% 낮다. 수평 해상도는 결과를 올바른 방향으로 움직이지만 출판 격자 크기에서 Figure 5를 재현할 만큼 빠르게 수렴하지 않는다.

#### 공식 Mesquite size-and-shape 최적화

후속 작업에서는 프로젝트 내부 one-step smoother를 공개된 최신 upstream Sandia Mesquite snapshot인 version 2.99 commit `7ae51c8e8617c67e63018c8a7effc0f5455f58b4`로 교체했다. [공식 Sandia archive](https://github.com/sandialabs/mesquite)에서 source를 다운로드하고 중첩 archive를 SHA-256으로 고정한다. Mesquite는 저장소에 복사하지 않고 외부 LGPL dependency로 유지한다.

논문은 Laplace 일관성을 위해 cell 면적과 위치를 모두 선택했다고 한다. 따라서 scale-invariant shape-only 목적함수는 예비 screen에서 Laplace 오차는 줄였지만 cell-area 및 edge-length variation을 키워 제외했다. 프로덕션 adapter는 `SphericalDomain`에서 Mesquite의 uniform ideal triangle size-and-shape target `TShapeSizeB1`을 `PMeanP(1)`로 aggregate하고 `TrustRegion`으로 최소화한다. Mesquite `FeasibleNewton` 구현은 실제 planar XY mesh용으로 문서화되어 구면에서는 사용하지 않는다. Dual이 polar pentagon인 두 vertex만 고정하고 나머지는 이동할 수 있다. Connectivity, vertex order, primal triangular cell, geodesic dual-grid 구현은 그대로다. 목적함수에는 ETOPO5 elevation, source/receiver coordinate, waveform metric이 들어가지 않는다.

Subdivision 7 검토 재실행에서 optimizer는 165.7 s에 수렴했다. 최대 great-circle vertex displacement는 0.015475 rad, Earth radius에서 98.6 km였다. 보고한 모든 지표가 개선됐다.

| Subdivision-7 격자 지표 | 원래 polar mesh | Mesquite | 감소 |
|---|---:|---:|---:|
| Primal-edge length CV | 0.065027 | 0.042243 | 35.0% |
| Primal-face area CV | 0.086445 | 0.062306 | 27.9% |
| Dual-cell area CV | 0.085150 | 0.062284 | 26.9% |
| Adjacent dual-area jump RMS | 0.017174 | 0.003643 | 78.8% |
| Maximum adjacent dual-area jump | 0.121137 | 0.085704 | 29.3% |
| Relative Laplace error, real `l=1` harmonic | `7.0163e-5` | `1.0790e-5` | 84.6% |
| Relative Laplace error, real `l=2` harmonic | `5.4227e-4` | `2.2976e-4` | 57.6% |

Laplace test는 FDTD curl과 같은 primal/dual metric factor가 유도한 circumcentric finite-volume scalar Laplacian의 area-weighted relative L2 error다. `l=1` spherical harmonic에서는 최적화가 거의 2차인 refinement convergence도 복원한다.

| Refinement | 원래 `l=1` 차수 | Mesquite `l=1` 차수 | 원래 `l=2` 차수 | Mesquite `l=2` 차수 |
|---|---:|---:|---:|---:|
| subdivision 5 → 6 | 1.505 | 1.993 | 1.080 | 1.211 |
| subdivision 6 → 7 | 1.503 | 1.992 | 1.037 | 1.112 |

그 다음 물질, 방사 격자, source, receiver, time step, 40,000-step duration을 바꾸지 않고 subdivisions 5, 6, 7에서 ETOPO5 propagation experiment를 반복했다. 모든 계산은 PyTorch CUDA `float64`를 사용했다. 이전 projected one-step 결과는 직접 대조군으로 남겼다.

| Mesh / subdivision | A / A′ 피크 | B / B′ 피크 | 0.12 s B / B′ 꼬리 | A/A′ / B/B′ 상대 RMS |
|---|---:|---:|---:|---:|
| Projected step / 5 | 0.97231 / 1.00000 | 0.04585 / 0.40613 | 0.00964 / 0.06858 | 34.0% / 734.0% |
| Mesquite / 5 | 0.97170 / 1.00000 | 0.34303 / 0.40516 | 0.06646 / 0.06814 | 31.4% / 23.8% |
| Projected step / 6 | 0.96277 / 1.00000 | 0.07607 / 0.36672 | 0.01533 / 0.06053 | 36.8% / 347.7% |
| Mesquite / 6 | 0.96689 / 1.00000 | 0.28091 / 0.36450 | 0.05441 / 0.06023 | 36.7% / 28.4% |
| Projected step / 7 | 0.96355 / 1.00000 | 0.14159 / 0.35471 | 0.02820 / 0.05904 | 37.6% / 134.5% |
| Mesquite / 7 | 0.97143 / 1.00000 | 0.31148 / 0.35580 | 0.06093 / 0.05922 | 37.4% / 18.5% |

이는 실질적인 개선이며 Laplace 일관성이 Maxwell propagation에도 이롭다는 Reference 13의 주장을 뒷받침한다. 특히 두 원거리 꼬리는 이제 상대 2.9%로 일치하고 level-7 B 피크는 2.20배 높아진다. 그러나 Figure 5 정량 통과는 아니다. 원거리 피크는 출판 플롯의 육안 목표보다 약 20% 및 9% 낮고 두 원거리 꼬리는 약 40% 낮으며 근거리 경로 RMS는 37.4%다. 2006년에 사용한 정확한 Mesquite 목적함수 parameter와 최종 좌표는 공개되지 않았으므로, 현재 결과는 좌표 동일성을 주장하는 것이 아니라 재현 가능한 복원이다.

#### 전도도 프로파일 민감도

보정 위치 subdivision-5 screen에서 ETOPO5 물질 주변 전리층을 변화시켰다. 모든 사례는 CUDA `float64`, 40,000 steps, 네 기록의 공통 정규화를 사용했다.

| Variant | A / A′ 피크 | B / B′ 피크 | 0.12 s A / A′ 꼬리 | 0.12 s B / B′ 꼬리 |
|---|---:|---:|---:|---:|
| 70 km, 3.33 km 기준 | 0.94981 / 1.00000 | 0.11120 / 0.39237 | 0.03388 / 0.03418 | 0.02238 / 0.06673 |
| 기준 높이 68 km | 0.95060 / 1.00000 | 0.10974 / 0.38851 | 0.03374 / 0.03438 | 0.02120 / 0.06231 |
| 기준 높이 72 km | 0.94915 / 1.00000 | 0.11276 / 0.39654 | 0.03411 / 0.03409 | 0.02363 / 0.07146 |
| Scale height 3.00 km | 0.94433 / 1.00000 | 0.11603 / 0.40923 | 0.03407 / 0.03343 | 0.02646 / 0.08270 |
| Scale height 3.67 km | 0.95584 / 1.00000 | 0.10687 / 0.37727 | 0.03455 / 0.03569 | 0.01977 / 0.05715 |

전리층 변화는 예상 방향으로 B′를 바꾸지만 모든 사례에서 B가 강하게 억제된다. 3.00-km scale height도 B를 0.11120에서 0.11603으로만 높이면서 B′는 출판 육안 추정치를 넘긴다. 따라서 표준 70-km/3.33-km Bannister profile을 유지한다. Parameter tuning으로 경로 선택적인 surface-geometry discretization error를 고칠 수 없다.

#### Fractional 방사 interface 실험

Opt-in material 실험에서 tangential-field midpoint sampling을 모든 방사 셀의 air/water/rock 두께 산술 평균으로 교체했다. 이는 정적 sheet conductance를 보존하지만 얇고 전도성이 높은 해수층의 주파수 의존 surface impedance는 보존하지 않는다. 보정 위치 CUDA `float64` 실행은 그 한계를 보여준다.

| 표면 subdivision | 표면 근처 방사 간격 | Interface | B / B′ 피크 | 0.12 s B / B′ 꼬리 |
|---:|---:|---|---:|---:|
| 5 | 5 km | Point | 0.11120 / 0.39237 | 0.02238 / 0.06673 |
| 5 | 5 km | Fractional | 0.11266 / 0.39157 | 0.02323 / 0.07028 |
| 4 | 5 km | Point | 0.29043 / 0.48461 | 0.06812 / 0.09994 |
| 4 | 5 km | Fractional | 0.12253 / 0.47570 | 0.01508 / 0.09288 |
| 4 | 250 m | Point | 0.30031 / 0.47117 | 0.06764 / 0.09794 |
| 4 | 250 m | Fractional | 0.26909 / 0.47164 | 0.04666 / 0.09775 |

250-m 방사 간격에서 point와 fractional 네 기록 파형은 RMS 6.15% 차이가 나고 B′ 피크는 비슷하며 B는 약 10% 다르다. 그러나 5-km 간격에서는 산술 fractional averaging이 B를 원래 point material보다 더 억제할 수 있다. 따라서 프로덕션 모델로 채택하지 않고 subdivision 7로 승격하지 않는다. 기능은 명시적 진단으로만 남기며 point sampling을 기본값으로 유지한다.

표면 subdivision을 4에서 5로 바꾸면 point-sampled B 피크가 0.29043에서 0.11120으로 이동하며, subdivision 4의 방사 세분화보다 영향이 훨씬 크다. 이는 수평 bathymetry/material aliasing이 다음 보정 대상임을 재확인한다. 올바른 subcell model은 방사 깊이의 bulk conductivity만이 아니라 각 수평 support에서 완전한 lossy update 또는 surface impedance를 평균해야 한다.

#### 측지 edge-support 물질 quadrature

두 번째 opt-in 진단은 각 tangential electric 자유도의 edge-dual diamond를 triangular support 네 개로 나누고 그 centroid에서 point-sampled ETOPO5 material을 평균했다. 한 edge midpoint에 의존하지 않으면서 정확한 표면 topology와 metric을 유지한다.

| Subdivision | Support | B / B′ 피크 | 0.12 s B / B′ 꼬리 |
|---:|---|---:|---:|
| 4 | Edge midpoint | 0.29043 / 0.48461 | 0.06812 / 0.09994 |
| 4 | Edge diamond | 0.29193 / 0.48430 | 0.06838 / 0.10050 |
| 5 | Edge midpoint | 0.11120 / 0.39237 | 0.02238 / 0.06673 |
| 5 | Edge diamond | 0.11150 / 0.39270 | 0.02244 / 0.06695 |

B 피크는 subdivision 4에서 0.5%, subdivision 5에서 0.3%만 변한다. 따라서 한 edge support의 local quadrature는 subdivision에 따른 큰 경로 차이를 제거하지 못하며 level 7로 승격하지 않는다. 남은 alias는 전역적이다. 서로 다른 표면 refinement가 binary 5-km water/rock column의 서로 다른 연속 경로로 파를 전달한다. 이 column을 바꾸어 논문을 재현하려면 공개되지 않은 정확한 optimized cell coordinate 또는 명시적으로 공개한 ocean-column approximation이 필요하며, local metric correction으로는 불가능하다. 이후 공식 Mesquite 복원은 이 alias를 크게 줄이지만 제거하지는 않는다.

## Figure 6: 주간 감쇠

![출판된 Figure 6과 재현한 Figure 6](images/simpson-taflove-2006-fig-6-comparison.png)

논문의 지시에 따라 각 수신기 기록을 post-overshoot zero crossing에서 자른다. 검토한 적응형 절단 길이는 A 23,464, A′ 22,663, B 24,508, B′ 24,531 samples다. 32,768-point DFT로 50.862630–498.453776 Hz의 고정 bin 45개를 얻는다. 기준선은 플롯 pixel에 맞춘 것이 아니라 같은 70 km 높이와 3.33 km scale height로 Bannister 주간 감쇠식을 평가한다.

| 경로 | 평균 절대 오차 | 최대 절대 오차 | 최악 주파수 | ±0.5 dB/Mm 판정 |
|---|---:|---:|---:|---:|
| A–B, east | 0.921 dB/Mm | 3.020 dB/Mm | 437.419 Hz | **FAIL** |
| A′–B′, west | 0.284 dB/Mm | 2.125 dB/Mm | 498.454 Hz | **FAIL** |

서쪽 곡선은 평균적으로 출판 추세를 따르지만 대역 상단에서 지점별 허용 오차를 위반한다. 동쪽 곡선은 ETOPO5 point-sampled material이 B를 억제하여 체계적으로 감쇠가 과도하다. 고정 깊이 Natural Earth material에서는 동/서 평균 오차가 0.423/0.425 dB/Mm가 되고 두 경로가 거의 같아지지만 최대 오차는 2.933/4.370 dB/Mm로 남는다. 따라서 수심 이산화는 큰 동서 분리를 설명하고, 남은 상위 대역 진동은 2004 검증에 기록한 고주파 공간 분산 잔차와 부합한다.

이전에 기록한 native-grid Figure 6 결과와 비교하면, 검토한 공통 트레이스의 동쪽 MAE는 2.064에서 0.921 dB/Mm, 최대는 5.026에서 3.020 dB/Mm로 개선된다. 서쪽 MAE는 0.277에서 0.284 dB/Mm로, 최대는 1.650에서 2.125 dB/Mm로 악화된다. 이는 solver만의 깨끗한 비교가 아니라 구성 일관성 개선이다. 이전 Mesquite 트레이스를 같은 적응 절차로 재분석하면 0.914/2.976 및 0.276/1.990 dB/Mm이므로, 고정 mesh와 분석 설정에서는 검토한 solver 변경이 Figure 6 정확도를 개선하지 않는다.

### Spectral-window 민감도

보정 위치 subdivision-5 진단은 각 적응형 post-overshoot zero-crossing 절단을 유지하면서 마지막 rectangular window를 cosine taper로 교체했다. Propagation model을 바꾸지 않고 hard-cutoff leakage를 분리한다.

| Terminal window | East MAE / 최대 | West MAE / 최대 |
|---|---:|---:|
| Rectangular | 4.033 / 6.419 dB/Mm | 1.790 / 4.164 dB/Mm |
| 2% cosine tail | 3.999 / 6.609 dB/Mm | 1.813 / 4.377 dB/Mm |
| 5% cosine tail | 4.071 / 7.705 dB/Mm | 1.862 / 5.119 dB/Mm |
| 10% cosine tail | 4.518 / 7.056 dB/Mm | 2.596 / 8.184 dB/Mm |
| 20% cosine tail | 4.566 / 8.405 dB/Mm | 2.358 / 7.031 dB/Mm |

어떤 taper도 지점별 최대 오차를 개선하지 않으며, 긴 taper일수록 물리적으로 분리된 펄스를 더 왜곡한다. Rectangular window를 유지하고 terminal DFT leakage를 Figure 6 잔차의 주원인에서 제외한다.

## Figure 7: 유전 레이더 응답

![출판된 Figure 7과 재현한 Figure 7](images/simpson-taflove-2006-fig-7-comparison.png)

원래 프로덕션 실행은 Clam Lake 송신기를 대척점 46.46° S, 89.15° E에 배치했고 유전 수신기는 요청한 Alaska 위치에 남겼다. 그 결과는 폐기했다. 아래 패널과 지표는 완전한 보정 위치 기준/이상체 쌍을 사용한다.

검토한 tangential curve의 중앙값은 −43.253 dB로 기준 zero crossing을 제외하면 대체로 −25 dB보다 훨씬 낮지만, 특이하지 않은 sample 중 −25 dB 미만인 비율은 92.469%다. 중앙 억제 기준은 통과하나 “almost every time”을 95%로 해석한 보고서 기준에는 미달한다.

Radial curve는 출판 스케일이나 형태를 재현하지 못한다. 거의 전체 window에서 플롯의 +30 dB 상한보다 높으며 중앙값 +126.000 dB, 95th percentile +147.896 dB다. 방사/접선 중앙 이점은 약 45 dB가 아니라 165.903 dB다.

| 지표 | 논문 결과 | 재현 | 판정 |
|---|---:|---:|---:|
| Median pointwise `ΔHtan` | −25 dB 미만 | −43.253 dB | **PASS** |
| `ΔHtan < −25 dB` 비율 | 최소 95% | 92.469% | **FAIL** |
| Pointwise `ΔHr` 스케일 | 약 +20 dB에 도달 | 중앙값 +126.000 dB | **FAIL** |
| Median `ΔHr−ΔHtan` | 약 45 dB | 165.903 dB | **FAIL** |

절대 field로 메커니즘을 확인할 수 있다.

| 물리량 | 피크 크기 |
|---|---:|
| 기준 `Htan` | `1.5553e-8 A/m` |
| Oil-model `Htan` | `1.5478e-8 A/m` |
| 절대 `Htan` 차이 | `1.2661e-10 A/m` |
| 기준 `Hr` | `1.0609e-16 A/m` |
| Oil-model `Hr` | `3.1418e-10 A/m` |
| 절대 `Hr` 차이 | `3.1418e-10 A/m` |

보정된 짧은 propagation path는 폐기된 대척점 실행보다 기준 tangential field를 세 자릿수 이상 높인다. 검토 쌍에서 radial scattered-field peak는 tangential scattered-field peak보다 7.90 dB 강하다. 겉으로 보이는 radial advantage는 기준 `Hr`가 radial scattered field보다 약 6자릿수 작은 데서 지배된다. Caption의 pointwise normalization 대신 본문의 peak normalization을 적용하면 `ΔHtan` −41.787 dB, `ΔHr` +129.430 dB가 되어 어느 해석에서도 출판된 +20 dB 스케일을 재현하지 못한다.

Figure 7은 **정량 실패**지만, 매설 전도도 이상체가 주된 tangential reference field를 약하게 교란하면서 radial magnetic component를 만들 수 있다는 점은 정성적으로 확인한다.

### 이전 Figure 7 프로덕션 쌍 대비 변화

| 지표 | 이전 | 검토 재실행 | 변화 |
|---|---:|---:|---:|
| Median pointwise `ΔHtan` | −36.829 dB | −43.253 dB | **6.424 dB 더 억제** |
| `ΔHtan < −25 dB` 비율 | 97.522% | 92.469% | 5.053 percentage points 악화 |
| Median pointwise `ΔHr` | +97.941 dB | +126.000 dB | 28.059 dB 악화 |
| Median radial advantage | 136.940 dB | 165.903 dB | 28.963 dB 악화 |
| 기준 실행 시간 | 2,201.4 s | 1,087.8 s | **50.6% 단축** |
| 이상체 실행 시간 | 1,819.9 s | 1,302.2 s | **28.4% 단축** |

Tangential median과 실행 시간은 개선됐지만 radial mismatch와 tangential coverage criterion은 악화됐다. Figure 7의 어떤 합격 판정도 개선되지 않는다.

### 프로덕션 실행 후 정확성 및 불확실성 gate

원래 tangential ground-line deposition은 요청한 0-m source를 Figure 7 subgrid에서 표면 아래 625 m에 있는 최근접 TE-r midpoint에 맞췄다. 이제 −625-m와 +2,500-m 평면 사이에서 0.8/0.2 weight로 adjoint radial interpolation하여 정확한 고도와 전류 모멘트를 모두 보존한다. Subdivision-5 paired test는 이것이 필요한 정확성 수정이지만 radar discrepancy 원인은 아님을 보여준다.

| Source / receiver / Shield | Peak-normalized `ΔHr` | Median pointwise `ΔHr` | Median advantage | 기준 `Hr` 피크 |
|---|---:|---:|---:|---:|
| Snapped −625 m / face / 2,500 km | +94.972 dB | +84.885 dB | 151.750 dB | `7.176e-16 A/m` |
| Exact 0 m / face / 2,500 km | +95.040 dB | +85.085 dB | 151.944 dB | `7.728e-16 A/m` |
| Exact 0 m / local-linear / 2,500 km | +70.511 dB | +59.617 dB | 125.385 dB | `3.065e-15 A/m` |
| Exact 0 m / local-linear / no Shield | +70.443 dB | +58.971 dB | 124.364 dB | `1.083e-15 A/m` |

Subdivision 5에서 containing-face `Hr` sample을 정확한 유전 좌표의 four-face local-linear reconstruction으로 바꾸면 정규화된 radial 결과가 24.5 dB 개선된다. 방사 보간만으로 수평 face-center offset을 보정할 수 없으므로 정확성을 위해 이 복원을 채택했다. 그러나 target에 fit한 해결책은 아니다. 이전 subdivision-7 point-sampled 실행에서는 pointwise median이 +95.691에서 +97.941 dB, peak-normalized 결과가 +103.991에서 +112.300 dB로 반대 방향으로 이동했다. 두 해상도에서 반대 변화가 나타나는 것은 출판 결과로 수렴하는 것이 아니라 강한 수평 sampling sensitivity임을 드러낸다. 근사 Shield 제거는 subdivision-5 normalized radial peak를 0.07 dB만 바꾸므로, 공개되지 않은 Shield 경계는 절대 스케일에는 영향을 주지만 정규화 오차의 주원인은 아니다.

| Subdivision-7 `Hr` 수신기 | Peak-normalized `ΔHr` | Median pointwise `ΔHr` | Median advantage | 기준 `Hr` 피크 |
|---|---:|---:|---:|---:|
| Containing face | +103.991 dB | +95.691 dB | 137.450 dB | `4.7439e-17 A/m` |
| 이전 exact local-linear, point-sampled oil | +112.300 dB | +97.941 dB | 136.940 dB | `7.2689e-17 A/m` |
| 검토 exact local-linear, conservative oil | +129.430 dB | +126.000 dB | 165.903 dB | `1.0609e-16 A/m` |

논문은 직교하는 300-A ground line 두 개를 명시하지만 상대 polarity는 밝히지 않는다. North와 east basis simulation을 분리하면 target에 맞춘 조합을 선택하지 않고 선형 합성이 가능하다.

| Source basis | Peak-normalized `ΔHtan` | Peak-normalized `ΔHr` | 절대 `ΔHr/ΔHtan` |
|---|---:|---:|---:|
| North only | −47.743 dB | +70.956 dB | −6.467 dB |
| East only | −46.111 dB | +72.670 dB | −7.228 dB |
| North + east | −66.515 dB | +70.511 dB | +3.590 dB |
| North − east | −46.585 dB | +71.865 dB | −6.878 dB |

모든 basis에서 절대 scattered component는 약 7 dB 이내이며 서로 비슷하다는 논문의 설명과 부합한다. Source polarity는 tangential cancellation을 통해 겉보기 advantage를 크게 바꾸지만 네 radial 결과 모두 논문의 약 +20 dB보다 50 dB 이상 높다. 따라서 source convention은 공개된 불확실성으로 유지하고 fit parameter로 사용하지 않는다.

## 실패 분석과 수정 작업

최종 프로덕션 결과를 채택하기 전에 다음 구현 문제를 찾아 수정했다.

1. Unsigned spherical-triangle test가 요청 방향과 대척 방향을 모두 허용했다. 이제 후보 face를 요청 방향과의 양의 alignment로 순위화한다. Figures 5–6에서 B/B′를 분리하고 Figure 7 송신기를 반대 반구에서 Clam Lake로 되돌린다. 회귀 테스트는 비적도 송신기와 유전 수신기를 포함한 모든 논문 위치를 검사한다.
2. Solver는 radial current만 주입하고 `Er`만 기록할 수 있었다. Tangential ground-line source와 backend-native `Hr`/signed-`Htan` recorder를 추가했다. 기록은 실행이 끝날 때까지 CUDA device에 남는다.
3. ETOPO5 layered lithosphere에는 local anomaly를 넣을 수 없었다. 공통 spherical-volume anomaly mechanism을 기복, 해양, 깊이 profile을 바꾸지 않고 이 물질로 확장했다. 후속 material audit에서 넓은 lateral cap이 해수까지 곱할 수 있음을 발견하여 Shield와 oil anomaly를 background conductivity가 `0.01 S/m` 이하인 곳으로 제한하고 water layer는 그대로 둔다.
4. 1.25 km subgrid는 Figures 5–6의 3 μs보다 conservative time step을 작게 만들었다. Level-5 CUDA float64 paired experiment에서 Courant factor 0.4와 1.0의 field maximum은 상대 약 `1e-8`, perturbation metric은 0.001 dB 이내로 일치했다. 안정적인 1.0 설정은 프로덕션 실행을 193,759에서 77,542 steps로 줄인다.
5. 첫 tangential source projection은 방향은 보존했지만 subcell line moment는 보존하지 않았다. 각 edge를 line-length/edge-length ratio로 scale하여 line direction을 유지하면서 절대 field를 수정했다. 최종 source는 포함 face의 방향 edge 세 개에 분배하고 두 radial source plane 사이에서 adjoint-linear stagger한다.
6. 원래 mesh orientation은 논문과 달리 지리 극점에 hexagonal cell을 뒀다. 기본 rigid rotation은 topology나 intrinsic metric을 바꾸지 않고 두 극점에 degree-five cell center를 맞춘다.
7. 논문의 정확한 Mesquite coordinate와 objective parameter는 공개되지 않았다. 최신 공개 Mesquite 2.99 snapshot을 offline optimizer로 통합했다. Uniform spherical size-and-shape objective는 두 polar pentagon만 고정하면서 추적한 모든 mesh-quality 및 Laplace metric을 개선한다. ETOPO5, source, receiver, waveform 정보는 사용하지 않는다. 최적화 coordinate archive는 각 FDTD 실행 전에 검증하고 topology 변경 없이 모든 geometry를 다시 만든다.
8. Figure 7은 이전에 ETOPO5 기복이 활성화되어도 source, receiver, buried body를 sea level 기준으로 배치했다. 기본값은 이제 세 요소 모두 local terrain을 일관되게 기준으로 하며 명시적인 sea-level placement는 제어 비교로 남긴다.
9. Binary point sampling은 명목 4,800 km² oil body를 level 7에서 7,013.6 km²로 만들고 낮은 level에서는 완전히 사라지게 했다. 기본 conservative rasterizer는 TM dual cell과 TE edge diamond에서 각각 4,800 km²를 보존한 뒤 radial cell-overlap fraction을 적용한다. Point sampling은 명시적 대조 모드로 남긴다.
10. Radial boundary를 명시적으로 PEC로 식별하고, 회귀 테스트에서 ghost-cell curl, second-order conductive decay, stiff-loss passivity, native/polar TM·TE CFL spectrum을 각각 검증한다.
11. Magnetic timestamp에 half-step offset을 포함하고 archive를 atomic write하며, reference/anomaly 비교는 mesh coordinate, material, source, backend, dtype, configuration이 들어간 canonical run signature가 일치해야 한다.
12. CUDA dual-cell circulation은 atomic scatter accumulation 대신 고정 degree-five/six incidence sum을 사용한다. 반복한 compiled float64 실행에서 네 field array가 bitwise identical이다.
13. Dense edge-by-layer metric tensor를 separable spherical metric factor로 교체했다. Subdivision 5, radial cell 24개에서 RTX 3060 persistent allocation은 방정식을 바꾸지 않고 89.4에서 38.0 MB로 줄며, 120-step float64 비교는 roundoff scale에서만 다르다.
14. 정확한 ETOPO5 pole sample은 이제 해당 latitude row 평균을 사용하여 polar pentagon의 정의되지 않은 longitude dependency를 제거한다. 공식 south-pole row 평균은 2,810.375 m다.

지리 보정 전에 수행한 coarse source-deposition 및 resolution 진단은 구현 테스트로 git history에 남기지만 대척 송신기를 사용했으므로 수치 radar metric은 이 보고서에서 제외한다. 최종 Figure 7 판정은 새 paper-scale corrected-location pair만 사용한다.

보관한 level-7 프로덕션 쌍은 binary point sampling을 사용하여 선택한 dual cell 두 개의 합계 면적이 기하학적 4,800 km²가 아니라 7,013.6 km²였다. 현재 기본값은 이를 fractional area support로 교체했다. 같은 TM cell 두 개와 TE support 다섯 개를 선택하지만 fractional occupancy를 부여하여 각 staggered grid의 적분 면적을 정확히 4,800 km²로 만든다. 재귀적으로 subdivide한 geodesic topology를 바꾸거나 conductivity를 tuning하지 않고 공개된 수평 면적 오차를 해결한다.

보정한 Figure 7 절대 field는 solver가 radial scattered field를 실제 생성함을 보여준다. 검토한 conservative-area pair에서 그 peak는 tangential scattered-field peak보다 7.90 dB 크지만, 보고된 165.90 dB normalized advantage는 거의 0인 reference `Hr`로 나눈 값이 지배한다. 논문은 차이가 정확한 optimized cell position, ground-line phase/deposition, Canadian Shield mask, conductivity realization, oil-body voxelization, 또는 내부적으로 모순된 normalization description 중 어디서 생기는지 판단할 정보를 충분히 제공하지 않는다. 어떤 입력도 문서화되지 않은 방식으로 tuning하지 않았다.

Figures 5–6에서 고정 깊이 material은 동서 대칭을 복원하지만 지점별 고주파 감쇠 허용 오차는 해결하지 못한다. Float64 precision, DFT zero-padding, source staggering, radial metric weighting, horizontal refinement는 이 연구와 2004 campaign에서 이미 분리해 시험했다. 현재 geodesic dual grid는 유지해야 하며 논문의 정확한 Hermance-derived 3-D conductivity realization은 공개되지 않았다. 따라서 최종 bathymetry 및 고주파 불일치는 tuning하여 없애지 않고 보고한다.

## 재현 명령

최종 Figure 5 결과는 먼저 고정된 Mesquite source를 build하고 level-7 coordinate archive를 만든 뒤 ETOPO5 실행에서 사용한다.

```bash
python tools/mesquite/build.py --build-dir build/mesquite

.venv/bin/python -m ionosphere_fdtd.mesh_optimize_cli \
  --subdivision 7 --orientation polar --fixed-vertices poles \
  --executable build/mesquite/bin/ionosphere-mesquite-optimize \
  --movement-tolerance 1e-10 --max-iterations 200 \
  --output /tmp/ionosphere-mesquite-level-7.npz

.venv/bin/python -m ionosphere_fdtd.simpson_taflove_2004_cli \
  --subdivision 7 --mesh-orientation polar \
  --mesh-coordinates /tmp/ionosphere-mesquite-level-7.npz \
  --minimum-ocean-depth-km 0 \
  --steps 40000 --material etopo5 \
  --etopo5-path data/ETOPO5.DAT --backend torch --device cuda:0 \
  --dtype float64 --dft-window adaptive \
  --ionosphere-reference-height-km 70 \
  --ionosphere-scale-height-km 3.3333333333333335 --torch-compile \
  --synchronize-every 1024 \
  --output-dir /tmp/ionosphere-verification-20260805/st2006-fig56-l7

.venv/bin/python -m ionosphere_fdtd.simpson_taflove_2006_cli \
  figures-5-6 \
  --traces /tmp/ionosphere-verification-20260805/st2006-fig56-l7/simpson-taflove-2004-traces.npz \
  --output-dir /tmp/ionosphere-verification-20260805/st2006-fig56-l7/figures-5-6
```

고정 깊이 분리 실행은 `--material etopo5`를 `--material natural-earth`로 바꾸고 `--etopo5-path`를 생략한다. Conservative shallow-ocean 진단은 `--minimum-ocean-depth-km`만 0에서 5로 바꾼다. Subdivision-5 ionosphere sensitivity 사례는 ETOPO5 material을 유지하고 위 표의 reference 또는 scale height만 바꾼다. Figure 6은 Figure 5와 같은 현재 트레이스에서 생성한다.

Figure 7 paired run은 다음과 같다.

```bash
.venv/bin/python -m ionosphere_fdtd.simpson_taflove_2006_cli radar-run \
  --case reference --subdivision 7 --material etopo5 \
  --etopo5-path data/ETOPO5.DAT --backend torch --device cuda:1 \
  --dtype float64 --torch-compile --courant 1.0 \
  --source-basis both --vertical-reference terrain \
  --horizontal-anomaly conservative-nearest \
  --receiver-support local-linear --synchronize-every 1024 \
  --output /tmp/ionosphere-verification-20260805/st2006-fig7-reference.npz

.venv/bin/python -m ionosphere_fdtd.simpson_taflove_2006_cli radar-run \
  --case anomaly --subdivision 7 --material etopo5 \
  --etopo5-path data/ETOPO5.DAT --backend torch --device cuda:0 \
  --dtype float64 --torch-compile --courant 1.0 \
  --source-basis both --vertical-reference terrain \
  --horizontal-anomaly conservative-nearest \
  --receiver-support local-linear --synchronize-every 1024 \
  --output /tmp/ionosphere-verification-20260805/st2006-fig7-anomaly.npz

.venv/bin/python -m ionosphere_fdtd.simpson_taflove_2006_cli analyze-radar \
  --reference /tmp/ionosphere-verification-20260805/st2006-fig7-reference.npz \
  --anomaly /tmp/ionosphere-verification-20260805/st2006-fig7-anomaly.npz \
  --figure /tmp/ionosphere-verification-20260805/st2006-figure-7.png
```

## 재현성 한계

- NOAA ETOPO5 기복은 보관 파일 및 2004 보고서에 기록한 checksum과 정확히 일치하지만, 논문의 완전한 3차원 Hermance conductivity mapping은 구할 수 없다.
- 정확한 Canadian Shield 경계와 oil-field footprint shape는 공개되지 않았다. 구현은 전자에 공개한 cap, 후자에 원형 equal-area footprint를 사용한다. Conservative fractional rasterization은 두 electric-field grid에서 공개된 4,800 km² 면적을 보존하지만 공개되지 않은 footprint shape를 복원할 수 없다.
- 논문은 optimized geodesic grid를 사용한다. 요구에 따라 이 프로젝트는 기존의 recursively subdivided geodesic dual-grid topology를 유지한다. Rigid polar orientation은 pentagonal cell center를 두 지리 극점에 둔다. 고정된 Mesquite 2.99 복원은 구면에서 문서화된 uniform size-and-shape objective를 사용하고 두 vertex를 고정한다. 논문은 정확한 Mesquite objective parameter, constraint, termination criterion, final coordinate를 공개하지 않으므로 복원한 vertex가 논문 격자와 동일하다고 가정할 수 없다.
- Figure 7은 source phase, Gaussian center time, formal error norm을 정의하지 않는다. 시뮬레이션은 envelope center보다 Gaussian `1/e` half-width 세 개 앞에서 시작하며 표시 시간은 그 center 기준이다.
- 모순된 Figure 7 normalization 설명 때문에 유일한 문자 그대로의 재현이 불가능하다. 선택한 pointwise 정의만이 출판된 spike와 부합한다.

## 최종 결론

현재 구현은 Figure 5 시점과 형태를 재현하지만 네 상대 진폭을 모두 재현하지 못한다. Figure 6 감쇠의 큰 추세는 따르지만 지점별 ±0.5 dB/Mm 주장을 만족하지 못한다. Figure 7의 +20 dB radial perturbation이나 약 45 dB sensitivity advantage도 재현하지 못한다. 따라서 최종 판정은 **FAIL**이다.

수정 작업으로 재사용 가능하고 시험된 기능들을 확보했다. 물리적으로 scale된 horizontal ground-line source, CUDA-native radial/tangential magnetic recording, ETOPO5 layered material의 buried anomaly, 보호된 water layer, polar pentagon alignment, 고정 Sandia Mesquite build와 spherical size-and-shape optimization pipeline, Laplace-consistency metric, conservative ocean-column diagnostic, conservative buried-body support, terrain-relative radar geometry, deterministic CUDA circulation, 명시적 PEC/CFL/loss invariant, 재현 가능한 Figure 5–7 analysis CLI가 포함된다. Precision, time-step stability, source moment, radial metric weighting, ionosphere-profile sensitivity를 시험했다. Geographic locator 결함을 수정했고 geographic, terrain-reference, conservative-area 보정의 영향을 받는 모든 paper-scale production trace를 다시 계산했다.

Figure 5에서 고정 깊이 geometry는 대칭을 복원한다. 공식 Mesquite optimization은 ETOPO5 결과를 실질적으로 개선하여 level-7 원거리 경로 RMS 차이를 134.5%에서 18.5%로 줄이고 B를 0.14159에서 0.31148로 높이며 거의 2차인 `l=1` Laplace convergence를 복원한다. 그러나 37.4% 근거리 경로 불일치나 약 40% 낮은 원거리 꼬리는 해결하지 못한다. 산술 radial fraction, local edge-support quadrature, conservative 5-km ocean occupancy도 충분하지 않다. 따라서 전체 ETOPO5 surface/lithosphere voxelization과 복원 격자 및 공개되지 않은 논문 전용 optimized coordinate의 차이가 가장 강하게 확인된 한계다. 얕은 수심만이 지배 원인이라는 가설은 더 이상 지지되지 않는다. Frequency-dependent ground surface impedance는 필수 geodesic grid를 유지하면서 물리적 수렴을 개선할 수 있지만, 논문이 발표한 bulk-cell algorithm과 달라진다. Figure 6에는 알려진 고주파 spatial-dispersion residual도 남아 있다. Figure 7은 optimized cell position, 정확한 3-D lithosphere conductivity, Canadian Shield mask, 정확한 oil-field footprint shape, source phase/deposition, 일관된 normalization definition처럼 논문에서 복원할 수 없는 입력의 제약을 받는다. 보정된 지리 `Hr` receiver도 subdivisions 5와 7에서 반대 방향으로 변하여, 잔차가 제거 가능한 face-center observation artifact가 아님을 확인한다. 문서화되지 않은 tuning으로 출판 Figure 7 값에 강제로 맞추는 것은 유효한 검증이 아니다.
