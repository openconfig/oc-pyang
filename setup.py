"""Copyright 2016 The OpenConfig Authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

setup_tools file definition for oc-pyang.
"""

from os import path
from setuptools import find_packages
from setuptools import setup
from codecs import open

# support both older pip (<=9.0.3), and modern >=10
try:
    from pip._internal.req import parse_requirements
except ImportError:
    from pip.req import parse_requirements

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
    scripts=['bin/oclint'],
    install_requires=inst_reqs,
    zip_safe=False,
)
