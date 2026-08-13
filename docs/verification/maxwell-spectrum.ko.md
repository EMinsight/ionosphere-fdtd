# Curl/Hodge Maxwell 연산자 스펙트럼

[English original](maxwell-spectrum.md)

## 목적과 수식화

이 후속 실험은 edge 전기장 자유도에 완전한 수평 DEC 1-form 연산자 `d delta + delta d`를 적용한다. FDTD 업데이트와 같은 `edge_difference`, `face_circulation`, `dual_cell_circulation`, primal/dual 길이 Hodge factor를 사용한다. Native 및 Mesquite subdivision 6–8 격자에서 `l=1–100`을 분석했으며, 50–500 Hz에 대응하는 물리적 범위는 `l=8.56–75.57`이다.

TM trial field는 vertex에서 표본화한 real sectoral `Y_l^l`의 정확한 edge gradient다. TE trial field는 face center에서 표본화한 real sectoral harmonic의 Hodge co-gradient다. 두 편광 모두 Rayleigh 값과 전체 연산자 잔차를 저장했다.

이 계산은 matrix-free projected Maxwell 고유값 분석이며, level 8의 약 197만 edge 미지수 전체를 푸는 전역 고유값 계산은 아니다. 각 projected 값을 고유값으로 취급할 수 있는지는 잔차로 판단한다.

## 결과

| 격자 | ELF TM wavenumber MAE | ELF TE projected MAE | 상단 ELF TM MAE | 상단 ELF TE projected MAE | 상단 ELF splitting |
|---|---:|---:|---:|---:|---:|
| Native 6 | 2.4549% | 0.8092% | 5.2760% | 1.7853% | 6.7304% |
| Native 7 | 0.6233% | 0.1989% | 1.3477% | 0.4440% | 1.7908% |
| Native 8 | 0.1565% | 0.0480% | 0.3388% | 0.1091% | 0.4582% |
| Mesquite 6 | 2.4767% | 0.8272% | 5.3255% | 1.8076% | 6.7801% |
| Mesquite 7 | 0.6282% | 0.2074% | 1.3587% | 0.4537% | 1.7933% |
| Mesquite 8 | 0.1576% | 0.0519% | 0.3414% | 0.1135% | 0.4547% |

`l=76`에서 native level 8의 TM wavenumber 오차는 −0.4204%, TE projected 오차는 −0.1368%다. Mesquite에서는 각각 −0.4237%, −0.1414%다. 따라서 좌표 최적화는 분산을 결정하는 Rayleigh 값을 개선하지 않는다.

정확한 DEC map이 gradient branch를 보존하므로 TM 결과는 이전 scalar 결과와 거의 같다. Stage 1 상대 위상속도 잔차와의 상관계수는 0.857이다. 498.453776 Hz에서 관측 잔차 크기의 28.4%, 376.383464 Hz에서 13.1%를 설명한다.

## 잔차에 따른 해석 범위

Native level 8의 TM 잔차는 `l=9`에서 1.34%, `l=76`에서 0.615%다. Mesquite는 이를 0.700%와 0.0114%로 줄인다. 따라서 TM branch는 안정적인 projected 고유모드이며 최적화 좌표에서 특히 잘 성립한다.

Face-center 기반 TE 구성은 잔차가 훨씬 크다. Native level 8에서 `l=9`는 86.6%, `l=76`은 19.9%이며, Mesquite에서는 32.6%와 14.1%로 감소한다. Rayleigh 값은 편광 분리를 보여주지만 정확한 TE 고유값이라고 주장하기에는 잔차가 크다. 엄밀한 TE 스펙트럼을 얻으려면 continuum harmonic을 face center에서 표본화하는 대신 dual-face scalar 고유값 문제나 전역 block eigensystem을 풀어야 한다.

## 평가

완전한 curl/Hodge 연산자에서도 충분히 잘 해상된 TM Maxwell branch는 scalar 진단과 같은 약 2차 고주파 분산을 보인다. Mesquite는 고유함수 일관성을 개선하지만 고유값은 개선하지 않는다. 따라서 수평 연산자 분산이 상단 대역 잔차에 기여하지만 넓은 대역에 나타나는 1–2% 위상속도 offset 전체를 설명하지는 못한다는 결론이 강화된다.

이번 실험만으로 TE branch를 정량적으로 확정하지는 못했다. 연산자 분석을 더 진행한다면 dual-face 일반화 고유값 문제를 구성해 풀어야 한다. 순서대로 진행하는 검증 캠페인에서는 신뢰할 수 있는 TM 결과만으로도 전체 잔차를 scalar·정적 mesh 품질 탓으로 돌리는 작업을 중단하고 Stage 4 하부 경계 대조군으로 넘어갈 근거가 충분하다.

## 검증

`artifacts/maxwell-spectrum/`에 전체 수치 배열, CSV, 플롯, 설정 metadata를 보관했다. 전체 테스트 결과는 `236 passed, 2 skipped`이며 `git diff --check`도 통과했다. 모든 배열은 유한값이고 플롯은 RGBA `1980 x 1980` 이미지다.
