from setuptools import setup

setup(
    name='raiden-scenario-player',
    packages=['raiden.scenario_player'],
    package_data={'scenario_player': ['scenarios/*.yaml', 'scenarios/*.yml']},
    entry_points={
        'console_scripts': ['raiden.scenario_player.cli:main'],
    }
)
