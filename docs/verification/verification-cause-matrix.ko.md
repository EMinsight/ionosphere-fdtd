# 전파 검증 원인 matrix

[English original](verification-cause-matrix.md)

## 목적

이 보고서는 Simpson–Taflove 2004 검증 campaign의 Stage 1–6 결과를
통합한다. 측정으로 확인한 수치 기여, screen에서 배제한 가설, 아직 해결하지
못한 모델 가정을 구분한다. 논문 재현과 solver 물리 검증은 별도로 평가한다.

## 원인 matrix

| 원인 후보 | 근거 | 상태 | 결과 해석 |
|---|---|---|---|
| 두 receiver 비율 또는 phase unwrap 오류 | Stage 1 multi-receiver 공간회귀에서도 매끄러운 불일치가 남는다. Subdivision 8의 세 대역 위상속도 MAE는 `0.01075 c`, `0.01464 c`, `0.01783 c`다. | 주원인 아님 | 기존 pairwise estimator가 주요 위상 잔차를 만들지 않는다. |
| 상단 대역 modal mixture와 transient 추출 | Stage 1 복소 회귀 RMS는 375–500 Hz에서 `0.0910`, 400–500 Hz에서 `0.1126`까지 커지지만 격자 세분에 따라 크게 줄어든다. | 확인된 측정 불확실성 | 상단 대역 감쇠는 위상속도보다 덜 안정적이므로 지점별 감쇠 차이를 한 원인에만 배정하면 안 된다. |
| 5 km 방사 방향 이온권 staircase | Stage 2 위상 오차는 `0.00141–0.00187 c`이며 Stage 1 대역 오차의 약 10–13%를 설명한다. 상단 대역 감쇠 오차는 Stage 1의 `0.20931 dB/Mm`에 비해 `0.04358 dB/Mm`다. | 확인된 부차적 기여 | 방사 세분은 오차 일부를 개선하지만 전체 크기나 주파수 증가를 없애지 못한다. |
| 수평 geodesic 연산자 분산 | Stage 3과 curl/Hodge 후속 분석에서 음의 wavenumber 오차가 약 2차로 수렴한다. Native level-8 상단 ELF TM MAE는 `0.3388%`이며 Stage 1 위상 잔차와의 상관계수는 `0.857`이다. | 확인된 기여 | 수평 세분은 특히 고주파 조격자 오차를 크게 줄이지만 넓은 대역의 1–2% 위상 offset 전체를 설명하지 못한다. |
| 정적 mesh 품질 또는 Mesquite 좌표 | Mesquite는 harmonic 잔차를 크게 줄이지만 분산을 결정하는 고유값은 거의 바꾸지 않는다. `l=76`에서 level-8 TM 오차는 `−0.4204%`에서 `−0.4237%`로 변한다. | 주원인에서 배제 | 고유함수 일관성 개선이 전파 고유값 개선을 뜻하지 않는다. |
| 벌크 지구 복셀화와 하부 경계 | Stage 4 표면 임피던스는 감쇠를 전 대역에서 일관되게 개선하지 않으며 모든 대역의 위상속도를 악화한다. Bulk와 impedance 모델은 같은 균일 지구 세분 극한으로 간다. | 주원인 아님 | 표면 임피던스는 대조군으로만 유지하고 fit을 위해 논문 알고리즘을 바꾸지 않는다. |
| 외삽에만 의존한 level-9 추세 | Stage 5의 400 Hz subdivision-9 직접값은 `0.857661 c`이고 2차 예측은 `0.857687 c`다. Bannister 잔차 `−0.015471 c`가 남는다. | 외삽 검증 완료 | 추가 수평 세분만으로 Bannister에 도달할 가능성은 낮으며 전체 broadband level-9 실행의 진단 가치는 작다. |
| Geodesic과 merged latitude–longitude grid family | Stage 6 연산자 screen은 차수 `1.999`로 수렴한다. Level-9 등가 셀 수에서 복원한 merged-grid 오차는 geodesic의 1.39배다. | 지지되지 않음; 제한된 screen | 현재 TM 근거는 grid family 우위를 보이지 않는다. 문자 그대로의 3-D 비교에는 권위 있는 merge-transition stencil이 필요하다. |
| 공통 이온권·물질·기준 가정 | Receiver, 방사, 수평 해상도, 하부 경계, grid family 효과의 범위를 제한한 뒤에도 비영 위상 offset이 남는다. 공개된 논문 입력만으로 모든 모델 세부사항을 유일하게 복원할 수 없다. | 가장 유력한 미해결 범주이나 원인 확정 아님 | 앞으로는 plot에 맞춰 격자를 조정하지 말고 독립 출처의 이온권 profile과 Bannister guide의 의미를 검증해야 한다. |

## 정량적 기여 범위

375–500 Hz에서 Stage 1 subdivision-8 위상속도 MAE는 `0.01783 c`다. 독립
5 km 방사 staircase는 `0.00187 c`, 즉 약 10%를 설명한다. Level-8 수평
TM 연산자의 wavenumber 오차는 약 0.34%이며, 400 Hz에서 level 8에서 9로
가며 직접 측정한 위상 보정량은 `0.001714 c`다. 이 효과들은 예상한 부호로
측정되지만 level-9 400 Hz 잔차 `0.015471 c`는 그대로 남는다.

이 실험들은 더해서 전체 오차가 되는 분해가 아니다. 방사, 수평, modal,
fitting 오차는 완전한 Maxwell 해에서 서로 영향을 준다. 위 수치는 통제된
범위와 추세 비교이며 합계가 100%가 되는 백분율이 아니다.

## 최종 평가

### 논문 재현

Simpson–Taflove figure의 정확한 재현에는 여전히 한계가 있다. 공개 자료는
adaptive latitude–longitude transition stencil, 모든 논문 전용 물질 입력,
분석 선택을 유일하게 정하지 않는다. 따라서 현재 geodesic solver가 출판된
Bannister 일치도를 정확히 재현해야 한다고 주장하지 않는다.

### Solver 물리 검증

Solver는 일관된 세분 거동을 보였으며 다음 독립 대조 검사를 통과했다.

- Multi-receiver 위상 추출이 안정적이다.
- 방사 오차는 격자 세분에 따라 감소한다.
- 수평 TM 분산은 약 2차로 수렴한다.
- Subdivision-9 직접값이 예측과 일치한다.
- 균일 bulk와 impedance 하부 경계가 같은 세분 극한을 공유한다.
- 두 수평 grid family가 같은 구면 고유값으로 접근한다.

따라서 물리 검증의 근거는 정확한 논문 재현보다 강하다. 남은 offset은 한
수치 결함 탓으로 단정하지 말고 공통 모델·기준 불확실성으로 보고해야 한다.

## 권장 후속 작업

1. 현재 Stage 1–6 artifact를 수치 기준선으로 고정한다.
2. 100, 250, 400 Hz에서 독립적인 이온권 profile 민감도 matrix를 만들고,
   물리적 출처가 있는 parameter를 한 번에 하나씩 바꾼다.
3. 각 profile을 방사 고유모드 benchmark와 먼저 비교한다. 방사 screen에서
   물질 변화가 예측될 때만 소수의 대응 3-D 협대역 대조 실험을 실행한다.
4. 별도의 2006 Figure 7 normalization 조사는 이 전파 원인 matrix에 섞지
   않는다.

출판 곡선에 맞추기 위해 이온권 parameter, 병합 threshold, 관측 window를
조정하지 않는다. 각 profile 출처와 합격 기준을 실행 전에 정해야 한다.

## 원본 보고서

- [Stage 1: multi-receiver 전파상수](multi-receiver-propagation-constant.ko.md)
- [Stage 2: 방사 고유모드 benchmark](radial-eigenmode.ko.md)
- [Stage 3: scalar 연산자 spectrum](operator-spectrum.ko.md)
- [Curl/Hodge Maxwell 후속 분석](maxwell-spectrum.ko.md)
- [Stage 4: 표면 임피던스 대조군](surface-impedance.ko.md)
- [Stage 5: subdivision-9 협대역](narrow-band-subdivision-9.ko.md)
- [Stage 6: merged latitude–longitude 대조군](merged-latlon-control.ko.md)
