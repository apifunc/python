"""
apifunc - Convert markdown files into organized project structures with code files
"""
from setuptools import setup, find_packages

setup(
    name="apifunc",
    version="0.1.2",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    description="Protocol Interface Functions",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="apifunc Team",
    author_email="info@apifunc.com",
    url="https://github.com/pi-func/python",
    install_requires=[
        "aiohttp>=3.8.0",
        "websockets>=10.0",
        "typing-extensions>=4.0.0",
        "redis>=4.0.0",
        "paho-mqtt>=1.6.0",
        "flask>=2.3.0",
        "requests>=2.31.0",
        "click>=8.1.0",
        "colorama>=0.4.6",
        "typing-extensions>=4.9.0",
        "pyyaml>=6.0.1",
        "fastapi>=0.110.0",
        "uvicorn>=0.27.0",
        "grpcio>=1.62.0",
        "grpcio-tools>=1.62.0",
    ],
    extras_require={
        "full": [
            "grpcio>=1.40.0",
            "paho-mqtt>=1.6.1",
            "pyzmq>=22.2.1",
            "redis>=4.0.2",
            "pika>=1.2.0",
            "graphql-core>=3.2.0",
            "schedule>=1.1.0",
        ],
        "dev": [
            "pytest>=6.2.5",
            "pytest-cov>=2.12.1",
            "black>=21.8b0",
            "isort>=5.9.3",
            "flake8>=3.9.2",
            "mypy>=0.910",
        ],
    },
    entry_points={
        "console_scripts": [
            "apifunc=apifunc.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.11",

)
