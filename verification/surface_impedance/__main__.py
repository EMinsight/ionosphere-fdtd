"""Run the frequency-domain surface-impedance lower-boundary control."""
from __future__ import annotations
import argparse,json,subprocess,time
from pathlib import Path
import numpy as np
from verification.common.archive import save_npz_atomic
from verification.simpson_taflove_2004.model import paper_evaluation_frequencies
from .model import render,run_comparison,solve_curve,surface_impedance_ohm,write_csv
def main(argv:list[str]|None=None)->int:
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,default=Path('artifacts/surface-impedance'));a=p.parse_args(argv);started=time.perf_counter();r=run_comparison(paper_evaluation_frequencies(),dz=5000.);a.output_dir.mkdir(parents=True,exist_ok=True)
 npz=save_npz_atomic(a.output_dir/'surface-impedance.npz',frequency_hz=r.pec.frequency_hz,pec_beta=r.pec.beta,bulk_beta=r.bulk.beta,impedance_beta=r.impedance.beta,pec_attenuation=r.pec.attenuation_db_per_mm,bulk_attenuation=r.bulk.attenuation_db_per_mm,impedance_attenuation=r.impedance.attenuation_db_per_mm,pec_velocity=r.pec.phase_velocity_fraction_c,bulk_velocity=r.bulk.phase_velocity_fraction_c,impedance_velocity=r.impedance.phase_velocity_fraction_c,bannister_attenuation=r.bannister_attenuation,bannister_velocity=r.bannister_velocity,pec_residual=r.pec.residual,bulk_residual=r.bulk.residual,impedance_residual=r.impedance.residual)
 csv=write_csv(r,a.output_dir/'surface-impedance.csv');fig=render(r,a.output_dir/'surface-impedance.png');bands={}
 for label,lo,hi in [('50-200',50,200),('200-375',200,375),('375-500',375,501)]:
  mask=(r.pec.frequency_hz>=lo)&(r.pec.frequency_hz<hi);bands[label]={}
  for name,c in [('pec',r.pec),('bulk',r.bulk),('impedance',r.impedance)]:bands[label][name]={'attenuation_mae_db_per_mm':float(np.mean(abs(c.attenuation_db_per_mm[mask]-r.bannister_attenuation[mask]))),'velocity_mae_fraction_c':float(np.mean(abs(c.phase_velocity_fraction_c[mask]-r.bannister_velocity[mask])))}
 convergence={}
 convergence_frequency=np.asarray((50.,250.,500.))
 for dz in (5000.,200.,100.,50.):
  bulk=solve_curve(convergence_frequency,'bulk',dz=dz);impedance=solve_curve(convergence_frequency,'impedance',dz=dz)
  convergence[str(int(dz))]={'absolute_attenuation_delta_db_per_mm':abs(bulk.attenuation_db_per_mm-impedance.attenuation_db_per_mm).tolist(),'absolute_velocity_delta_fraction_c':abs(bulk.phase_velocity_fraction_c-impedance.phase_velocity_fraction_c).tolist(),'maximum_eigen_residual':float(max(bulk.residual.max(),impedance.residual.max()))}
 meta={'git_revision':_rev(),'method':'1-D conservative TM generalized eigenproblem','lower_boundaries':{'pec':'zero flux at sea level','bulk':'100 km homogeneous ground terminated by zero flux','impedance':'exact homogeneous half-space surface impedance Robin flux'},'ground_sigma_s_m':1e-3,'ground_epsilon_r':10.,'analysis_spacing_m':5000.,'surface_impedance_ohm':{'50_hz':[surface_impedance_ohm(50).real,surface_impedance_ohm(50).imag],'500_hz':[surface_impedance_ohm(500).real,surface_impedance_ohm(500).imag]},'maximum_eigen_residual':float(max(r.pec.residual.max(),r.bulk.residual.max(),r.impedance.residual.max())),'bands':bands,'convergence':{'frequency_hz':convergence_frequency.tolist(),'spacing_m':convergence},'elapsed_s':time.perf_counter()-started};(a.output_dir/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n');print(f'npz: {npz}\ncsv: {csv}\nfigure: {fig}\n{json.dumps(meta,indent=2)}');return 0
def _rev()->str:
 r=subprocess.run(('git','rev-parse','--short','HEAD'),check=True,capture_output=True,text=True).stdout.strip();d=subprocess.run(('git','status','--porcelain'),check=True,capture_output=True,text=True).stdout.strip();return r+('-dirty' if d else '')
if __name__=='__main__':raise SystemExit(main())
