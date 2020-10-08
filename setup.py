# -*- coding: utf-8 -*-

'''setup.py - Waqas Bhatti (wbhatti@astro.princeton.edu) - Nov 2016

This sets up the package.

Stolen from http://python-packaging.readthedocs.io/en/latest/everything.html and
modified by me.

'''
import versioneer
__version__ = versioneer.get_version()

from setuptools import setup, find_packages

# set up the cmdclass
cmdclass = versioneer.get_cmdclass()


# get the readme
def readme():
    with open('README.md') as f:
        return f.read()


# let's be lazy and put requirements in one place
# what could possibly go wrong?
with open('requirements.txt') as infd:
    INSTALL_REQUIRES = [x.strip('\n') for x in infd.readlines()]

EXTRAS_REQUIRE = {}

###############
## RUN SETUP ##
###############

setup(
    name='astrocoffee',
    version=__version__,
    cmdclass=cmdclass,
    description=('A small Tornado webapp to review and '
                 'vote on daily astro-ph arXiv paper listings.'),
    long_description=readme(),
    long_description_content_type="text/markdown",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Astronomy",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ],
    keywords='astronomy,arxiv,astro-ph,tornado',
    url='https://github.com/waqasbhatti/astroph-coffee',
    author='Waqas Bhatti',
    author_email='waqas.afzal.bhatti@gmail.com',
    license='MIT',
    packages=find_packages(),
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    entry_points={
        'console_scripts':[
            'astrocoffee-server=astrocoffee.coffeeserver:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
    python_requires='>=3.6',
)
