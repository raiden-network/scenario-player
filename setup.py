from setuptools import setup, find_packages

setup(
    name='raiden-scenario-player',
    packages=find_packages(),
    package_data={
        '': [
            '*.yaml',
            '/*.yml',
        ],
    },

    entry_points={
        'console_scripts': [
            'scenario-player=scenario_player.main:main',
            'scenario-player-nightlies=scenario_player.scenarios.__init__:run_builtin_scenarios',
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
