# 병합 위도–경도 연산자 대조 실험

[English original](merged-latlon-control.md)

## 가설

논문의 adaptive merged latitude–longitude grid는 같은 해상도의 geodesic
grid보다 400 Hz 수평 분산이 훨씬 작아서 남은 위상속도 차이 일부를 설명할
수 있다.

## 방법

첫 Stage 6 gate에서는 분산을 포함하는 최소 TM 대조군인 보존적
cell-centered 구면 Laplacian을 구현했다. 위도 band 간격은 균일하고 경도는
주기적이다. `cos(latitude)`가 2분의 1씩 작아지는 지점을 지날 때마다 동서
인접 셀을 2의 거듭제곱 단위로 병합한다. 서로 맞지 않는 band 경계에서는
실제로 공유하는 arc를 따라 하나의 보존적 finite-volume flux를 교환한다.

400 Hz Bannister 속도는 구면조화함수 degree 61에 해당한다. Real sectoral
`Y_61^61`을 cell center에서 표본화하고 Rayleigh 값과 전체 연산자 잔차를
측정했다. 적도 경도 수 320, 640, 1280, 2560은 각각 39,830, 159,830,
638,550, 2,556,310개 셀을 만들며 geodesic subdivision 6–9와 3% 이내로
맞는다.

이 실험은 수평 연산자 screen이며 논문의 완전한 3-D Maxwell solver가
아니다. 2004년 논문은 adaptive east–west combination과 주기 경도를
명시하지만 transition mask 전체를 기계적으로 복원할 수 있게 공개하지
않았다. 따라서 power-of-two threshold는 tuning하지 않은 명시적 가정이다.

## 검증 대조군

- 구면 셀 면적 합은 상대오차 `1.11e-16` 이내에서 `4 pi R^2`와 일치한다.
- 상수장은 정확한 null mode이며 전체 discrete flux가 보존된다.
- 연산자의 이차 에너지가 양수다.
- Gershgorin CFL bound가 유한한 양수다.
- 격자를 세분하면 sectoral-harmonic 오차가 단조 감소한다.
- 전체 harmonic 잔차는 `0.001408`에서 `0.00002054`로 줄어든다.

이 검사는 보존성, 가중 연산자 대칭성, 에너지 부호, 안정성 bound, 알려진
구면 고유값 benchmark를 다룬다. 감쇠와 손실을 포함한 3-D 에너지 변화는
이번 screen의 범위 밖이므로 보고하지 않는다.

## 결과

| 등가 subdivision | 병합 셀 수 | 병합 격자 wavenumber 오차 | Geodesic wavenumber 오차 | 병합 격자 잔차 |
|---:|---:|---:|---:|---:|
| 6 | 39,830 | −5.8228% | −4.1833% | 0.001408 |
| 7 | 159,830 | −1.4757% | −1.0612% | 0.0003340 |
| 8 | 638,550 | −0.3702% | −0.2663% | 0.00008243 |
| 9 | 2,556,310 | −0.09262% | −0.06657% 외삽 | 0.00002054 |

병합 격자의 수렴 차수는 1.999다. 셀 수를 맞췄을 때 오차는 geodesic
격자의 약 1.39배로 일관된다. 두 이산화 모두 같은 연속체 고유값으로
가지만, 복원한 병합 격자가 더 빠르게 접근하지는 않는다.

## 결정

이번 screen은 grid family 분산이 Bannister와의 위상 offset을 만든다는
가설을 지지하지 않는다. 같은 해상도에서 병합 격자가 크게 우수하지 않으며,
충분히 해상된 TM branch에서는 오히려 약간 나쁘다.

수평 stencil이 400 Hz 오차를 없앤다는 주장만 시험하기 위해 완전한 3-D
병합 격자를 구현할 근거는 없다. 감쇠와 full-vector polarization을
비교하려면 여전히 그런 구현이 필요하므로 Stage 6의 결과는 논문 재현이
아닌 제한된 판정이다. 현재 증거는 두 격자가 공유하는 방사 방향
이온권·물질 profile과 Bannister guide 사이의 관계를 우선 검토하도록 한다.

## 다음 실험

Bannister에 맞추려고 병합 threshold나 transition flux를 조정하지 않는다.
추가 작업이 필요하다면 완전한 3-D solver를 만들기 전에 권위 있는
transition mask나 원본 source code를 확보해야 한다. 그렇지 않으면 Stage
1–6 결과를 원인 matrix로 통합하여 확인된 수치 효과와 공통 모델 불확실성을
분리한다.

## 검증

[`artifacts/merged-latlon/`](../../artifacts/merged-latlon/)에 배열, CSV 값,
metadata, 수렴 plot을 보관했다. 다음 명령으로 screen을 실행한다.

```bash
python -m verification.merged_latlon
```
