import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="bi_db",
    version="1.3.2",
    author="BI Data Engineering",
    author_email="jun.kim@pitchbook.com",
    description="Database connector module designed to make database engineering operations easier for PitchBook Business Intelligence",
    url="https://git.pitchbookdata.com/business-intelligence/bi_db",
    packages=setuptools.find_packages(),
    install_requires=['snowflake.sqlalchemy', 'bi_tools', 'bi_s3',
        'simple_salesforce', 'salesforce_bulk', 'pandas'],
    classifiers=(
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 3',
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)
