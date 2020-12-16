from setuptools import setup, find_packages

setup(
    name="spycery",
    description="python package providing useful modules and extensions for python development",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    version="v0.0.4",
    url="https://github.com/steinbergs-python-packages/spycery",
    author="Stephan Steinberg",
    author_email="st.steinberg@t-online.de",
    license="MIT",
    packages=find_packages(),
    platforms="any",
    python_requires=">=3.6",
    install_requires=["astor", "graphviz", "matplotlib", "numpy", "pandas", "psutil", "requests_toolbelt", "requests", "websocket-client"],
    keywords="python development tools modules extensions",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
        "Topic :: Utilities",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ]
)
