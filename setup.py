from setuptools import setup, find_packages


setup(
    name='msl',
    version='0.1.0',
    author='Hannes Nikulski',
    author_email='hannes@nikulski.net',
    description='MSL Compiler',

    packages=find_packages(exclude=["tests"]),
    url='https://github.com/Malmosmo/MSL',
    license='LICENSE',

    long_description=open('README.md').read(),
)