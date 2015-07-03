from setuptools import setup, find_packages

setup(
    name="AmazonAPIWrapper",
    version="0.0.1",
    description="Amazon API Wrapper",
    url="https://github.com/lv10/amazonapi",
    author="lv10",
    author_email="luis@lv10.me",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 2.7"
    ],
    packages=find_packages(exclude=["tests"]),
    install_requires=[
        "beautifulsoup4==4.4.0",
        "argparse==1.2.1",
        "requests==2.7.0",
        "wsgiref==0.1.2",
        "lxml==3.4.4",
    ],
)
