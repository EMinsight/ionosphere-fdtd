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
| A4 | 두 동심 PEC 구면 사이 vector spherical harmonic | 완전한 구면 방사 metric, 모든 field component, 방사 PEC 경계, modal frequency 추출 | TE/TM spherical-Bessel determinant root | 사전 선언한 asymptotic v2 protocol에서 PASS, v1 실패 기록은 보존 |

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

모든 A4 격자는 analytic mode의 5주기 동안 관찰한다. Radial 수렴에서는 angular
subdivision 2를 고정하고 주파수, centered energy, PEC 경계를 판정한다. Modal
leakage는 `(subdivision, radial cells) = (1, 8), (2, 16), (3, 32)` joint
sequence에서 따로 판정한다.

| A4 진단 | 성긴 격자 | 중간 격자 | 조밀한 격자 | 판정 |
|---|---:|---:|---:|---|
| TE centered-energy 변동 | `0.2995%` | `0.07198%` | `0.01439%` | PASS, 차수 `2.1897` |
| TM centered-energy 변동 | `0.3093%` | `0.08176%` | `0.02416%` | PASS, 차수 `1.8392` |
| TE joint modal leakage | `0.02347%` | `0.04121%` | `0.04406%` | FAIL, 차수 `-0.4542` |
| TM joint modal leakage | `0.08704%` | `0.04486%` | `0.02134%` | PASS, 차수 `1.0139` |
| PEC tangential trace residual | `0` | `0` | `0` | PASS, 정확히 강제됨 |

A2에서 재사용한 낮은 TM mode의 leakage는 `0.09570%`에서 `0.003255%`로
단조 감소했다. Refinement 방향을 분리하자 앞서 발견한 TM leakage의 모호성은
해소됐지만, 동일한 시간 동안 실행한 joint 연구에서 TE 실패가 드러났다. 이
sequence에서는 analytic TE mode가 invariant discrete modal subspace에 가까워지지
않으므로 A4 v1 판정은 **FAIL**이다.

### TE 연산자 비교

Matrix-free weighted Krylov–Ritz 분석으로 solver의 실제 electric `curl-curl`
연산자를 표본화한 analytic TE mode에 적용했다. 그런 다음 analytic mode와
overlap이 가장 큰 Ritz vector를 선택하고, 자체 energy-weighted projector로
그 vector를 1주기 동안 진화시켰다.

| Subdivision / radial cells | Analytic operator residual | Analytic–Ritz overlap | Ritz 주파수 (Hz) | Ritz-projector leakage |
|---|---:|---:|---:|---:|
| `1 / 8` | `4.7324e-6` | `0.9999559328` | `1489.38552` | `1.2065e-6` |
| `2 / 16` | `3.4335e-5` | `0.9999991780` | `1496.59225` | `3.9011e-5` |
| `3 / 32` | `1.6712e-5` | `0.9999999577` | `1498.39719` | `2.1328e-5` |
| `4 / 64` | `9.7667e-6` | `0.9999999975` | `1498.84863` | `1.0551e-5` |

격자를 한 단계 세분할 때마다 Ritz 주파수 오차는 약 4분의 1로 줄고,
analytic–Ritz overlap은 1에 가까워진다. Subdivision 1은 operator residual이
예외적으로 작아 거의 invariant하며, subdivision 2–4에서는 analytic residual과
Ritz-projector leakage가 감소한다. 따라서 기존 `1/8, 2/16, 3/32` TE leakage
gate에는 비점근적인 coarse-grid symmetry 효과가 포함돼 있다. TE 고유값 자체가
잘못됐다는 결과는 아니다. 아래 asymptotic v2 sequence는 이 분석을 마친 뒤,
production 실행 결과를 보기 전에 선언했다.

### A4 asymptotic v2 합격 판정

V2 protocol은 TE sequence를 `2/16, 3/32, 4/64`로 고정하고 각 case를 analytic
주파수의 5주기 동안 관찰한다. 주파수 차수 `1.8` 이상, energy-variation 차수
`1.5` 이상, 양의 leakage 차수, 정확히 0인 PEC residual을 요구한다. Production
실행 전에 이 gate를 코드에 먼저 넣었다.

| 측정량 | `2 / 16` | `3 / 32` | `4 / 64` | 차수 | 판정 |
|---|---:|---:|---:|---:|---|
| 상대 주파수 오차 | `-0.15417%` | `-0.03855%` | `-0.009638%` | `1.99979` | PASS |
| Centered-energy 변동 | `0.07198%` | `0.01436%` | `0.00009418%` | `4.78900` | PASS |
| Modal leakage | `0.04121%` | `0.04406%` | `0.03524%` | `0.11302` | PASS |
| PEC tangential trace residual | `0` | `0` | `0` | — | PASS |

선언한 v2 gate를 모두 통과했다. 이미 통과한 radial TE/TM, 낮은 TM, energy,
PEC 검사까지 합치면 현재 A4 판정은 **PASS**다. V1 실패 결과는 덮어쓰지 않고
그대로 보존한다.

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
5. A4 radial mode는 모두 analytic 주파수의 5주기 동안 관찰한다. Angular
   subdivision 2에서 radial cell을 8–32개로 늘릴 때 TE/TM 주파수 오차와
   centered-energy 변동이 단조 감소하고 fitting 차수가 각각 `1.8`, `1.5`
   이상이어야 한다. `(1,8)`, `(2,16)`, `(3,32)` joint sequence의 TE/TM
   leakage fitting 차수는 양수여야 한다. 낮은 TM leakage는 단조 감소해야 하며,
   odd ghost PEC trace는 정확히 0을 유지해야 한다.
6. Operator 근거에서 coarse level이 비점근 구간임을 확인하면 대체 sequence를
   실행 전에 선언해야 한다. A4 v2는 동일한 5주기 관찰창에서 TE `2/16,
   3/32, 4/64`를 사용하고, 주파수 차수 `>=1.8`, energy-variation 차수
   `>=1.5`, 양의 leakage 차수, PEC trace 0을 gate로 삼는다.

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
python -m verification.analytic_solutions --operator-analysis
python -m verification.analytic_solutions --a4-asymptotic
```
