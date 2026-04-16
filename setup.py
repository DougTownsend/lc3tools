from setuptools import setup, Extension
from pybind11.setup_helpers import build_ext
import pybind11
import glob
import os
import sys
import subprocess

def _pkgconfig(*args):
    try:
        out = subprocess.check_output(["pkg-config"] + list(args),
                                      stderr=subprocess.DEVNULL)
        return out.decode().split()
    except Exception:
        return []

compile_args_base = []
if sys.platform == 'win32':
    compile_args_base = ['/std:c++17', '/EHsc', '/Zc:__cplusplus']
else:
    compile_args_base = [
        '-Wno-error=format-security',
        '-Wno-format-security',
        '-fvisibility=default',
        '-std=c++17',
    ]

backend_sources = [
    *glob.glob("src/backend/*.cpp"),
    *glob.glob("src/utils/*.cpp"),
    *glob.glob("src/common/*.cpp"),
]

cli_sources = glob.glob("src/cli/*.cpp")

# curs_main.cpp uses ncurses + SDL2 — only compile when both are available
core_cli_sources = [s for s in cli_sources
                    if "curs_main" not in s and "tinyfiledialogs" not in s]

include_dirs = [
    pybind11.get_include(),
    "src/backend",
    "src/utils",
    "include",
    "src/cli",
    "src/common",
]

# --- cli_bindings: platform-specific configuration ---
cli_compile_args = list(compile_args_base) + ["-DBUILDING_CLI_BINDINGS"]
cli_include_dirs = list(include_dirs)
cli_lib_dirs     = []
cli_libraries    = []
cli_link_args    = []
cli_ext_sources  = core_cli_sources  # default: no curs_main

if sys.platform == 'win32':
    # Windows: enable curs_main when SDL2 + PDCurses are available via vcpkg.
    vcpkg = os.environ.get('VCPKG_INSTALLATION_ROOT', '')
    if vcpkg:
        triplet = 'x64-windows'
        vroot = os.path.join(vcpkg, 'installed', triplet)
        sdl2_inc = os.path.join(vroot, 'include', 'SDL2')
        if os.path.isdir(sdl2_inc):
            cli_ext_sources = cli_sources
            cli_compile_args.append("-DHAS_CURS_MAIN")
            cli_include_dirs.append(sdl2_inc)
            cli_include_dirs.append(os.path.join(vroot, 'include'))
            cli_lib_dirs.append(os.path.join(vroot, 'lib'))
            cli_libraries.extend(['SDL2', 'pdcurses'])
else:
    # Unix: enable curs_main with ncurses + SDL2
    sdl2_cflags = _pkgconfig("--cflags", "sdl2")
    sdl2_libs   = _pkgconfig("--libs",   "sdl2")

    if sdl2_cflags or sdl2_libs:
        cli_ext_sources = cli_sources
        cli_compile_args.append("-DHAS_CURS_MAIN")
        cli_libraries.append("ncurses")
        cli_include_dirs += [f[2:] for f in sdl2_cflags if f.startswith("-I")]
        cli_compile_args += [f for f in sdl2_cflags if not f.startswith("-I")]
        cli_lib_dirs     += [f[2:] for f in sdl2_libs if f.startswith("-L")]
        cli_libraries    += [f[2:] for f in sdl2_libs if f.startswith("-l")]
        cli_link_args    += [f for f in sdl2_libs if not f.startswith(("-L", "-l"))]

ext_modules = [
    Extension(
        "lc3py.core",
        sources=["bindings.cpp"] + backend_sources + core_cli_sources,
        include_dirs=include_dirs,
        language='c++',
        extra_compile_args=compile_args_base,
    ),

    Extension(
        "lc3py.cli_bindings",
        sources=["bindings.cpp"] + backend_sources + cli_ext_sources,
        include_dirs=cli_include_dirs,
        language='c++',
        extra_compile_args=cli_compile_args,
        library_dirs=cli_lib_dirs,
        libraries=cli_libraries,
        extra_link_args=cli_link_args,
    ),
]

setup(
    name="lc3sim",
    version="0.2.0",
    packages=["lc3py"],
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    package_data={'lc3py': ['*.py']},
    zip_safe=False,
)
