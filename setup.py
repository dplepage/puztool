import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="puztool",
    version="0.5",
    author="Dan Lepage",
    author_email="dplepage@gmail.com",
    description="Some puzzle tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dplepage/puztool",
    packages=setuptools.find_packages(),
    python_requires='>=3.9',
    install_requires=[
        'numpy',
        'beautifulsoup4',
        'funcy',
        'flask',
        'imageio',
        'imageio-ffmpeg',
        'z3-solver',
    ]
)
