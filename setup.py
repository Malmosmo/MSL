from setuptools import setup, find_packages
from pip.req import parse_requirements

install_reqs = parse_requirements("requirements.txt")
reqs = [str(ir.req) for ir in install_reqs]

setup(
    name='msl',
    version='0.1.0',
    author='Hannes Nikulski',
    author_email='hannes@nikulski.net',
    description='MSL Compiler',

    packages=find_packages(exclude=["tests"]),
    url='https://github.com/Malmosmo/MSL',
    license='LICENSE',

    install_requires=reqs,
    long_description=open('README.md').read(),
)
