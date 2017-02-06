try:
    import ez_setup
    ez_setup.use_setuptools()
except ImportError:
    pass

from setuptools import setup

setup(
    name='fit test pathing',
    version='0.1',
    author='James Turnquist',
    author_email='james.turnquist@dell.com',
    description='setup pathing for RackHD/test',
    license='Apache 2.0',
    packages=[],
    entry_points={}
)
