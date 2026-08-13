"""Compare bulk-Earth, PEC, and impedance lower boundaries in 1-D."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from numpy.typing import NDArray
from scipy.sparse import diags
from scipy.sparse.linalg import eigs
from ionosphere_fdtd.constants import C_0,EPSILON_0,MU_0
from verification.radial_eigenmode.model import conductivity_s_m,TOP_ALTITUDE_M
from verification.simpson_taflove_2004.model import bannister_figure_8_guide,bannister_phase_velocity_fraction_c
FloatArray=NDArray[np.float64];ComplexArray=NDArray[np.complex128]
GROUND_SIGMA_S_M=1e-3;GROUND_EPSILON_R=10.;BOTTOM_M=-100_000.;DZ_M=100.
@dataclass(frozen=True,slots=True)
class BoundaryCurve:
 frequency_hz:FloatArray;beta:ComplexArray;attenuation_db_per_mm:FloatArray;phase_velocity_fraction_c:FloatArray;residual:FloatArray
@dataclass(frozen=True,slots=True)
class BoundaryComparison:
 pec:BoundaryCurve;bulk:BoundaryCurve;impedance:BoundaryCurve;bannister_attenuation:FloatArray;bannister_velocity:FloatArray
def surface_impedance_ohm(frequency_hz:float)->complex:
 omega=2*np.pi*frequency_hz
 return np.sqrt(1j*omega*MU_0/(GROUND_SIGMA_S_M+1j*omega*EPSILON_0*GROUND_EPSILON_R))
def _solve(frequency_hz:float,model:str,dz:float=DZ_M)->tuple[complex,float]:
 if model not in {'pec','bulk','impedance'}:raise ValueError('unknown lower boundary model')
 lo=BOTTOM_M if model=='bulk' else 0.;z=np.arange(lo,TOP_ALTITUDE_M+dz,dz);omega=2*np.pi*frequency_hz;k=omega/C_0
 ground=z<0;sigma=np.where(ground,GROUND_SIGMA_S_M,conductivity_s_m(z));er=np.where(ground,GROUND_EPSILON_R,1.);eps=er-1j*sigma/(omega*EPSILON_0);inv=1/eps;interface=2*inv[:-1]*inv[1:]/(inv[:-1]+inv[1:]);off=interface/dz**2;diag=np.empty(len(z),complex);diag[0]=-off[0];diag[-1]=-off[-1];diag[1:-1]=-(off[:-1]+off[1:])
 if model=='impedance':
  # The atmospheric-domain outward flux is the negative of the upward
  # derivative.  For exp(+j omega t), q_z = j omega eps_0 Z_s H at z=0.
  admittance=1j*omega*EPSILON_0*surface_impedance_ohm(frequency_hz)
  diag[0]-=admittance/dz
 op=diags((off,diag+k*k,off),(-1,0,1),format='csc');weight=diags(inv,format='csc');standard=diags(eps,format='csc')@op;vals,vecs=eigs(standard,k=4,sigma=(k/.85)**2)
 candidates=[]
 for i,val in enumerate(vals):
  beta=np.sqrt(val);beta=beta if beta.real>0 else -beta;v=omega/beta.real/C_0;a=-20/np.log(10)*beta.imag*1e6
  if .65<v<1.05 and 0<a<100:candidates.append((abs(v-.85),i,beta))
 if not candidates:raise RuntimeError(f'no physical mode for {model} at {frequency_hz:g} Hz')
 _,i,beta=min(candidates);x=vecs[:,i];res=np.linalg.norm(op@x-beta**2*(weight@x))/(np.linalg.norm(op@x)+np.linalg.norm(beta**2*(weight@x)));return complex(beta),float(res)
def solve_curve(frequency:FloatArray,model:str,dz:float=DZ_M)->BoundaryCurve:
 f=np.asarray(frequency,float);beta=np.empty(len(f),complex);res=np.empty(len(f))
 for i,value in enumerate(f):beta[i],res[i]=_solve(float(value),model,dz)
 return BoundaryCurve(f,beta,-20/np.log(10)*beta.imag*1e6,2*np.pi*f/beta.real/C_0,res)
def run_comparison(frequency:FloatArray,dz:float=DZ_M)->BoundaryComparison:
 f=np.asarray(frequency,float);return BoundaryComparison(solve_curve(f,'pec',dz),solve_curve(f,'bulk',dz),solve_curve(f,'impedance',dz),bannister_figure_8_guide(f),bannister_phase_velocity_fraction_c(f))
def write_csv(r:BoundaryComparison,output:str|Path)->Path:
 output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);rows=['frequency_hz,model,attenuation_db_per_mm,phase_velocity_fraction_c,beta_real,beta_imag,eigen_residual,bannister_attenuation_db_per_mm,bannister_phase_velocity_fraction_c']
 for name,c in [('pec',r.pec),('bulk',r.bulk),('impedance',r.impedance)]:
  for i,f in enumerate(c.frequency_hz):rows.append(f'{f:.12g},{name},{c.attenuation_db_per_mm[i]:.12g},{c.phase_velocity_fraction_c[i]:.12g},{c.beta[i].real:.12g},{c.beta[i].imag:.12g},{c.residual[i]:.12g},{r.bannister_attenuation[i]:.12g},{r.bannister_velocity[i]:.12g}')
 output.write_text('\n'.join(rows)+'\n');return output
def render(r:BoundaryComparison,output:str|Path)->Path:
 import matplotlib.pyplot as plt
 output=Path(output);fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True);f=r.pec.frequency_hz
 for name,c in [('PEC',r.pec),('bulk Earth',r.bulk),('surface impedance',r.impedance)]:axes[0,0].plot(f,c.attenuation_db_per_mm,label=name);axes[0,1].plot(f,c.phase_velocity_fraction_c,label=name);axes[1,0].plot(f,c.attenuation_db_per_mm-r.bannister_attenuation,label=name);axes[1,1].plot(f,c.phase_velocity_fraction_c-r.bannister_velocity,label=name)
 axes[0,0].plot(f,r.bannister_attenuation,'k--',label='Bannister');axes[0,1].plot(f,r.bannister_velocity,'k--',label='Bannister');axes[0,0].set_ylabel('Attenuation (dB/Mm)');axes[0,1].set_ylabel('Phase velocity (c)');axes[1,0].set_ylabel('Attenuation residual (dB/Mm)');axes[1,1].set_ylabel('Velocity residual (c)')
 for ax in axes[1]:ax.set_xlabel('Frequency (Hz)')
 for ax in axes.flat:ax.grid(True,color='.9');ax.legend(fontsize=8)
 fig.savefig(output,dpi=180,facecolor='white');plt.close(fig);return output
