from setuptools import setup, Extension
from pybind11.setup_helpers import build_ext
import pybind11
import glob
import os
import sys

compile_args = []
if sys.platform != 'win32':
    compile_args = ['-Wno-error=format-security', '-Wno-format-security', '-fvisibility=default', '-std=c++11']

sources = [
    "bindings.cpp",
    *glob.glob("src/backend/*.cpp"),
    *glob.glob("src/utils/*.cpp"),
    *glob.glob("src/cli/*.cpp"),
    *glob.glob("src/common/*.cpp"),
]

include_dirs = [
    pybind11.get_include(),
    "src/backend",
    "src/utils",
    "include",
    "src/cli",
    "src/common",
]

ext_modules = [
    Extension(
        "lc3py.core",
        sources=sources,
        include_dirs=include_dirs,
        language='c++',
        extra_compile_args=compile_args,
    ),

    Extension(
        "lc3py.cli_bindings",
        sources=sources,
        include_dirs=include_dirs,
        language='c++',
        extra_compile_args=compile_args,
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