# Simpson–Taflove 2004 Fig. 7·8 float32 기준 검증 결과

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

## float64 재검증 상태

Apple MPS는 PyTorch `float64`를 지원하지 않는다. 같은 level-7 격자와
35,000스텝을 PyTorch CPU 8스레드에서 재실행했으나 113분 이상 계산 후
수동으로 중단했다. 시간 적분 중에 중단했기 때문에 Fig. 7, Fig. 8 또는
Markdown 보고서는 생성되지 않았으며, 이 시도를 검증 결과로 사용하지
않는다.

다음 검증은 CUDA가 있는 Linux 시스템에서 아래 명령으로 수행한다.

```bash
uv run --extra pytorch --extra visualization ionosphere-verify-2004 \
  --subdivision 7 --steps 35000 \
  --material natural-earth \
  --backend torch --device cuda --dtype float64 --torch-compile \
  --output-dir artifacts/simpson-taflove-2004/level-7-float64-cuda
```

완료된 실행은 출력 디렉터리에 `verification-report.md`를 자동 생성한다.
해당 보고서에서 `device=cuda`, `dtype=float64`, 35,000스텝과 Git revision을
확인한 뒤 이 문서의 float32 오차와 비교해야 한다.

가능성이 큰 차이 원인은 다음과 같다.

1. NOAA-NGDC 지형·수심 원본 대신 해안선 기반 육지 마스크를 사용했다.
2. 전체 Hermance 지각 모델 대신 Fig. 6의 저항률 경계값으로 층을 근사했다.
3. 정확한 Bannister 대기 전도도 자료와 원시 비교 데이터가 없다.
4. 원 논문의 adaptive merged latitude–longitude grid와 현재 geodesic dual
   grid의 수치 분산 특성이 다르다.
5. 논문 DFT 절단 스텝은 원 논문 파형의 zero-crossing에 맞춘 값이므로,
   도달 시간이 다른 현재 파형에는 동일한 절단이 추가 오차를 만든다.

## 다음 검증 순서

1. NOAA relief와 Hermance 전도도 자료를 동일한 해상도로 준비한다.
2. 균질 모델에서 subdivision별 위상속도와 도달 시간을 수렴 검증한다.
3. 각 실행이 자동 생성하는 Markdown 보고서의 peak step과 east/west RMS를
   이 기준 결과와 비교한다.
4. 원 논문 절단값과 현재 파형의 zero-crossing 기반 절단값을 각각 계산해
   DFT 창 효과를 분리한다.
5. 원시 Bannister 곡선을 확보한 뒤 digitized guide를 교체한다.

## 참고문헌

J. J. Simpson and A. Taflove, “Three-dimensional FDTD modeling of impulsive
ELF propagation about the entire Earth-sphere,” *IEEE Transactions on Antennas
and Propagation*, 52(2), 443–451, 2004.
