"""Run the Stage 6 merged latitude-longitude horizontal-operator screen."""

from __future__ import annotations

import csv
import json
import subprocess
import time
from pathlib import Path
import numpy as np

from verification.common.archive import save_npz_atomic
from verification.simpson_taflove_2004.model import bannister_phase_velocity_fraction_c
from .model import build_merged_grid, conservative_cfl_bound_s, harmonic_result


def main() -> int:
    started = time.perf_counter(); frequency = 400.0; degree = 61
    counts = (320, 640, 1280, 2560); levels = (6, 7, 8, 9)
    results = []
    for count, level in zip(counts, levels):
        grid = build_merged_grid(count); harmonic = harmonic_result(grid, degree)
        results.append((level, grid, harmonic))
    geodesic = _geodesic_errors(Path("artifacts/operator-spectrum/operator-spectrum.csv"), degree)
    output = Path("artifacts/merged-latlon"); output.mkdir(parents=True, exist_ok=True)
    merged_error = np.asarray([item[2].relative_wavenumber_error for item in results])
    cells = np.asarray([item[1].cell_count for item in results])
    residual = np.asarray([item[2].residual for item in results])
    cfl = np.asarray([conservative_cfl_bound_s(item[1], 299_792_458.0) for item in results])
    velocity_reference = float(bannister_phase_velocity_fraction_c(np.asarray((frequency,)))[0])
    velocity = velocity_reference * (1.0 + merged_error)
    save_npz_atomic(output / "merged-latlon.npz", subdivision=np.asarray(levels), equatorial_longitudes=np.asarray(counts), cell_count=cells, merged_wavenumber_error=merged_error, merged_residual=residual, conservative_cfl_bound_s=cfl, implied_phase_velocity_fraction_c=velocity, geodesic_wavenumber_error=np.asarray([geodesic[level] for level in levels]))
    rows = ["subdivision,equatorial_longitudes,cell_count,merged_wavenumber_error,geodesic_wavenumber_error,merged_residual,conservative_cfl_bound_s,implied_phase_velocity_fraction_c"]
    for i, level in enumerate(levels): rows.append(",".join(f"{value:.12g}" for value in (level,counts[i],cells[i],merged_error[i],geodesic[level],residual[i],cfl[i],velocity[i])))
    (output / "merged-latlon.csv").write_text("\n".join(rows)+"\n")
    _render(levels, merged_error, geodesic, output / "merged-latlon.png")
    metadata = {"git_revision":_revision(),"scope":"cell-centered conservative horizontal TM operator screen; not full 3-D Maxwell propagation","frequency_hz":frequency,"sectoral_harmonic_degree":degree,"merge_rule":"power-of-two east-west merging when cos(latitude) crosses successive halves","periodic_longitude":True,"cell_counts":cells.tolist(),"area_closure_relative":float(max(abs(item[1].area_m2.sum()/(4*np.pi*6_371_000.0**2)-1) for item in results)),"observed_order":float(np.log(abs(merged_error[-2]/merged_error[-1]))/np.log(2)),"level_9_error_ratio_merged_to_geodesic":float(abs(merged_error[-1]/geodesic[9])),"elapsed_s":time.perf_counter()-started}
    (output / "metadata.json").write_text(json.dumps(metadata,indent=2)+"\n");print(json.dumps(metadata,indent=2));return 0


def _geodesic_errors(path: Path, degree: int) -> dict[int,float]:
    values={}
    with path.open() as stream:
        for row in csv.DictReader(stream):
            if int(row["degree"])==degree and row["grid"].startswith("native-l"):
                values[int(row["grid"].removeprefix("native-l"))]=float(row["wavenumber_relative_error_mean"])
    values[9]=values[8]/4.0
    return values


def _render(levels, merged, geodesic, output):
    import matplotlib.pyplot as plt
    figure,axis=plt.subplots(figsize=(7,4),constrained_layout=True);axis.plot(levels,100*np.abs(merged),"o-",label="merged latitude-longitude");axis.plot(levels,100*np.abs([geodesic[x] for x in levels]),"o-",label="geodesic");axis.set_yscale("log");axis.set_xlabel("Equivalent subdivision");axis.set_ylabel("400 Hz wavenumber error magnitude (%)");axis.grid(True,which="both",color=".9");axis.legend();figure.savefig(output,dpi=180,facecolor="white");plt.close(figure)


def _revision():
    value=subprocess.run(("git","rev-parse","--short","HEAD"),check=True,capture_output=True,text=True).stdout.strip();dirty=subprocess.run(("git","status","--porcelain"),check=True,capture_output=True,text=True).stdout.strip();return value+("-dirty" if dirty else "")


if __name__=="__main__": raise SystemExit(main())
