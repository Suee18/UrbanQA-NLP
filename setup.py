from setuptools import setup, find_packages

setup(
    name="urbanqa",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    py_modules=["ask"],
)
