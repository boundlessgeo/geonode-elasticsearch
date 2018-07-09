from setuptools import setup, find_packages

try:
    LONG_DESCRIPTION = open('README.md', 'r').read()
except IOError:
    LONG_DESCRIPTION = "Elasticsearch app for indexing GeoNode models via elasticsearch-dsl"

setup(
    name="geonode-elasticsearch-app",
    version="0.2.3",
    author="tbrundage",
    author_email="tbrundage@boundlessgeo.com",
    description="Elasticsearch app for indexing GeoNode models via elasticsearch-dsl",
    long_description=LONG_DESCRIPTION,
    license="GPLv2",
    url="https://github.com/boundlessgeo/geonode-elasticsearch",
    packages=find_packages(),
    classifiers=[
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Framework :: Django",
    ],
    install_requires=[
        "elasticsearch-dsl>=6.0.0,<6.2.0",
        "ipaddress>=1.0.0,<2.0.0"  # missing from elasticsearch-dsl 6.0.0
    ]
)
