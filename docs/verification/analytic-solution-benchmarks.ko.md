# Analytic solution benchmark suite

[English original](analytic-solution-benchmarks.md)

## 목적

앞으로는 특정 논문의 곡선이 아니라 Maxwell 방정식과 선언한 경계조건에서
직접 얻은 reference solution으로 solver를 검증한다. 이 catalog는 연속
analytic solution과 정확한 discrete-time solution을 구분하고, component
검사부터 full-vector 구면 cavity benchmark까지 순서대로 정리한다.

## 준비한 케이스

| ID | Analytic 모델 | 검사하는 solver 기능 | 기준값 | 준비 상태 |
|---|---|---|---|---|
| A0 | Zero field와 진공 정적장 | Field 저장, source-free update, 경계 | Field가 정확히 변하지 않음 | 기존 자동 invariant 사용 가능 |
| A1 | 균일 도체의 curl-free field | 물질 표본화, 손실 E update, precision | `E(t)=E0 exp[-sigma t/(epsilon_0 epsilon_r)]` | 수식, test, 현재 update 경로 준비 완료 |
| A2 | 무손실 thin shell의 구면 surface harmonic | Geodesic curl/Hodge metric, TM/TE branch, leapfrog 시간 적분 | `lambda_l=l(l+1)/R^2`, `f_l=c sqrt(lambda_l)/(2 pi)`, 정확한 leapfrog 주파수 | Full-field 수렴 runner 완료 |
| A3 | 균일 손실 매질의 plane wave | 유전율, 전도도, 감쇠와 위상 부호 | `gamma=sqrt[j omega mu (sigma+j omega epsilon)]` | Periodic Yee 보조 geometry 수렴 검증 완료 |
| A4 | 두 동심 PEC 구면 사이 vector spherical harmonic | 완전한 구면 방사 metric, 모든 field component, 방사 PEC 경계, modal frequency 추출 | TE/TM spherical-Bessel determinant root | Staggered-field initializer, projector, full-field 수렴 검증 완료 |

A1 구현은 `EPSILON_0 * relative_permittivity`를 사용한다.

## Analytic 기준

### A1: 균일 도체 relaxation

공간적으로 curl-free인 전기장에 impressed current가 없으면 다음과 같다.

```text
epsilon dE/dt + sigma E = 0,
E(t) = E0 exp(-sigma t / epsilon).
```

이 해는 exponential loss integrator를 정확히 검사한다. Trapezoidal loss
integration을 선택하면 알려진 rational amplification factor와 비교해 물리
모델 오차와 discrete integrator 오차를 섞지 않아야 한다.

### A2: 무손실 구면 surface mode

Scalar spherical harmonic `Y_l^m`은 다음 식을 만족한다.

```text
-Delta_S Y_l^m = l(l+1)/R^2 Y_l^m.
```

연속 angular frequency는 `omega_l=c sqrt(l(l+1))/R`이다. 공간 discrete
eigenvalue `lambda_h`를 구하면 centered leapfrog recurrence의 정확한 수치
주파수는 다음과 같다.

```text
omega_dt = (2/dt) asin(c dt sqrt(lambda_h) / 2).
```

첫 비교는 연속값에 대한 공간 수렴을 측정한다. 두 번째 비교는 시간 trace를
정확한 discrete recurrence와 machine precision에서 비교한다. 두 검사를
분리하면 오차가 공간과 시간 중 어디서 생겼는지 알 수 있다.

### A3: 균일 손실 전파

`exp(+j omega t)` convention에서는 다음과 같다.

```text
gamma = alpha + j beta
      = sqrt[j omega mu (sigma + j omega epsilon)].
```

400 Hz, `sigma=0.001 S/m`, `epsilon_r=10`에서 준비한 기준은
`alpha=0.00125649725 Np/m`, `beta=0.00125677689 rad/m`, 위상속도
`1.99977748e6 m/s`다. 이 케이스는 감쇠 부호와 물질 계수를 검사하기 좋지만
전역 구면 격자는 순수한 주기 plane-wave channel을 제공하지 않는다. 따라서
전역 point-source waveform에서 이 값을 추정하지 말고 보조 geometry로
유지해야 한다.

이제 1차원 periodic Yee 보조 문제에서 감쇠하는 Fourier mode를 직접 측정한다.
감쇠율과 진동 주파수는 모두 연속체 기준값에 2차로 수렴한다.
이 보조 케이스는 손실과 전파가 동시에 작용하는 update를 분리해 검사한다.
구면 Hodge geometry는 검사하지 않으며, 그 부분은 A2와 A4가 담당한다.

### A4: 동심 PEC 구면 cavity

안쪽과 바깥쪽 반지름을 `a`, `b`라 하자. 방사 함수는 spherical Bessel
function `j_l(kr)`와 `y_l(kr)`의 선형결합이다. PEC root는 다음 식을
만족한다.

```text
TE: det [[j_l(ka), y_l(ka)], [j_l(kb), y_l(kb)]] = 0
TM: 각 z_l(x)를 d[x z_l(x)]/dx로 바꾼다.
```

`a=6371 km`, `b=a+100 km`, `l=1`에서 처음 세 root는 다음과 같다.

| 편광 | 주파수 (Hz) |
|---|---|
| TE | 1498.99913, 2997.94300, 4496.89915 |
| TM | 10.50912, 1498.99913, 2997.94300 |

낮은 TM root는 지구 규모 수평 전파를 검사하고 약 1499 Hz root는 첫 방사
standing wave를 검사한다. 따라서 A4 하나로 수평, 방사, 편광, 경계, 시간
적분 오차를 구분할 수 있어 가장 좋은 end-to-end 문제다.

## 측정한 수렴

Initializer는 실제 staggered electric-field 자유도 위치에서 analytic vector
spherical harmonic을 표본화한다. `H=0`인 standing wave로 시작한 뒤 projector가
energy-weighted modal amplitude와 직교 leakage를 측정하며, solver는 모든 field
component를 정상적으로 갱신한다. 초기화 뒤 어떤 component도 0으로 되돌리거나
억제하지 않는다.

| 케이스와 측정량 | 가장 성긴 격자의 상대 오차 | 가장 조밀한 격자의 상대 오차 | 관측 차수 |
|---|---:|---:|---:|
| A2 낮은 TM 주파수, subdivision 1–4 | `-1.9382%` | `-0.03169%` | `1.9782` |
| A3 periodic 감쇠율, 64–512 cells | `+0.3633%` | `+0.005640%` | `2.0031` |
| A3 periodic 주파수, 64–512 cells | `-0.5630%` | `-0.008753%` | `2.0024` |
| A4 첫 방사 TE 주파수, 방사 cell 8–32개 | `-0.6161%` | `-0.03856%` | `1.9989` |
| A4 첫 방사 TM 주파수, 방사 cell 8–32개 | `-0.6161%` | `-0.03858%` | `1.9987` |

측정한 비대상 mode electric-energy 비율의 최댓값은 `0.0009570271`이다.
A2는 수평 geodesic refinement를 검사하고, A4 TE와 TM 실행은 angular
subdivision 2를 고정한 채 방사 refinement를 분리해 검사한다.

## 합격 절차

미리 정한 refinement sequence를 사용하고 `error=C h^p`를 fitting한다.
격자 하나만 비교하면 안 된다.

1. A0는 모든 backend와 지원 dtype에서 정확히 0을 유지해야 한다.
2. A1은 curl-free field에서 선택한 loss integrator의 analytic amplification과
   roundoff 이내로 일치해야 한다. Stiff conductive case도 포함한다.
3. A2 discrete-time trace는 leapfrog recurrence와 roundoff 이내로 일치해야
   한다. 연속 고유값 오차는 subdivision 1–4에서 단조 감소하고 관측 차수가
   약 2여야 한다.
4. A3는 양의 감쇠와 위상상수를 복원해야 하며, 보조 channel의 공간·시간
   세분에 따라 두 오차가 모두 감소해야 한다.
5. A4는 낮은 TM mode와 첫 방사 TE mode를 모두 복원해야 한다. 주파수 오차,
   mode projection leakage, 에너지 drift, PEC tangential-field 잔차가 모두
   세분에 따라 감소해야 한다.

관측한 production 결과로 tolerance를 정하지 않는다. 초기 roundoff
tolerance는 dtype에 따라 조정할 수 있지만, 수렴 gate에서는 고정 percentage
threshold보다 차수와 단조성을 먼저 사용한다.

## 다음 구현 작업

이제 analytic 케이스를 실행 비용과 목적에 따라 배치할 수 있다. 작고 빠른
invariant와 수식 검사는 pytest에, 수렴 실행시간 측정은 benchmark에, 생성한
full-field 근거는 verification에 둔다. Production 합격 threshold는 이번 탐색
측정값과 분리해 미리 선언해야 한다.

## 재현

[`artifacts/analytic-solutions/`](../../artifacts/analytic-solutions/)에 생성한
reference catalog를 저장한다. 다음 명령으로 다시 만든다.

```bash
python -m verification.analytic_solutions
python -m verification.analytic_solutions --full-field
```
