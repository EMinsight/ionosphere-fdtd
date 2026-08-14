"""Generate the solver-centered analytic benchmark catalog."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
import numpy as np

from ionosphere_fdtd.constants import EARTH_RADIUS_M
from .model import homogeneous_medium_propagation_constant, pec_spherical_shell_frequencies_hz, spherical_surface_frequency_hz
from .full_field import observed_order, run_full_field_suite
from .periodic import run_periodic_convergence
from .operator_analysis import run_te_operator_comparison
from .a4_asymptotic import write_a4_te_asymptotic


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--full-field",action="store_true");parser.add_argument("--operator-analysis",action="store_true");parser.add_argument("--a4-asymptotic",action="store_true");args=parser.parse_args(argv)
    output = Path("artifacts/analytic-solutions"); output.mkdir(parents=True, exist_ok=True)
    degrees = np.asarray((1, 2, 5, 8, 20, 61))
    surface = np.asarray([spherical_surface_frequency_hz(int(value), EARTH_RADIUS_M) for value in degrees])
    shell = {}
    for degree in (1, 2, 5):
        for polarization in ("TE", "TM"):
            shell[f"l{degree}_{polarization}"] = pec_spherical_shell_frequencies_hz(degree, EARTH_RADIUS_M, EARTH_RADIUS_M + 100_000.0, polarization=polarization, count=3).tolist()
    media = {}
    for conductivity, epsilon_r in ((0.0,1.0),(1e-5,1.0),(1e-3,10.0)):
        result=homogeneous_medium_propagation_constant(400.0,conductivity_s_m=conductivity,relative_permittivity=epsilon_r)
        media[f"sigma_{conductivity:g}_epsr_{epsilon_r:g}"]={"beta_rad_per_m":result.beta_rad_per_m,"attenuation_np_per_m":result.attenuation_np_per_m,"phase_velocity_m_per_s":result.phase_velocity_m_per_s}
    catalog={"git_revision":_revision(),"reference_radius_m":EARTH_RADIUS_M,"shell_outer_offset_m":100_000.0,"surface_modes":{"degree":degrees.tolist(),"frequency_hz":surface.tolist()},"pec_shell_modes_hz":shell,"homogeneous_400_hz":media,"case_order":["A0 zero/static fields","A1 homogeneous conductive relaxation","A2 spherical surface harmonic plus leapfrog dispersion","A3 homogeneous lossy-medium propagation constant","A4 concentric PEC spherical-shell TE/TM modes"]}
    (output/"catalog.json").write_text(json.dumps(catalog,indent=2)+"\n")
    rows=["degree,surface_frequency_hz"]+[f"{degree},{frequency:.12g}" for degree,frequency in zip(degrees,surface)]
    (output/"surface-modes.csv").write_text("\n".join(rows)+"\n")
    if args.full_field:
        _write_full_field(output)
    if args.operator_analysis:
        _write_operator_analysis(output)
    if args.a4_asymptotic:
        print(json.dumps(write_a4_te_asymptotic(output), indent=2))
    print(json.dumps(catalog,indent=2));return 0


def _write_full_field(output: Path) -> None:
    results=run_full_field_suite();rows=["case,refinement,polarization,subdivision,radial_cells,analytic_frequency_hz,measured_frequency_hz,relative_frequency_error,maximum_leakage,relative_energy_variation,maximum_pec_residual,time_step_s"]
    for result in results:rows.append(",".join(str(getattr(result,name)) for name in ("case","refinement","polarization","subdivision","radial_cells","analytic_frequency_hz","measured_frequency_hz","relative_frequency_error","maximum_leakage","relative_energy_variation","maximum_pec_residual","time_step_s")))
    (output/"full-field.csv").write_text("\n".join(rows)+"\n")
    a2_rows=[x for x in results if x.case=="A2"];a2=np.asarray([x.relative_frequency_error for x in a2_rows]);a4_te_rows=[x for x in results if x.case=="A4" and x.refinement=="radial" and x.polarization=="TE"];a4_tm_rows=[x for x in results if x.case=="A4" and x.refinement=="radial" and x.polarization=="TM"];a4_te=np.asarray([x.relative_frequency_error for x in a4_te_rows]);a4_tm=np.asarray([x.relative_frequency_error for x in a4_tm_rows])
    periodic=run_periodic_convergence();periodic_rows=["cells,time_step_s,analytic_decay_per_s,measured_decay_per_s,relative_decay_error,analytic_frequency_hz,measured_frequency_hz,relative_frequency_error"]
    for result in periodic:periodic_rows.append(",".join(str(getattr(result,name)) for name in ("cells","time_step_s","analytic_decay_per_s","measured_decay_per_s","relative_decay_error","analytic_frequency_hz","measured_frequency_hz","relative_frequency_error")))
    (output/"periodic-lossy.csv").write_text("\n".join(periodic_rows)+"\n")
    decay=np.asarray([x.relative_decay_error for x in periodic]);frequency=np.asarray([x.relative_frequency_error for x in periodic])
    te_energy=np.asarray([x.relative_energy_variation for x in a4_te_rows]);tm_energy=np.asarray([x.relative_energy_variation for x in a4_tm_rows]);joint_te=np.asarray([x.maximum_leakage for x in results if x.case=="A4" and x.refinement=="joint" and x.polarization=="TE"]);joint_tm=np.asarray([x.maximum_leakage for x in results if x.case=="A4" and x.refinement=="joint" and x.polarization=="TM"])
    orders={"A4_TE_radial_order":observed_order(a4_te),"A4_TM_radial_order":observed_order(a4_tm),"A4_TE_energy_variation_order":observed_order(te_energy),"A4_TM_energy_variation_order":observed_order(tm_energy),"A4_TE_joint_leakage_order":observed_order(joint_te),"A4_TM_joint_leakage_order":observed_order(joint_tm)}
    monotone=lambda values: bool(np.all(np.diff(np.abs(values)) < 0.0))
    failures=[]
    if not all(orders[name] >= 1.8 for name in ("A4_TE_radial_order","A4_TM_radial_order")):failures.append("radial frequency order below 1.8")
    if not all(orders[name] >= 1.5 for name in ("A4_TE_energy_variation_order","A4_TM_energy_variation_order")):failures.append("energy-variation order below 1.5")
    if not all(monotone(values) for values in (a4_te,a4_tm,te_energy,tm_energy)):failures.append("radial frequency or energy variation is not monotone")
    if not all(orders[name] > 0.0 for name in ("A4_TE_joint_leakage_order","A4_TM_joint_leakage_order")):failures.append("joint leakage does not have positive order")
    if not monotone(np.asarray([x.maximum_leakage for x in a2_rows])):failures.append("low-TM leakage is not monotone")
    pec=max(x.maximum_pec_residual for x in results)
    if pec != 0.0:failures.append("PEC residual is nonzero")
    summary={"A2_horizontal_order":observed_order(a2),"A3_decay_order":observed_order(decay),"A3_frequency_order":observed_order(frequency),**orders,"maximum_leakage":max(x.maximum_leakage for x in results),"maximum_pec_residual":pec,"A4_observation_periods":5.0,"A4_acceptance_verdict":"PASS" if not failures else "FAIL","A4_acceptance_failures":failures}
    (output/"full-field-summary.json").write_text(json.dumps(summary,indent=2)+"\n")


def _write_operator_analysis(output: Path) -> None:
    results=run_te_operator_comparison();names=("subdivision","radial_cells","analytic_relative_residual","ritz_relative_residual","analytic_ritz_overlap","analytic_frequency_hz","ritz_frequency_hz","ritz_projector_leakage_one_period")
    rows=[",".join(names)]+[",".join(str(getattr(result,name)) for name in names) for result in results]
    (output/"te-operator-comparison.csv").write_text("\n".join(rows)+"\n")


def _revision() -> str:
    value=subprocess.run(("git","rev-parse","--short","HEAD"),check=True,capture_output=True,text=True).stdout.strip();dirty=subprocess.run(("git","status","--porcelain"),check=True,capture_output=True,text=True).stdout.strip();return value+("-dirty" if dirty else "")


if __name__=="__main__": raise SystemExit(main())
