# Simpson–Taflove 2004 Fig. 7·8 기준 및 수정 검증 결과

> 정량 검증 상태: **실패**

검증일: 2026-08-03 (Asia/Seoul)

## 목적

Simpson과 Taflove의 2004년 논문에 제시된 파라미터로 Fig. 7의 네 수신점
시간파형과 Fig. 8의 주파수별 전파 감쇠율을 계산하여 현재 geodesic FDTD
구현의 재현 가능성을 확인했다.

## 재현 명령

```bash
uv run --extra pytorch --extra visualization ionosphere-verify-2004 \
  --subdivision 7 \
  --steps 35000 \
  --material natural-earth \
  --backend torch \
  --device mps \
  --dtype float32 \
  --torch-compile \
  --output-dir artifacts/simpson-taflove-2004/level-7
```

새 CLI는 실행할 때마다 그림과 함께 `verification-report.md`를 자동으로
생성한다. 이 문서는 보고서 자동 생성 기능을 추가하기 전에 수행한 기준
실행을 보존한 것이다.

## 논문 파라미터

| 항목 | 적용값 |
|---|---:|
| 계산 영역 | 해수면 기준 -100–100 km |
| 방사 셀 | 40개, 5 km 간격 |
| 시간 간격 | 3.0 μs |
| 시간 스텝 | 35,000 |
| 소스 위치 | 적도, 47° W |
| 소스 길이 | 수직 5 km 셀 |
| Gaussian `1/e` full width | `480 Δt` |
| Gaussian center | `960 Δt` |
| A / A′ | 소스에서 동/서 방향 45° |
| B / B′ | 소스에서 동/서 방향 90° |
| Fig. 8 유효 주파수 | 50–500 Hz |

수신기별 DFT 절단 길이는 A 22,849, B 24,165, A′ 22,737, B′ 25,023
samples로 설정했다. 논문에는 소스 전류 진폭이 명시되지 않아 Fig. 7은
1 A로 정규화했다. Fig. 8의 스펙트럼 비율은 이 진폭과 무관하다.

## 실행 환경

| 항목 | 값 |
|---|---:|
| 표면 셀 | 163,842 |
| 방사 셀 | 40 |
| backend | PyTorch |
| device | Apple MPS |
| dtype | float32 |
| compiled step | 활성화 |
| 실행 시간 | 609.5 s |
| 재료 모델 | Natural Earth 110-m + Fig. 6 층상 근사 |

## 결과

### Fig. 7 시간파형

음의 주펄스와 뒤따르는 slow-tail 형태는 정성적으로 나타났다. 그러나
주펄스 도달이 논문보다 늦고, 논문에서 지각 구조 차이로 분리되는 동·서
파형이 현재 결과에서는 거의 겹쳤다.

![Figure 7 level-7 verification](../../artifacts/simpson-taflove-2004/level-7/simpson-taflove-2004-fig-7.png)

### Fig. 8 감쇠율

Fig. 8의 이전 결과 기준선은 논문 그림에서 판독한 log-log 근사식
`0.0265 f^0.938`을 사용했다. 원시 Bannister 데이터는 아니다.

![Figure 8 level-7 verification](../../artifacts/simpson-taflove-2004/level-7/simpson-taflove-2004-fig-8.png)

| 경로 | 평균 절대 오차 | 논문의 보고 범위 | 판정 |
|---|---:|---:|---:|
| A–B | 6.146 dB/Mm | 약 ±0.5 dB/Mm | 실패 |
| A′–B′ | 5.991 dB/Mm | 약 ±1.0 dB/Mm | 실패 |

중간 해상도인 subdivision 5에서도 각각 6.623 dB/Mm, 6.448 dB/Mm였으며
실행 시간은 51.6초였다. subdivision 7에서 오차가 소폭 감소했지만 논문의
정량 일치 범위에는 도달하지 못했다.

## 결론

현재 구현은 전 지구 ELF 전파의 핵심 시간영역 형태를 생성하지만 Fig. 7과
Fig. 8을 정량적으로 재현하지 못한다. 따라서 이 결과를 논문 재현 성공으로
사용하면 안 된다.

## float64 재검증 결과

Apple MPS가 PyTorch `float64`를 지원하지 않아 CUDA가 있는 Linux 시스템의
NVIDIA GeForce RTX 3060에서 같은 level-7 격자와 35,000스텝을 재실행했다.
실행 시간은 1,083.6초였으며 PyTorch compiled step을 사용했다.

```bash
uv run --extra pytorch --extra visualization ionosphere-verify-2004 \
  --subdivision 7 --steps 35000 \
  --material natural-earth \
  --backend torch --device cuda:0 --dtype float64 --torch-compile \
  --output-dir artifacts/simpson-taflove-2004/level-7-float64-cuda
```

[전체 float64 실행 보고서](../../artifacts/simpson-taflove-2004/level-7-float64-cuda/verification-report.md)

| dtype | A–B 평균 절대 오차 | A′–B′ 평균 절대 오차 |
|---|---:|---:|
| float32 | 6.146 dB/Mm | 5.991 dB/Mm |
| float64 | 6.148 dB/Mm | 5.992 dB/Mm |

float64 결과도 두 경로 모두 논문의 보고 범위를 크게 벗어나 정량 검증에
실패했다. float32 대비 오차 변화는 A–B에서 +0.002 dB/Mm,
A′–B′에서 +0.001 dB/Mm에 불과하므로, 기존 불일치는 부동소수점
정밀도 부족으로 설명되지 않는다.

## 원인 수정 후 CUDA float64 재검증

기존 검증은 완만한 74 km/6 km 이온층 전도도 프로파일을 사용해
주펌스 도달이 늦었고, 양의 overshoot와 slow-tail 직전 zero
crossing이 사라졌다. 그 상태에서 논문의 고정 절단 스텝을 적용해
DFT 스펙트럼이 추가로 왜곡되었다.

대표 daytime exponential profile인 reference height 70 km, scale height
3.33 km를 적용하고 각 계산 파형의 post-overshoot zero crossing을
자동으로 찾아 DFT를 잘라 다시 검증했다.

```bash
uv run --extra pytorch --extra visualization ionosphere-verify-2004 \
  --subdivision 7 --steps 25023 \
  --material natural-earth \
  --backend torch --device cuda:0 --dtype float64 --torch-compile \
  --dft-window adaptive \
  --ionosphere-reference-height-km 70 \
  --ionosphere-scale-height-km 3.33 \
  --output-dir artifacts/simpson-taflove-2004/level-7-float64-cuda-corrected
```

[수정 level-7 전체 보고서](../../artifacts/simpson-taflove-2004/level-7-float64-cuda-corrected/verification-report.md)

| 항목 | 기존 float64 | 수정 float64 |
|---|---:|---:|
| A 음의 피크 스텝 | 8,760 | 7,513 |
| B 음의 피크 스텝 | 18,222 | 14,459 |
| A–B 평균 절대 오차 | 6.148 dB/Mm | 0.241 dB/Mm |
| A′–B′ 평균 절대 오차 | 5.992 dB/Mm | 0.249 dB/Mm |
| A–B 최대 절대 오차 | 미측정 | 2.389 dB/Mm |
| A′–B′ 최대 절대 오차 | 미측정 | 2.433 dB/Mm |

자동 선택된 DFT 절단은 A 21,784, A′ 21,721, B/B′ 22,442
samples였다. Fig. 8의 전체 기울기와 대부분의 점은 크게 개선되었지만,
488.281 Hz의 잔차가 약 +2.4 dB/Mm이어 논문의 보고 범위를
최대 절대 오차 기준으로 엄격하게 적용하면 아직 실패다.

## subdivision 8 CUDA float64 수렴 검증

논문 격자보다 거친 subdivision 7의 고주파 수치 분산 여부를 확인하기 위해
표면 셀을 4배 늘린 subdivision 8을 같은 조건으로 실행했다. PyTorch
backend에서 face edge를 한 번에 모으던 큰 임시 tensor를 corner별로
누적하고 solver 산술을 제자리 연산으로 바꿔 12 GB RTX 3060에서 실행할
수 있도록 peak memory를 줄였다. Compiled one-step preflight의 peak allocated
memory는 약 10.1 GB였고, 전체 25,023스텝 실행에는 3,477.9초가 걸렸다.

```bash
uv run --extra pytorch --extra visualization ionosphere-verify-2004 \
  --subdivision 8 --steps 25023 \
  --material natural-earth \
  --backend torch --device cuda:0 --dtype float64 --torch-compile \
  --dft-window adaptive \
  --ionosphere-reference-height-km 70 \
  --ionosphere-scale-height-km 3.33 \
  --synchronize-every 1024 \
  --output-dir artifacts/simpson-taflove-2004/level-8-float64-cuda-corrected
```

[subdivision 8 전체 보고서](../../artifacts/simpson-taflove-2004/level-8-float64-cuda-corrected/verification-report.md)

| subdivision | 표면 셀 | A–B 평균/최대 오차 | A′–B′ 평균/최대 오차 |
|---:|---:|---:|---:|
| 6 | 40,962 | 0.572 / 2.028 dB/Mm | 0.584 / 2.130 dB/Mm |
| 7 | 163,842 | 0.241 / 2.389 dB/Mm | 0.249 / 2.433 dB/Mm |
| 8 | 655,362 | 0.156 / 0.906 dB/Mm | 0.156 / 0.913 dB/Mm |

subdivision 7의 488.281 Hz 잔차는 A–B에서 +2.389 dB/Mm였으나
subdivision 8에서 +0.412 dB/Mm로 감소했다. 평균 오차도 두 경로에서
각각 35%, 37% 감소해 공간 해상도 증가에 따른 전반적인 수렴을 확인했다.
음의 주펄스 위치는 A/A′ 7,489, B/B′ 14,446스텝이며 adaptive DFT 절단은
A 21,788, A′ 21,722, B/B′ 22,436 samples였다.

다만 subdivision 8의 최대 잔차는 478.109 Hz에서 +0.906/+0.913 dB/Mm로
이동했다. 따라서 A′–B′의 ±1.0 dB/Mm 범위는 통과하지만 A–B의 ±0.5
dB/Mm 범위는 통과하지 못해 전체 정량 상태는 여전히 실패다. 절단점을
±16 samples 바꿔도 최대 오차 변화는 약 0.01 dB/Mm에 불과해 adaptive
cutoff가 원인은 아니다. 반면 zero-padding을 32,768에서 65,536으로 늘리면
MAE는 약 0.156 dB/Mm로 유지되지만 483.195 Hz의 좁은 peak를 더 촘촘히
표본화해 최대 오차가 1.736/1.744 dB/Mm로 증가한다. 원시 Bannister
비교점이 없는 상태에서 임의 FFT bin 전체의 최대값은 주파수 표본화에
민감하므로, 현재 결과를 완전한 정량 재현으로 판정해서는 안 된다.

가능성이 큰 차이 원인은 다음과 같다.

1. NOAA-NGDC 지형·수심 원본 대신 해안선 기반 육지 마스크를 사용했다.
2. 전체 Hermance 지각 모델 대신 Fig. 6의 저항률 경계값으로 층을 근사했다.
3. 정확한 Bannister 대기 전도도 자료와 원시 비교 데이터가 없다.
4. 원 논문의 adaptive merged latitude–longitude grid와 현재 geodesic dual
   grid의 수치 분산 특성이 다르다.
5. 논문 DFT 절단 스텝은 원 논문 파형의 zero-crossing에 맞춘 값이므로,
   도달 시간이 다른 현재 파형에는 동일한 절단이 추가 오차를 만든다.

## 다음 검증 순서

1. 원시 Bannister 비교점 또는 Fig. 8 digitization을 확보해 평가 주파수를
   고정하고, FFT zero-padding에 불변인 점별 판정을 정의한다.
2. 균질 모델에서 subdivision별 위상속도와 도달 시간을 수렴 검증한다.
3. NOAA relief와 Hermance 전도도 자료를 동일한 해상도로 준비해
   동서 파형 비대칭을 재현한다.
4. 2.5 km 소스를 방사 격자의 정확한 staggered 위치에 배치한다.

## 참고문헌

J. J. Simpson and A. Taflove, “Three-dimensional FDTD modeling of impulsive
ELF propagation about the entire Earth-sphere,” *IEEE Transactions on Antennas
and Propagation*, 52(2), 443–451, 2004.
