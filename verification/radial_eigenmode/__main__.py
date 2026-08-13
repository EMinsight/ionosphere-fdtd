"""Run the independent one-dimensional radial eigenmode benchmark."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import numpy as np

from ..common.archive import save_npz_atomic
from ..simpson_taflove_2004.model import paper_evaluation_frequencies
from .model import render, run_benchmark, write_csv


def _parser() -> argparse.ArgumentParser:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path,default=Path("artifacts/radial-eigenmode"))
    return parser


def main(argv:list[str]|None=None)->int:
    args=_parser().parse_args(argv);started=time.perf_counter()
    result=run_benchmark(paper_evaluation_frequencies());elapsed=time.perf_counter()-started
    args.output_dir.mkdir(parents=True,exist_ok=True)
    npz=save_npz_atomic(args.output_dir/"radial-eigenmode.npz",
        frequency_hz=result.continuous.frequency_hz,
        continuous_beta_rad_per_m=result.continuous.beta_rad_per_m,
        continuous_attenuation_db_per_mm=result.continuous.attenuation_db_per_mm,
        continuous_phase_velocity_fraction_c=result.continuous.phase_velocity_fraction_c,
        continuous_eigen_residual=result.continuous.eigen_residual,
        spacing_m=result.spacing_m,discretized_beta_rad_per_m=result.discretized_beta_rad_per_m,
        discretized_attenuation_db_per_mm=result.discretized_attenuation_db_per_mm,
        discretized_phase_velocity_fraction_c=result.discretized_phase_velocity_fraction_c,
        attenuation_error_db_per_mm=result.attenuation_error_db_per_mm,
        phase_velocity_error_fraction_c=result.phase_velocity_error_fraction_c,
        eigen_residual=result.eigen_residual)
    csv=write_csv(result,args.output_dir/"radial-eigenmode.csv")
    figure=render(result,args.output_dir/"radial-eigenmode.png")
    bands={}
    for name,lo,hi in (("50-200",50,200),("200-375",200,375),("375-500",375,501)):
        mask=(result.continuous.frequency_hz>=lo)&(result.continuous.frequency_hz<hi)
        bands[name]={f"{spacing/1000:g}_km":{"attenuation_mae_db_per_mm":float(np.mean(np.abs(result.attenuation_error_db_per_mm[i,mask]))),"phase_velocity_mae_fraction_c":float(np.mean(np.abs(result.phase_velocity_error_fraction_c[i,mask])))} for i,spacing in enumerate(result.spacing_m)}
    metadata={"git_revision":_git_revision(),"method":"conservative complex TM generalized eigenproblem","boundaries":"zero normal flux at 0 and 100 km","analysis_spacing_m":result.continuous.analysis_spacing_m,"ionosphere_reference_height_km":70.0,"ionosphere_scale_height_km":1/0.3,"frequency_count":len(result.continuous.frequency_hz),"radial_spacing_km":(result.spacing_m/1000).tolist(),"elapsed_s":elapsed,"maximum_eigen_residual":float(max(np.max(result.continuous.eigen_residual),np.max(result.eigen_residual))),"bands":bands}
    (args.output_dir/"metadata.json").write_text(json.dumps(metadata,indent=2)+"\n",encoding="utf-8")
    print(f"npz: {npz}\ncsv: {csv}\nfigure: {figure}\n{json.dumps(metadata,indent=2)}")
    return 0


def _git_revision()->str:
    rev=subprocess.run(("git","rev-parse","--short","HEAD"),check=True,capture_output=True,text=True).stdout.strip()
    dirty=subprocess.run(("git","status","--porcelain"),check=True,capture_output=True,text=True).stdout.strip()
    return rev+("-dirty" if dirty else "")


if __name__=="__main__":raise SystemExit(main())
