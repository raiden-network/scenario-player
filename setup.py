from setuptools import setup, find_namespace_packages

setup(
    name='raiden-scenario-player',
    packages=find_namespace_packages(),
    package_data={'scenario_player': ['scenarios/*.yaml', 'scenarios/*.yml']},
    entry_points={
        'console_scripts': ['scenario-player=raiden.scenario_player.main:main'],
    },
    requires=[
        'raiden',
        'flask',
        'flasgger',
        'requests',
        'pyyaml',
        'redis',
        'gevent',
        'urwid',
    ],
)
