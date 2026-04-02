from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="shadowclaude",
    version="0.1.0",
    author="ShadowClaude Team",
    author_email="team@shadowclaude.ai",
    description="The Open Source AI Coding Assistant - Based on Claude Code Architecture",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/520llw/shadowclaude",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Tools",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
        "schedule>=1.2.0",
        "pycryptodome>=3.19.0",
        "pysilk-mod>=1.6.4",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "black>=23.0",
            "mypy>=1.0",
        ],
        "voice": [
            "pysilk-mod>=1.6.4",
        ],
    },
    entry_points={
        "console_scripts": [
            "shadowclaude=shadowclaude.__main__:main",
            "sc=shadowclaude.__main__:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
