"""Generate the solver-centered analytic benchmark catalog."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
import numpy as np

from ionosphere_fdtd.constants import EARTH_RADIUS_M
from .model import homogeneous_medium_propagation_constant, pec_spherical_shell_frequencies_hz, spherical_surface_frequency_hz


def main() -> int:
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
    (output/"surface-modes.csv").write_text("\n".join(rows)+"\n");print(json.dumps(catalog,indent=2));return 0


def _revision() -> str:
    value=subprocess.run(("git","rev-parse","--short","HEAD"),check=True,capture_output=True,text=True).stdout.strip();dirty=subprocess.run(("git","status","--porcelain"),check=True,capture_output=True,text=True).stdout.strip();return value+("-dirty" if dirty else "")


if __name__=="__main__": raise SystemExit(main())
