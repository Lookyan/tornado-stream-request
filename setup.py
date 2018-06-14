from distutils.core import setup

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='tornado-streaming-parser',
    version='0.1',
    description='Streaming HTTP multipart/form-data body parser for Tornado',
    packages=[
        'streamparser'
    ],
    install_requires=required
)
