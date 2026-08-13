"""Analyze the wide-band spectrum of the discrete spherical operator."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import numpy as np

from ionosphere_fdtd.mesh import build_geodesic_mesh
from verification.common.archive import save_npz_atomic
from verification.mesh_optimization.mesquite import load_optimized_mesh
from .model import analyze_operator_spectrum,frequency_to_degree,render,write_csv


def _parser()->argparse.ArgumentParser:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh-coordinates",type=Path,action="append",default=[])
    parser.add_argument("--maximum-degree",type=int,default=100)
    parser.add_argument("--output-dir",type=Path,default=Path("artifacts/operator-spectrum"))
    return parser


def main(argv:list[str]|None=None)->int:
    args=_parser().parse_args(argv)
    if args.maximum_degree<2:raise SystemExit("--maximum-degree must be at least 2")
    started=time.perf_counter();degrees=np.arange(1,args.maximum_degree+1)
    meshes={f"native-l{level}":build_geodesic_mesh(level,orientation="polar") for level in (6,7,8)}
    mesh_metadata={}
    for path in args.mesh_coordinates:
        mesh,metadata=load_optimized_mesh(path,expected_orientation="polar")
        meshes[f"mesquite-l{mesh.subdivision}"]=mesh;mesh_metadata[str(mesh.subdivision)]={"path":str(path),"vertices_sha256":metadata["vertices_sha256"],"objective":metadata["optimizer_reported_objective"]}
    results={}
    for label,mesh in meshes.items():
        print(f"analyzing {label}: {mesh.n_vertices:,} vertices",flush=True)
        results[label]=analyze_operator_spectrum(mesh,degrees)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    arrays={"degree":degrees}
    for label,result in results.items():
        key=label.replace("-","_")
        for field in ("eigenvalue_relative_error_mean","eigenvalue_relative_error_max_abs","wavenumber_relative_error_mean","wavenumber_relative_error_max_abs","eigenfunction_residual_mean","eigenfunction_residual_max"):
            arrays[f"{key}_{field}"]=getattr(result,field)
    npz=save_npz_atomic(args.output_dir/"operator-spectrum.npz",**arrays)
    csv=write_csv(results,args.output_dir/"operator-spectrum.csv");figure=render(results,args.output_dir/"operator-spectrum.png")
    mapped=frequency_to_degree(np.asarray((50.,500.)));physical=(degrees>=np.ceil(mapped[0]))&(degrees<=np.floor(mapped[1]));upper=(degrees>=60)&(degrees<=76)
    summary={}
    for label,result in results.items():
        summary[label]={"physical_degree_eigenvalue_mae":float(np.mean(np.abs(result.eigenvalue_relative_error_mean[physical]))),"physical_degree_wavenumber_mae":float(np.mean(np.abs(result.wavenumber_relative_error_mean[physical]))),"upper_elf_wavenumber_mae":float(np.mean(np.abs(result.wavenumber_relative_error_mean[upper]))),"degree_76_wavenumber_error":float(result.wavenumber_relative_error_mean[75]),"degree_76_eigenfunction_residual":float(result.eigenfunction_residual_mean[75])}
    orders={}
    for family in ("native","mesquite"):
        if all(f"{family}-l{level}" in results for level in (6,7,8)):
            errors=np.stack([np.abs(results[f"{family}-l{level}"].wavenumber_relative_error_mean) for level in (6,7,8)])
            orders[family]={"6_to_7_physical_mean":float(np.mean(np.log2(errors[0,physical]/errors[1,physical]))),"7_to_8_physical_mean":float(np.mean(np.log2(errors[1,physical]/errors[2,physical]))),"7_to_8_upper_elf_mean":float(np.mean(np.log2(errors[1,upper]/errors[2,upper])))}
    metadata={"git_revision":_git_revision(),"degree_min":1,"degree_max":args.maximum_degree,"frequency_mapping":{"50_hz_degree":float(mapped[0]),"500_hz_degree":float(mapped[1]),"formula":"l = 2*pi*f*R / v_Bannister(f)"},"modes_per_degree":["real Y_l^0","real Y_l^l","imag Y_l^l"],"mesquite":mesh_metadata,"summary":summary,"estimated_orders":orders,"elapsed_s":time.perf_counter()-started}
    (args.output_dir/"metadata.json").write_text(json.dumps(metadata,indent=2)+"\n",encoding="utf-8")
    print(f"npz: {npz}\ncsv: {csv}\nfigure: {figure}\n{json.dumps(metadata,indent=2)}")
    return 0


def _git_revision()->str:
    rev=subprocess.run(("git","rev-parse","--short","HEAD"),check=True,capture_output=True,text=True).stdout.strip();dirty=subprocess.run(("git","status","--porcelain"),check=True,capture_output=True,text=True).stdout.strip();return rev+("-dirty" if dirty else "")


if __name__=="__main__":raise SystemExit(main())
