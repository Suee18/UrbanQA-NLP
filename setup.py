from setuptools import setup, find_packages

_pkgs = find_packages(where="src")

setup(
    name="urbanqa",
    packages=_pkgs,
    package_dir={p: "src/" + p.replace(".", "/") for p in _pkgs},
    py_modules=["ask"],
)
