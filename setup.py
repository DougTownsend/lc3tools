from setuptools import setup, Extension
from pybind11.setup_helpers import build_ext
import pybind11
import glob
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
if sys.platform != 'win32':
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

# curs_main.cpp uses ncurses+Qt5 — only compile it into cli_bindings
core_cli_sources = [s for s in cli_sources if "curs_main" not in s]

include_dirs = [
    pybind11.get_include(),
    "src/backend",
    "src/utils",
    "include",
    "src/cli",
    "src/common",
]

# Qt5 flags (for cli_bindings only)
qt5_cflags = _pkgconfig("--cflags", "Qt5Widgets")
qt5_libs   = _pkgconfig("--libs",   "Qt5Widgets")

# Separate Qt5 lib flags into -L/-l vs linker args
qt5_lib_dirs  = [f[2:] for f in qt5_libs if f.startswith("-L")]
qt5_link_libs = [f[2:] for f in qt5_libs if f.startswith("-l")]
qt5_extra_link = [f for f in qt5_libs if not f.startswith(("-L", "-l"))]

# ncurses
ncurses_lib = "pdcurses" if sys.platform == "win32" else "ncurses"

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
        sources=["bindings.cpp"] + backend_sources + cli_sources,
        include_dirs=include_dirs + [f[2:] for f in qt5_cflags if f.startswith("-I")],
        language='c++',
        extra_compile_args=compile_args_base
            + [f for f in qt5_cflags if not f.startswith("-I")]
            + ["-DBUILDING_CLI_BINDINGS"],
        library_dirs=qt5_lib_dirs,
        libraries=[ncurses_lib] + qt5_link_libs,
        extra_link_args=qt5_extra_link,
    ),
]

setup(
    name="lc3py",
    version="0.1.0",
    packages=["lc3py"],
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    package_data={'lc3py': ['*.py']},
    zip_safe=False,
)
