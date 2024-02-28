from setuptools import setup

setup(
    name="phitech",
    version="0.1.0",
    description="Trading tools",
    author="darchitect",
    packages=["phitech"],
    requirements=["click", "pyyaml", "dotted-dict"],
    entry_points={
        "console_scripts": [
            "pt=phitech.main:run",
        ],
    },
)
