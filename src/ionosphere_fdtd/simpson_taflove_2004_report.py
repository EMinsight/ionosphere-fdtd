"""Markdown reporting for the Simpson–Taflove 2004 validation run."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import platform
import sys

import numpy as np

from .simpson_taflove_2004 import (
    PAPER_PATH_AB_TOLERANCE_DB_PER_MM,
    PAPER_PATH_APBP_TOLERANCE_DB_PER_MM,
)


@dataclass(frozen=True, slots=True)
class ValidationRunSummary:
    """Reproducibility metadata and results for one complete validation run."""

    generated_at: datetime
    command: str
    git_revision: str
    subdivision: int
    surface_cells: int
    radial_cells: int
    time_step_s: float
    steps: int
    material_model: str
    ionosphere_reference_height_m: float
    ionosphere_scale_height_m: float
    dft_window: str
    backend: str
    device: str
    dtype: str
    compiled: bool
    elapsed_s: float
    metrics: Mapping[str, float | int]
    figure_7: Path
    figure_8: Path
    trace_data: Path


def write_validation_report(
    summary: ValidationRunSummary,
    output: str | Path,
) -> Path:
    """Write a self-contained Markdown record for a validation run."""

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    path_ab_error = float(
        summary.metrics["path_ab_mean_absolute_error_db_per_mm"]
    )
    path_apbp_error = float(
        summary.metrics["path_apbp_mean_absolute_error_db_per_mm"]
    )
    path_ab_max_error = float(
        summary.metrics["path_ab_maximum_absolute_error_db_per_mm"]
    )
    path_apbp_max_error = float(
        summary.metrics["path_apbp_maximum_absolute_error_db_per_mm"]
    )
    path_ab_passed = path_ab_max_error <= PAPER_PATH_AB_TOLERANCE_DB_PER_MM
    path_apbp_passed = path_apbp_max_error <= PAPER_PATH_APBP_TOLERANCE_DB_PER_MM
    status = "통과" if path_ab_passed and path_apbp_passed else "실패"
    path_ab_status = "통과" if path_ab_passed else "실패"
    path_apbp_status = "통과" if path_apbp_passed else "실패"
    path_ab_tolerance = f"{PAPER_PATH_AB_TOLERANCE_DB_PER_MM:.1f}"
    path_apbp_tolerance = f"{PAPER_PATH_APBP_TOLERANCE_DB_PER_MM:.1f}"
    figure_7_link = _relative_markdown_link(summary.figure_7, output_path)
    figure_8_link = _relative_markdown_link(summary.figure_8, output_path)
    trace_data_link = _relative_markdown_link(summary.trace_data, output_path)
    metric_rows = "\n".join(
        f"| `{name}` | {_format_metric(value)} |"
        for name, value in summary.metrics.items()
    )
    report = f"""# Simpson–Taflove 2004 Fig. 7·8 검증

> 정량 검증 상태: **{status}**

생성 시각: {summary.generated_at.astimezone().isoformat(timespec="seconds")}

## 재현 명령

```bash
{summary.command}
```

## 실행 구성

| 항목 | 값 |
|---|---:|
| Git revision | `{summary.git_revision}` |
| subdivision | {summary.subdivision} |
| 표면 셀 | {summary.surface_cells:,} |
| 방사 셀 | {summary.radial_cells} |
| 시간 간격 | {summary.time_step_s:.3e} s |
| 시간 스텝 | {summary.steps:,} |
| 재료 모델 | `{summary.material_model}` |
| 이온층 reference height | {summary.ionosphere_reference_height_m / 1_000.0:g} km |
| 이온층 scale height | {summary.ionosphere_scale_height_m / 1_000.0:g} km |
| DFT window | `{summary.dft_window}` |
| backend | `{summary.backend}` |
| device | `{summary.device}` |
| dtype | `{summary.dtype}` |
| compiled step | `{summary.compiled}` |
| 실행 시간 | {summary.elapsed_s:.1f} s |

## 논문 파라미터

- 소스: 적도, 47° W, 지표 바로 위의 5 km 수직 전류 셀
- Gaussian `1/e` full width: `480 Δt`
- Gaussian center: `960 Δt`
- `Δt = 3.0 μs`
- 관측점: A/A′는 반대편까지 거리의 1/4, B/B′는 1/2
- DFT 절단: `adaptive`는 각 계산 파형의 slow-tail 직전 zero crossing,
  `paper`는 A 22,849, B 24,165, A′ 22,737, B′ 25,023 samples
- 고정 비교 주파수: Fig. 8 marker 간격과 일치하는 32,768-point
  DFT의 50–500 Hz 구간 45개 bin (50.863–498.454 Hz)

## 판정

| 경로 | 평균 절대 오차 | 최대 절대 오차 | 논문 보고 범위 | 결과 |
|---|---:|---:|---:|---:|
| A–B | {path_ab_error:.3f} dB/Mm | {path_ab_max_error:.3f} dB/Mm | ±{path_ab_tolerance} dB/Mm | {path_ab_status} |
| A′–B′ | {path_apbp_error:.3f} dB/Mm | {path_apbp_max_error:.3f} dB/Mm | ±{path_apbp_tolerance} dB/Mm | {path_apbp_status} |

## 전체 지표

| 지표 | 값 |
|---|---:|
{metric_rows}

## 생성 결과

![Figure 7 verification]({figure_7_link})

![Figure 8 verification]({figure_8_link})

[Receiver traces (NPZ)]({trace_data_link})

## 해석 시 주의사항

- NOAA-NGDC relief 원본 대신 Natural Earth 110-m 육지 마스크를 사용한다.
- Fig. 6의 부등식 경계값으로 지각 층을 근사하며 전체 Hermance 모델은
  아니다.
- Fig. 8 기준선은 Bannister (1984), 식 (5), (7), (8)의 daytime attenuation
  모델을 `H = 70 km`, `ξ₀ = ξ₁ = 1/0.3 km`로 계산한다.
- 원 논문의 병합 위경도 격자와 이 프로젝트의 geodesic dual grid는 서로
  다르다.
- 논문에 전류 진폭이 명시되지 않아 Fig. 7은 1 A로 정규화한다. Fig. 8의
  스펙트럼 비율은 이 진폭 선택과 무관하다.

## 실행 환경

- Python: `{platform.python_version()}`
- NumPy: `{np.__version__}`
- Platform: `{platform.platform()}`
- Python executable: `{sys.executable}`
"""
    output_path.write_text(report, encoding="utf-8")
    return output_path


def _relative_markdown_link(target: Path, report: Path) -> str:
    return Path(
        os.path.relpath(target.resolve(), start=report.parent.resolve())
    ).as_posix()


def _format_metric(value: float | int) -> str:
    return str(value) if isinstance(value, int) else f"{value:.6g}"
