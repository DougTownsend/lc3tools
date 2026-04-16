from setuptools import setup, Extension
from pybind11.setup_helpers import build_ext
import pybind11
import glob
import sys
import subprocess

import os

# On macOS, Homebrew installs Qt as keg-only — its pkg-config files
# aren't on the default search path.  Auto-detect and add them.
if sys.platform == 'darwin':
    try:
        brew_qt = subprocess.check_output(
            ["brew", "--prefix", "qt"], stderr=subprocess.DEVNULL
        ).decode().strip()
        qt_pc = os.path.join(brew_qt, "lib", "pkgconfig")
        if os.path.isdir(qt_pc):
            pkg_path = os.environ.get("PKG_CONFIG_PATH", "")
            if qt_pc not in pkg_path:
                os.environ["PKG_CONFIG_PATH"] = qt_pc + (":" + pkg_path if pkg_path else "")
    except Exception:
        pass

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

# curs_main.cpp uses ncurses+Qt5 — only compile it on Unix
core_cli_sources = [s for s in cli_sources if "curs_main" not in s]

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
cli_ext_sources  = cli_sources  # all cli/*.cpp including curs_main

if sys.platform == 'win32':
    # Windows: enable curs_main when Qt + PDCurses are available.
    # CI sets QT_ROOT_DIR (or Qt6_DIR / Qt5_DIR) via install-qt-action;
    # PDCurses comes from vcpkg (VCPKG_INSTALLATION_ROOT).
    #
    # install-qt-action sets Qt6_DIR to .../lib/cmake/Qt6 (cmake config),
    # but we need the root (which has include/ and lib/).  QT_ROOT_DIR
    # points there directly; otherwise walk up from the cmake path.
    qt_root = os.environ.get('QT_ROOT_DIR', '')
    if not qt_root:
        cmake_dir = os.environ.get('Qt6_DIR', os.environ.get('Qt5_DIR', ''))
        if cmake_dir and os.path.isdir(cmake_dir):
            # .../lib/cmake/Qt6 → go up 3 levels to the root
            qt_root = os.path.dirname(os.path.dirname(os.path.dirname(cmake_dir)))

    vcpkg = os.environ.get('VCPKG_INSTALLATION_ROOT', '')

    if qt_root and os.path.isdir(os.path.join(qt_root, 'include')):
        cli_ext_sources = cli_sources  # include curs_main.cpp
        cli_compile_args.append("-DHAS_CURS_MAIN")

        # Detect Qt version: check which env var led us here
        qt_ver = 6 if os.environ.get('Qt6_DIR', '') else 5

        # Qt headers
        qt_inc = os.path.join(qt_root, 'include')
        for sub in ['', 'QtCore', 'QtGui', 'QtWidgets']:
            d = os.path.join(qt_inc, sub) if sub else qt_inc
            if os.path.isdir(d):
                cli_include_dirs.append(d)
        cli_lib_dirs.append(os.path.join(qt_root, 'lib'))
        pfx = 'Qt6' if qt_ver == 6 else 'Qt5'
        cli_libraries.extend([pfx + 'Core', pfx + 'Gui', pfx + 'Widgets'])

        # PDCurses via vcpkg
        if vcpkg:
            triplet = 'x64-windows'
            cli_include_dirs.append(
                os.path.join(vcpkg, 'installed', triplet, 'include'))
            cli_lib_dirs.append(
                os.path.join(vcpkg, 'installed', triplet, 'lib'))
        cli_libraries.append('pdcurses')
    else:
        # No Qt available — exclude curs_main.cpp
        cli_ext_sources = core_cli_sources
else:
    # Unix: enable curs_main with ncurses + Qt (try Qt6, fall back to Qt5)
    qt_cflags = _pkgconfig("--cflags", "Qt6Widgets")
    qt_libs   = _pkgconfig("--libs",   "Qt6Widgets")
    if not qt_cflags and not qt_libs:
        qt_cflags = _pkgconfig("--cflags", "Qt5Widgets")
        qt_libs   = _pkgconfig("--libs",   "Qt5Widgets")

    print(f"[setup.py] pkg-config Qt6Widgets cflags: {_pkgconfig('--cflags', 'Qt6Widgets')}")
    print(f"[setup.py] pkg-config Qt5Widgets cflags: {_pkgconfig('--cflags', 'Qt5Widgets')}")
    print(f"[setup.py] qt_cflags={qt_cflags}")
    print(f"[setup.py] qt_libs={qt_libs}")
    print(f"[setup.py] PKG_CONFIG_PATH={os.environ.get('PKG_CONFIG_PATH', 'NOT SET')}")

    if qt_cflags or qt_libs:
        # Qt found via pkg-config — enable curs_main (lc3pysim TUI)
        cli_ext_sources = cli_sources
        cli_compile_args.append("-DHAS_CURS_MAIN")
        cli_libraries.append("ncurses")
        cli_include_dirs += [f[2:] for f in qt_cflags if f.startswith("-I")]
        cli_compile_args += [f for f in qt_cflags if not f.startswith("-I")]
        cli_lib_dirs     += [f[2:] for f in qt_libs if f.startswith("-L")]
        cli_libraries    += [f[2:] for f in qt_libs if f.startswith("-l")]
        cli_link_args    += [f for f in qt_libs if not f.startswith(("-L", "-l"))]
    elif sys.platform == 'darwin':
        # macOS fallback: Homebrew Qt6 doesn't ship pkg-config files.
        # Detect Qt frameworks directly from brew --prefix.
        try:
            brew_qt = subprocess.check_output(
                ["brew", "--prefix", "qt"], stderr=subprocess.DEVNULL
            ).decode().strip()
            qt_lib = os.path.join(brew_qt, "lib")
            qt_fw = os.path.join(qt_lib, "QtCore.framework")
            print(f"[setup.py] brew Qt prefix: {brew_qt}")
            print(f"[setup.py] Qt lib dir: {qt_lib} exists={os.path.isdir(qt_lib)}")
            print(f"[setup.py] QtCore.framework: {qt_fw} exists={os.path.isdir(qt_fw)}")
            if os.path.isdir(qt_fw):
                # Framework-style Qt (standard on macOS Homebrew)
                cli_ext_sources = cli_sources
                cli_compile_args.append("-DHAS_CURS_MAIN")
                cli_libraries.append("ncurses")
                cli_compile_args.append("-F" + qt_lib)
                cli_link_args += ["-F" + qt_lib,
                                  "-framework", "QtCore",
                                  "-framework", "QtGui",
                                  "-framework", "QtWidgets"]
                # Framework headers: lib/QtCore.framework/Headers/
                for sub in ['QtCore', 'QtGui', 'QtWidgets']:
                    fw_inc = os.path.join(qt_lib, sub + ".framework", "Headers")
                    if os.path.isdir(fw_inc):
                        cli_include_dirs.append(fw_inc)
            elif os.path.isdir(os.path.join(brew_qt, "include")):
                # Non-framework Qt (rare on macOS)
                cli_ext_sources = cli_sources
                cli_compile_args.append("-DHAS_CURS_MAIN")
                cli_libraries.append("ncurses")
                qt_inc = os.path.join(brew_qt, "include")
                cli_include_dirs.append(qt_inc)
                for sub in ['QtCore', 'QtGui', 'QtWidgets']:
                    d = os.path.join(qt_inc, sub)
                    if os.path.isdir(d):
                        cli_include_dirs.append(d)
                cli_lib_dirs.append(qt_lib)
                cli_libraries.extend(['Qt6Core', 'Qt6Gui', 'Qt6Widgets'])
        except Exception as e:
            print(f"[setup.py] macOS Qt detection failed: {e}")
    else:
        # No Qt available — build without lc3pysim (lc3asm and lc3sim still work)
        cli_ext_sources = core_cli_sources

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
