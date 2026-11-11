from setuptools import find_packages, setup


setup(
    name="html-sdd-spec",
    version="0.1.0",
    description="A readable HTML spec and collaboration contract for product, engineering, and agents",
    packages=find_packages(),
    package_data={"html_sdd": ["assets/*.html"]},
    include_package_data=True,
    entry_points={"console_scripts": ["html-sdd=html_sdd.cli:main"]},
    python_requires=">=3.9",
)
