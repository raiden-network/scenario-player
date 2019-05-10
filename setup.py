from setuptools import find_packages, setup

setup(
    name="raiden-scenario-player",
    packages=find_packages(),
    entry_points={"console_scripts": ["scenario-player=scenario_player.__main__:main"]},
    install_requires=[
        "raiden>=0.100.3",
        "flask",
        "flasgger",
        "requests",
        "pyyaml",
        "redis",
        "gevent",
        "urwid",
        "eth-utils",
        "structlog",
        "click",
    ],
)
