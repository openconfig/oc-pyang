"""setup_tools file definition for oc-pyang."""
from os import path
from pip.req import parse_requirements
from setuptools import find_packages
from setuptools import setup
from codecs import open

import openconfig_pyang

thisdir = path.abspath(path.dirname(__file__))
pip_reqs = parse_requirements(path.join(thisdir, "requirements.txt"),
                              session=False)
inst_reqs = [str(ir.req) for ir in pip_reqs]

setup(
    name="openconfig_pyang",
    version=openconfig_pyang.__version__,
    description=("OpenConfig Pyang provides plugins for the Pyang validator "
                 "that provide functionality which relates to OpenConfig "
                 " data models. Particularly, it provides a linter, path "
                 " extractor, and documentation generator."),

    url="https://github.com/openconfig/oc-pyang",

    author="The OpenConfig Authors",
    author_email="netopenconfig@googlegroups.com",

    license="Apache",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Telecommunications Industry",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Code Generators",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 2 :: Only"
    ],
    include_package_data=True,
    keywords="yang pyang openconfig",
    packages=find_packages(),
    install_requires=inst_reqs,
    zip_safe=False,
)
