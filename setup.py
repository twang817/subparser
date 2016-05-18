import io

from setuptools import setup, find_packages

version = io.open('subparser/_version.py').readlines()[-1].split()[-1].strip('"\'')

setup(
    name='subparser',
    version=version,

    description='utility class for handling argparse subparsers',

    author='Tommy Wang',
    author_email='twang@august8.net',
    url='http://github.com/twang817/subparser',
    download_url='http://github.com/twang817/subparser/tarball/{version}'.format(version=version),

    packages=find_packages(),
    install_requires=['six'],

    license='PSF',
)
