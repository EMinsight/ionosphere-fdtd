"""Evaluate spherical harmonics under the discrete primal/dual Laplacian."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from scipy.special import sph_harm_y

from ionosphere_fdtd.constants import C_0, EARTH_RADIUS_M
from ionosphere_fdtd.mesh import GeodesicMesh
from ionosphere_fdtd.mesh_quality import scalar_laplacian
from verification.simpson_taflove_2004.model import bannister_phase_velocity_fraction_c

FloatArray = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class OperatorSpectrum:
    degree: NDArray[np.int64]
    mode_count: NDArray[np.int64]
    eigenvalue_relative_error_mean: FloatArray
    eigenvalue_relative_error_max_abs: FloatArray
    wavenumber_relative_error_mean: FloatArray
    wavenumber_relative_error_max_abs: FloatArray
    eigenfunction_residual_mean: FloatArray
    eigenfunction_residual_max: FloatArray


def frequency_to_degree(frequency_hz: FloatArray) -> FloatArray:
    frequency=np.asarray(frequency_hz,dtype=np.float64)
    velocity=bannister_phase_velocity_fraction_c(frequency)*C_0
    return 2*np.pi*frequency*EARTH_RADIUS_M/velocity


def _real_modes(mesh:GeodesicMesh,degree:int)->tuple[FloatArray,...]:
    x,y,z=mesh.vertices.T
    theta=np.arccos(np.clip(z,-1,1));phi=np.mod(np.arctan2(y,x),2*np.pi)
    modes=[]
    for order in sorted({0,degree}):
        harmonic=sph_harm_y(degree,order,theta,phi)
        components=(harmonic.real,) if order==0 else (harmonic.real,harmonic.imag)
        modes.extend(np.asarray(value,dtype=np.float64) for value in components)
    return tuple(modes)


def analyze_operator_spectrum(
    mesh:GeodesicMesh,degrees:NDArray[np.int64]|None=None
)->OperatorSpectrum:
    if degrees is None:
        degrees=np.arange(1,101,dtype=np.int64)
    degree_values=np.asarray(degrees,dtype=np.int64)
    if degree_values.ndim!=1 or len(degree_values)==0 or np.any(degree_values<1):
        raise ValueError("degrees must be a nonempty one-dimensional positive array")
    areas=mesh.dual_cell_solid_angles
    eigen_mean=[];eigen_max=[];wave_mean=[];wave_max=[];res_mean=[];res_max=[];counts=[]
    for degree in degree_values:
        exact=float(degree*(degree+1));e_errors=[];k_errors=[];residuals=[]
        for field in _real_modes(mesh,int(degree)):
            applied=scalar_laplacian(mesh,field)
            norm=float(np.sum(areas*field**2))
            effective=-float(np.sum(areas*field*applied))/norm
            e_errors.append(effective/exact-1)
            k_errors.append(np.sqrt(max(effective,0)/exact)-1)
            residual=applied+effective*field
            residuals.append(float(np.sqrt(np.sum(areas*residual**2)/(exact**2*norm))))
        counts.append(len(e_errors));eigen_mean.append(np.mean(e_errors));eigen_max.append(np.max(np.abs(e_errors)));wave_mean.append(np.mean(k_errors));wave_max.append(np.max(np.abs(k_errors)));res_mean.append(np.mean(residuals));res_max.append(np.max(residuals))
    return OperatorSpectrum(degree_values,np.asarray(counts),np.asarray(eigen_mean),np.asarray(eigen_max),np.asarray(wave_mean),np.asarray(wave_max),np.asarray(res_mean),np.asarray(res_max))


def write_csv(results:dict[str,OperatorSpectrum],output:str|Path)->Path:
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    rows=["grid,degree,mode_count,eigenvalue_relative_error_mean,eigenvalue_relative_error_max_abs,wavenumber_relative_error_mean,wavenumber_relative_error_max_abs,eigenfunction_residual_mean,eigenfunction_residual_max"]
    for label,result in results.items():
        for i,degree in enumerate(result.degree):
            values=(degree,result.mode_count[i],result.eigenvalue_relative_error_mean[i],result.eigenvalue_relative_error_max_abs[i],result.wavenumber_relative_error_mean[i],result.wavenumber_relative_error_max_abs[i],result.eigenfunction_residual_mean[i],result.eigenfunction_residual_max[i])
            rows.append(label+","+",".join(f"{v:.12g}" for v in values))
    output.write_text("\n".join(rows)+"\n",encoding="utf-8");return output


def render(results:dict[str,OperatorSpectrum],output:str|Path)->Path:
    import matplotlib.pyplot as plt
    output=Path(output);figure,axes=plt.subplots(3,1,figsize=(11,11),sharex=True,constrained_layout=True)
    for label,result in results.items():
        axes[0].plot(result.degree,100*result.eigenvalue_relative_error_mean,label=label)
        axes[1].plot(result.degree,100*result.wavenumber_relative_error_mean,label=label)
        axes[2].plot(result.degree,100*result.eigenfunction_residual_mean,label=label)
    for ax in axes:
        ax.axvspan(8.55785,75.5659,color="0.9",label="50–500 Hz" if ax is axes[0] else None);ax.grid(True,color="0.92");ax.legend(ncol=2,fontsize=8)
    axes[0].set_ylabel("Eigenvalue error (%)");axes[1].set_ylabel("Wavenumber error (%)");axes[2].set_ylabel("Eigenfunction residual (%)");axes[2].set_xlabel("Spherical-harmonic degree l")
    figure.savefig(output,dpi=180,facecolor="white");plt.close(figure);return output
