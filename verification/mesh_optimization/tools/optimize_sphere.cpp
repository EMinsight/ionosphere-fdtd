#include "Mesquite_MeshImpl.hpp"
#include "Mesquite_MsqError.hpp"
#include "Mesquite_PaverMinEdgeLengthWrapper.hpp"
#include "Mesquite_SphericalDomain.hpp"

#include <cerrno>
#include <climits>
#include <cstdlib>
#include <iostream>

using namespace Mesquite;

namespace {

bool parse_positive_double(const char* text, double& value) {
  char* end = 0;
  errno = 0;
  value = std::strtod(text, &end);
  return errno == 0 && end != text && *end == '\0' && value > 0.0;
}

bool parse_positive_int(const char* text, int& value) {
  char* end = 0;
  errno = 0;
  const long parsed = std::strtol(text, &end, 10);
  if (errno != 0 || end == text || *end != '\0' || parsed < 1 || parsed > INT_MAX) {
    return false;
  }
  value = static_cast<int>(parsed);
  return true;
}

}  // namespace

int main(int argc, char** argv) {
  if (argc != 5) {
    std::cerr << "usage: ionosphere-mesquite-optimize "
                 "INPUT.vtk OUTPUT.vtk MOVEMENT_TOLERANCE MAX_ITERATIONS\n";
    return 64;
  }

  double movement_tolerance = 0.0;
  int max_iterations = 0;
  if (!parse_positive_double(argv[3], movement_tolerance) ||
      !parse_positive_int(argv[4], max_iterations)) {
    std::cerr << "movement tolerance and iteration limit must be positive\n";
    return 64;
  }

  MsqError error;
  MeshImpl mesh;
  mesh.read_vtk(argv[1], error);
  if (error) {
    std::cerr << "failed to read input mesh: " << error << '\n';
    return 2;
  }

  SphericalDomain sphere(Vector3D(0.0, 0.0, 0.0), 1.0);
  MeshDomainAssoc mesh_and_domain(&mesh, &sphere);

  // This wrapper constructs a uniform LambdaConstant ideal-shape target,
  // measures the target scale from the input mesh, evaluates TShapeSizeB1,
  // and minimizes its PMeanP objective with the TrustRegion vertex mover.
  PaverMinEdgeLengthWrapper optimizer(movement_tolerance, max_iterations);
  optimizer.run_instructions(&mesh_and_domain, error);
  if (error) {
    std::cerr << "Mesquite optimization failed: " << error << '\n';
    return 3;
  }

  mesh.write_vtk(argv[2], error);
  if (error) {
    std::cerr << "failed to write optimized mesh: " << error << '\n';
    return 4;
  }

  std::cout << "mesquite_version=" << version_string(false) << '\n';
  std::cout << "objective=uniform-shape-size:TShapeSizeB1:PMeanP(1)\n";
  std::cout << "vertex_mover=TrustRegion\n";
  return 0;
}
