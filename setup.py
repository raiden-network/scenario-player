from setuptools import setup, find_namespace_packages

setup(
    name='raiden-scenario-player',
    packages=find_namespace_packages(),
    package_data={
        '': [
            '*.yaml',
            '/*.yml',
        ],
    },

    entry_points={
        'console_scripts': [
            'scenario-player=raiden.scenario_player.main:main',
            'scenario-player-nightlies=raiden.scenario_player.scenarios.__init__:run_builtin_scenarios',
        ],
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
