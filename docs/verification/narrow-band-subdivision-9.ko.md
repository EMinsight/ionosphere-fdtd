# Subdivision-9 협대역 직접 측정

[English original](narrow-band-subdivision-9.md)

## 가설

Subdivision 6–8에서 추정한 비영(非零) 수평 연속체 위상속도 오차가 외삽
오류일 수 있다. 이 추정이 타당하다면 subdivision-9 직접 측정도 예측한
세분 추세를 따라야 한다.

## 방법

Raised-cosine ramp를 적용한 400 Hz 전류로 균일 지구 검증 모델을 구동했다.
네 방위각마다 30°, 45°, 60°, 75°, 90°의 receiver 다섯 개를 표본화했다.
60 ms 이후 온전한 열 주기를 `sum Er(t) exp(-j 2 pi f t)`로 online
누산했으며 receiver history는 저장하지 않았다. 구면 spreading을 보정한
뒤 복소 진폭을 공간 방향으로 fitting했다.

Subdivision 9 결과를 해석하기 전에 subdivision 7과 8에서 기존 broadband
multi-receiver 결과와 협대역 방법을 비교했다. Level 9에서는 논문의 `3 us`
시간 간격이 보수적 CFL 한계 `2.963467 us`를 넘으므로 `2.9 us`를 사용했다.
Level 7–8은 `3 us`를 유지했다.

균일 물질 계수가 수평 방향으로 정확히 같음을 확인한 뒤 방사 profile 한
행만 저장하고 broadcast했다. 이 정확한 저장 압축은 field update를 바꾸지
않으며, level-9 persistent storage를 줄여 설치된 12 GiB GPU에서 실행할 수
있게 한다. 계산에는 CUDA `float32`를 사용했다. 이전 broadband CUDA
`float64` 실행과 비교하면 이 precision과 1.23% 시간 간격 차이가 제약이다.

## 대조군

400 Hz에서 level 8 협대역 결과는 broadband 결과와 감쇠 `0.02311 dB/Mm`,
위상속도 `0.0007634 c`만큼 다르다. 복소 공간회귀 RMS는 `0.003469`다.
Level 7 위상속도 차이는 `0.0000028 c` 이내지만 감쇠는 `0.1833 dB/Mm`
차이가 난다. 따라서 결정 단계에서는 위상 수렴이 더 신뢰할 수 있는
관측량이다.

## 결과

| Subdivision | 감쇠 (dB/Mm) | 위상속도 (c) | 복소 RMS | 실행 시간 | 최대 GPU 메모리 |
|---:|---:|---:|---:|---:|---:|
| 7 | 7.32628 | 0.848986 | 0.014967 | 616.6 s | 0.605 GB |
| 8 | 7.15032 | 0.855947 | 0.003469 | 413.1 s | 1.800 GB |
| 9 | 7.10897 | 0.857661 | 0.000990 | 1991.6 s | 7.164 GB |

Level 7–9에서 관측한 수렴 차수는 감쇠 2.089, 위상속도 2.022다. Level
7–8만으로 만든 2차 level-9 예측은 `7.10633 dB/Mm`, `0.857687 c`다. 직접
결과와의 차이는 각각 `0.00264 dB/Mm`, `-0.0000259 c`에 불과하다.

400 Hz Bannister 값은 `7.05500 dB/Mm`, `0.873132 c`다. Level-9 직접
위상 잔차는 여전히 `-0.015471 c`다. 기존 broadband level 6–8 오차를
별도로 fitting하면 level-9 오차 `0.016376 c`와 연속체 극한 `0.015910 c`를
예측한다. 직접 오차는 이 예측보다 `0.000906 c` 작지만 명확히 0이 아니다.

## 결정

Level-9 직접 측정은 약 2차의 수평 세분 추세를 확인했으며, 400 Hz 부근에
비영 수평 연속체 위상 offset이 남는다는 결론을 뒷받침한다. 수평 해상도는
거친 격자 오차의 상당 부분을 설명하지만 추가 세분만으로 Bannister
위상속도에 도달할 가능성은 낮다.

이 결과는 비용이 큰 전체 broadband level-9 논문 재현을 정당화하지
않는다. Level 8에서 9로 가며 줄어든 양보다 남은 offset이 이미 훨씬 크기
때문이다. 우선순위가 높은 상단 대역 한 주파수로 Stage 5 결정 조건을
충족했다. 100 Hz와 250 Hz는 각각 긴 GPU 점유가 추가로 필요하고 400 Hz
보다 상단 대역 연속체 문제를 직접 판별하지 못하므로 실행하지 않았다.

## 다음 실험

검증을 계속한다면 400 Hz에서 최소 규모의 Stage 6 merged
latitude–longitude 대조군으로 진행한다. 균일 지구, receiver geometry,
lock-in estimator를 그대로 사용해 grid family 분산만 의도적으로 바꿔야
한다.

## 검증

[`artifacts/narrow-band/`](../../artifacts/narrow-band/)에 복소 진폭,
방위각별 fitting, 실행 시간과 메모리 metadata, 집계 CSV, JSON summary,
수렴 plot을 보관했다. 전체 테스트 결과는 `240 passed, 2 skipped`이며
`git diff --check`도 통과했다.
