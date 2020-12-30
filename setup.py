from setuptools import setup, find_packages

setup(
    name='pierogis-bot',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'requests>=2.25.1',
        'requests-oauthlib',
        'boto3',
        'pierogis>=0.0.2'
    ],
    extras_require={
        "yaml": ["pyaml"],
        "lambda_local": ["python-lambda-local"]
    }
)
