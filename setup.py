import io
import os
import re

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'src', 'cmlibs', 'exporter', '__init__.py')) as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fd.read(), re.MULTILINE).group(1)

if not version:
    raise RuntimeError('Cannot find version information')


def readfile(filename, split=False):
    with io.open(filename, encoding="utf-8") as stream:
        if split:
            return stream.read().split("\n")
        return stream.read()


readme = readfile("README.rst", split=True)
readme.append('License')
readme.append('=======')
readme.append('')
readme.append('::')
readme.append('')
readme.append('')

software_licence = readfile("LICENSE")

requires = [
    'cmlibs.argon >= 0.4.0',
    'cmlibs.zinc',
    'svgpathtools_light @ https://github.com/hsorby/svgpathtools-light/releases/download/1.6.2rc1/svgpathtools_light-1.6.2rc1-py2.py3-none-any.whl',
]

setup(
    name='cmlibs.exporter',
    version=version,
    description='CMLibs Export functions.',
    long_description='\n'.join(readme) + software_licence,
    long_description_content_type='text/x-rst',
    classifiers=[],
    author='Hugh Sorby',
    author_email='h.sorby@auckland.ac.nz',
    url='https://github.com/CMLibs-Bindings/cmlibs.exporter',
    license='Apache Software License',
    license_files=("LICENSE",),
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
    extras_require={
        "thumbnail_hardware": ["PySide6"],
        "thumbnail_software": ["PyOpenGL"],
    }

)
