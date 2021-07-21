from setuptools import find_packages, setup


def get_readme():
    """Load README.rst for display on PyPI."""
    with open("README.rst") as fhandle:
        return fhandle.read()


with open('glompo/_version.py', 'r') as file:
    exec(file.read())

setup(
    name="glompo",
    version=__version__,
    description="Globally managed parallel optimization",
    long_description=get_readme(),
    author="Michael Freitas Gustavo",
    author_email="michael.freitasgustavo@ugent.be",
    url="https://github.com/mfgustavo/glompo",
    download_url="https://github.com/mfgustavo/glompo",
    packages=find_packages(),
    license_file='LICENSE',
    include_package_data=True,
    package_dir={"glompo": "glompo"},
    install_requires=['numpy', 'PyYAML', 'tables'],
    python_requires='>=3.6',
    extras_require={
        'Docs': ['sphinx==1.8.5', 'sphinx-rtd-theme==0.2.4'],
        'Plotting': ['matplotlib'],
        'Video': ['matplotlib>=3.0, <3.4', 'ffmpeg', 'PySide2'],
        'PerturbationGenerator': ['scipy'],
        'UnitTesting': ['pytest>=4.4'],
        'CMAOptimizer': ['cma>=2.7, <3'],
        'GFLSOptimizer': ['optsam'],
        'Nevergrad': ['nevergrad'],
        'ParAMSWrapper': ['scm'],
        'Checkpointing': ['dill>=0.2.7'],
        'ResourceUsageStatusPrinting': ['psutil>=5.6.2']
    }
)
