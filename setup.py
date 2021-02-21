import re

from setuptools import setup, find_packages

with open("src/pierogis_bot/__init__.py", encoding="utf8") as f:
    version = re.search(r'__version__ = \'(.*?)\'', f.read()).group(1)

setup(
    name='pierogis-bot',
    version=version,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=[
        'requests>=2.25.1',
        'requests-oauthlib',
        'boto3',
        'pyrogis>=0.2.0'
    ],
    extras_require={
        'yaml': ['pyaml'],
        'lambda_local': ['python-lambda-local']
    },
    entry_points={
        'console_scripts': [
            'pierogis_bot=pierogis_bot.__main__:main'
        ]
    }
)
