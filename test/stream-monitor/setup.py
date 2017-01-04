"""
todo: add
"""
try:
    import ez_setup
    ez_setup.use_setuptools()
except ImportError:
    pass

from setuptools import setup

setup(
    name='stream monitors',
    version='0.1',
    author='Stuart Stanley',
    author_email = 'stuart.stanley@dell.com',
    description = 'Stream-monitors and test-log-groupers',
    license = 'Apache 2.0',
    packages = ['sm_plugin', 'stream_sources', 'flogging'],
    entry_points = {
        'nose.plugins.0.10': [
            'stream_monitor = sm_plugin:StreamMonitorPlugin'
            ]
        }
    )
