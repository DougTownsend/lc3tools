from setuptools import setup, Extension
import pybind11
import os
import glob

base_path = os.path.abspath("..")

# Automatically grab all backend and utility source files 
# to ensure the simulator has all its logic linked
sources = [
    "bindings.cpp",
    *glob.glob(os.path.join(base_path, "src/backend/*.cpp")),
    *glob.glob(os.path.join(base_path, "src/utils/*.cpp")),
]

ext_modules = [
    Extension(
        "lc3py",
        sources,
        include_dirs=[
            pybind11.get_include(),
            os.path.join(base_path, "src/backend"),
            os.path.join(base_path, "src/utils"),
            os.path.join(base_path, "include"),
        ],
        language='c++',
        extra_compile_args=[
            '-Wno-error=format-security',
            '-Wno-format-security'
        ],
    ),
]

setup(
    ext_modules=ext_modules,
)
