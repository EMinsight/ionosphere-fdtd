import numpy as np
from verification.surface_impedance.model import surface_impedance_ohm,solve_curve
def test_surface_impedance_is_passive()->None:
 z=surface_impedance_ohm(250.);assert z.real>0;assert z.imag>0
def test_boundary_controls_return_lossy_modes()->None:
 f=np.asarray((100.,250.))
 for model in ('pec','bulk','impedance'):
  c=solve_curve(f,model,dz=500.);assert np.all(c.attenuation_db_per_mm>0);assert np.all((c.phase_velocity_fraction_c>.65)&(c.phase_velocity_fraction_c<1.05))
