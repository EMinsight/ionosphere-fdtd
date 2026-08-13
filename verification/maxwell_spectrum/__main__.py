"""Run the complete curl/Hodge one-form Maxwell spectrum diagnostic."""
from __future__ import annotations
import argparse,json,subprocess,time
from pathlib import Path
import numpy as np
from ionosphere_fdtd.mesh import build_geodesic_mesh
from verification.common.archive import save_npz_atomic
from verification.mesh_optimization.mesquite import load_optimized_mesh
from .model import analyze_maxwell_spectrum,render,write_csv

def main(argv:list[str]|None=None)->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("--mesh-coordinates",type=Path,action="append",default=[]);p.add_argument("--maximum-degree",type=int,default=100);p.add_argument("--output-dir",type=Path,default=Path("artifacts/maxwell-spectrum"));a=p.parse_args(argv);started=time.perf_counter();degrees=np.arange(1,a.maximum_degree+1);meshes={f"native-l{i}":build_geodesic_mesh(i,orientation="polar") for i in (6,7,8)};meta={}
 for path in a.mesh_coordinates:
  mesh,m=load_optimized_mesh(path,expected_orientation="polar");meshes[f"mesquite-l{mesh.subdivision}"]=mesh;meta[str(mesh.subdivision)]={"path":str(path),"vertices_sha256":m["vertices_sha256"]}
 results={}
 for label,mesh in meshes.items():print(f"analyzing {label}: {mesh.n_edges:,} edge fields",flush=True);results[label]=analyze_maxwell_spectrum(mesh,degrees)
 a.output_dir.mkdir(parents=True,exist_ok=True);arrays={"degree":degrees}
 for label,r in results.items():
  key=label.replace("-","_")
  for field in ("tm_eigenvalue_error","te_eigenvalue_error","tm_wavenumber_error","te_wavenumber_error","tm_residual","te_residual","polarization_splitting"):arrays[f"{key}_{field}"]=getattr(r,field)
 npz=save_npz_atomic(a.output_dir/"maxwell-spectrum.npz",**arrays);csv=write_csv(results,a.output_dir/"maxwell-spectrum.csv");fig=render(results,a.output_dir/"maxwell-spectrum.png");physical=(degrees>=9)&(degrees<=75);upper=(degrees>=60)&(degrees<=76);summary={}
 for label,r in results.items():summary[label]={"physical_tm_wavenumber_mae":float(np.mean(abs(r.tm_wavenumber_error[physical]))),"physical_te_wavenumber_mae":float(np.mean(abs(r.te_wavenumber_error[physical]))),"upper_tm_wavenumber_mae":float(np.mean(abs(r.tm_wavenumber_error[upper]))),"upper_te_wavenumber_mae":float(np.mean(abs(r.te_wavenumber_error[upper]))),"upper_polarization_splitting_mean_abs":float(np.mean(abs(r.polarization_splitting[upper]))),"degree_76_tm_wavenumber_error":float(r.tm_wavenumber_error[75]),"degree_76_te_wavenumber_error":float(r.te_wavenumber_error[75])}
 metadata={"git_revision":_rev(),"operator":"DEC one-form d-delta plus delta-d using FDTD curl and Hodge metrics","degree_range":[1,a.maximum_degree],"physical_degree_range":[8.55785,75.5659],"polarizations":{"TM":"exact edge gradient of real Y_l^l at vertices","TE":"Hodge co-gradient of real Y_l^l at face centers"},"mesquite":meta,"summary":summary,"elapsed_s":time.perf_counter()-started};(a.output_dir/"metadata.json").write_text(json.dumps(metadata,indent=2)+"\n");print(f"npz: {npz}\ncsv: {csv}\nfigure: {fig}\n{json.dumps(metadata,indent=2)}");return 0
def _rev()->str:
 r=subprocess.run(("git","rev-parse","--short","HEAD"),capture_output=True,text=True,check=True).stdout.strip();d=subprocess.run(("git","status","--porcelain"),capture_output=True,text=True,check=True).stdout.strip();return r+("-dirty" if d else "")
if __name__=="__main__":raise SystemExit(main())
