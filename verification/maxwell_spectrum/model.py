"""Analyze the DEC one-form Maxwell operator on spherical grids."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from scipy.special import sph_harm_y

from ionosphere_fdtd.mesh import GeodesicMesh

FloatArray=NDArray[np.float64]


@dataclass(frozen=True,slots=True)
class MaxwellSpectrum:
    degree:NDArray[np.int64]
    tm_eigenvalue_error:FloatArray
    te_eigenvalue_error:FloatArray
    tm_wavenumber_error:FloatArray
    te_wavenumber_error:FloatArray
    tm_residual:FloatArray
    te_residual:FloatArray
    polarization_splitting:FloatArray


def apply_one_form_hodge_laplacian(mesh:GeodesicMesh,edge_integrals:FloatArray)->FloatArray:
    """Apply positive ``d delta + delta d`` using the FDTD incidence/Hodge terms."""
    values=np.asarray(edge_integrals,dtype=np.float64)
    if values.shape!=(mesh.n_edges,):raise ValueError(f"edge_integrals must have shape ({mesh.n_edges},)")
    hodge=mesh.dual_edge_angles/mesh.primal_edge_angles
    divergence=mesh.dual_cell_circulation(hodge*values)/mesh.dual_cell_solid_angles
    gradient_part=-mesh.edge_difference(divergence)
    curl=mesh.face_circulation(values)/mesh.face_solid_angles
    curl_part=(mesh.primal_edge_angles/mesh.dual_edge_angles)*mesh.dual_edge_difference(curl)
    return gradient_part+curl_part


def _scalar_mode(mesh:GeodesicMesh,degree:int)->FloatArray:
    x,y,z=mesh.vertices.T;theta=np.arccos(np.clip(z,-1,1));phi=np.mod(np.arctan2(y,x),2*np.pi)
    return np.asarray(sph_harm_y(degree,degree,theta,phi).real,dtype=np.float64)


def _te_mode(mesh:GeodesicMesh,degree:int)->FloatArray:
    centers=mesh.face_centers;x,y,z=centers.T;theta=np.arccos(np.clip(z,-1,1));phi=np.mod(np.arctan2(y,x),2*np.pi)
    face=np.asarray(sph_harm_y(degree,degree,theta,phi).real,dtype=np.float64)
    return (mesh.primal_edge_angles/mesh.dual_edge_angles)*mesh.dual_edge_difference(face)


def _metrics(mesh:GeodesicMesh,mode:FloatArray,exact:float)->tuple[float,float]:
    applied=apply_one_form_hodge_laplacian(mesh,mode);weight=mesh.dual_edge_angles/mesh.primal_edge_angles
    norm=float(np.sum(weight*mode**2));effective=float(np.sum(weight*mode*applied)/norm)
    residual=float(np.sqrt(np.sum(weight*(applied-effective*mode)**2)/(exact**2*norm)))
    return effective,residual


def analyze_maxwell_spectrum(mesh:GeodesicMesh,degrees:NDArray[np.int64]|None=None)->MaxwellSpectrum:
    degree=np.arange(1,101,dtype=np.int64) if degrees is None else np.asarray(degrees,dtype=np.int64)
    if degree.ndim!=1 or len(degree)==0 or np.any(degree<1):raise ValueError("degrees must be positive")
    tm=[];te=[];tm_r=[];te_r=[]
    for value in degree:
        exact=float(value*(value+1));tm_value,tm_residual=_metrics(mesh,mesh.edge_difference(_scalar_mode(mesh,int(value))),exact);te_value,te_residual=_metrics(mesh,_te_mode(mesh,int(value)),exact)
        tm.append(tm_value);te.append(te_value);tm_r.append(tm_residual);te_r.append(te_residual)
    tm=np.asarray(tm);te=np.asarray(te);exact=degree*(degree+1)
    tm_error=tm/exact-1;te_error=te/exact-1
    return MaxwellSpectrum(degree,tm_error,te_error,np.sqrt(np.maximum(tm,0)/exact)-1,np.sqrt(np.maximum(te,0)/exact)-1,np.asarray(tm_r),np.asarray(te_r),(te-tm)/exact)


def write_csv(results:dict[str,MaxwellSpectrum],output:str|Path)->Path:
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);rows=["grid,degree,tm_eigenvalue_error,te_eigenvalue_error,tm_wavenumber_error,te_wavenumber_error,tm_residual,te_residual,polarization_splitting"]
    for label,r in results.items():
        for i,d in enumerate(r.degree):rows.append(label+","+",".join(f"{v:.12g}" for v in (d,r.tm_eigenvalue_error[i],r.te_eigenvalue_error[i],r.tm_wavenumber_error[i],r.te_wavenumber_error[i],r.tm_residual[i],r.te_residual[i],r.polarization_splitting[i])))
    output.write_text("\n".join(rows)+"\n",encoding="utf-8");return output


def render(results:dict[str,MaxwellSpectrum],output:str|Path)->Path:
    import matplotlib.pyplot as plt
    output=Path(output);fig,axes=plt.subplots(3,1,figsize=(11,11),sharex=True,constrained_layout=True)
    for label,r in results.items():
        axes[0].plot(r.degree,100*r.tm_wavenumber_error,label=label+" TM");axes[0].plot(r.degree,100*r.te_wavenumber_error,"--",label=label+" TE")
        axes[1].plot(r.degree,100*r.polarization_splitting,label=label)
        axes[2].plot(r.degree,100*r.tm_residual,label=label+" TM");axes[2].plot(r.degree,100*r.te_residual,"--",label=label+" TE")
    for ax in axes:ax.axvspan(8.55785,75.5659,color="0.9");ax.grid(True,color="0.92");ax.legend(ncol=3,fontsize=7)
    axes[0].set_ylabel("Wavenumber error (%)");axes[1].set_ylabel("TE−TM eigenvalue / exact (%)");axes[2].set_ylabel("Eigenmode residual (%)");axes[2].set_xlabel("Spherical-harmonic degree l")
    fig.savefig(output,dpi=180,facecolor="white");plt.close(fig);return output
