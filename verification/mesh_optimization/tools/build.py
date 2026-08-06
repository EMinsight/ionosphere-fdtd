#!/usr/bin/env python3
"""Build the pinned Sandia Mesquite master snapshot and sphere optimizer."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile

MESQUITE_COMMIT = "7ae51c8e8617c67e63018c8a7effc0f5455f58b4"
MESQUITE_ARCHIVE_SHA256 = (
    "64cb1162807a1e99e3bfc6288ccf91b3dc43dbf30fabeda6c3126021e18a0a4a"
)
MESQUITE_ARCHIVE_URL = (
    "https://raw.githubusercontent.com/sandialabs/mesquite/"
    f"{MESQUITE_COMMIT}/mesquite/mesquite-master.zip"
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=Path("build/mesquite"),
        help="download, source, and build root (default: build/mesquite)",
    )
    parser.add_argument(
        "--cmake",
        default="cmake",
        help="CMake executable (default: cmake from PATH)",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=min(os.cpu_count() or 1, 4),
        help="parallel build jobs (default: up to 4)",
    )
    return parser


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _download(archive: Path) -> None:
    if archive.exists():
        if _sha256(archive) == MESQUITE_ARCHIVE_SHA256:
            return
        raise RuntimeError(f"existing archive has the wrong SHA-256: {archive}")
    temporary = archive.with_suffix(".download")
    try:
        with urllib.request.urlopen(MESQUITE_ARCHIVE_URL) as response:
            with temporary.open("wb") as output:
                shutil.copyfileobj(response, output)
        actual = _sha256(temporary)
        if actual != MESQUITE_ARCHIVE_SHA256:
            raise RuntimeError(
                "Mesquite archive SHA-256 mismatch: "
                f"expected {MESQUITE_ARCHIVE_SHA256}, got {actual}"
            )
        temporary.replace(archive)
    finally:
        temporary.unlink(missing_ok=True)


def _prepare_source(archive: Path, source: Path) -> None:
    marker = source / ".ionosphere-mesquite-source"
    if source.exists():
        if marker.read_text().strip() == MESQUITE_ARCHIVE_SHA256:
            return
        raise RuntimeError(f"unrecognized source directory already exists: {source}")

    source.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(source.parent)
    extracted = source.parent / "mesquite-master"
    if extracted != source:
        extracted.rename(source)

    # The archived standalone CMake path calls this Trilinos-only bookkeeping
    # macro without defining it. The macro does not affect compilation.
    cmake_file = source / "CMakeLists.txt"
    contents = cmake_file.read_text()
    anchor = "  ENDMACRO()\n\n  SET( ${PACKAGE_NAME}_ENABLE_TESTS"
    replacement = (
        "  ENDMACRO()\n\n"
        "  MACRO(TRIBITS_EXCLUDE_FILES)\n"
        "  ENDMACRO()\n\n"
        "  SET( ${PACKAGE_NAME}_ENABLE_TESTS"
    )
    if anchor not in contents:
        raise RuntimeError("cannot apply the standalone Mesquite CMake compatibility fix")
    cmake_file.write_text(contents.replace(anchor, replacement, 1))
    marker.write_text(MESQUITE_ARCHIVE_SHA256 + "\n")


def _run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True)


def _build_adapter(source: Path, cmake_build: Path, output: Path) -> None:
    compiler = shutil.which("c++")
    if compiler is None:
        raise RuntimeError("a C++ compiler named 'c++' is required")
    include_directories = {
        source / "src" / "include",
        cmake_build,
        cmake_build / "src" / "include",
    }
    include_directories.update(
        path.parent for path in (source / "src").rglob("*.hpp")
    )
    adapter = Path(__file__).with_name("optimize_sphere.cpp").resolve()
    library = cmake_build / "src" / "libmesquite.a"
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        compiler,
        "-std=c++11",
        "-O3",
        "-DNDEBUG",
        *[f"-I{path}" for path in sorted(include_directories)],
        str(adapter),
        str(library),
        "-lm",
        "-o",
        str(output),
    ]
    _run(command)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.jobs < 1:
        raise SystemExit("--jobs must be positive")
    cmake = shutil.which(args.cmake) if os.sep not in args.cmake else args.cmake
    if not cmake or not Path(cmake).is_file():
        raise SystemExit(f"CMake executable not found: {args.cmake}")

    root = args.build_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    archive = root / "mesquite-master.zip"
    source = root / "source"
    cmake_build = root / "cmake-build"
    executable = root / "bin" / "ionosphere-mesquite-optimize"

    _download(archive)
    _prepare_source(archive, source)
    _run(
        [
            str(cmake),
            "-S",
            str(source),
            "-B",
            str(cmake_build),
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            "-DMesquite_ENABLE_TESTS=OFF",
            "-DMesquite_ENABLE_TRAP_FPE=OFF",
        ]
    )
    _run([str(cmake), "--build", str(cmake_build), "--parallel", str(args.jobs)])
    _build_adapter(source, cmake_build, executable)
    print(f"mesquite_commit={MESQUITE_COMMIT}")
    print(f"mesquite_archive_sha256={MESQUITE_ARCHIVE_SHA256}")
    print(f"optimizer={executable}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
