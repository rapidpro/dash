import re

from setuptools import setup, find_packages


EGG_REGEX = re.compile(r".*#egg=(?P<package>.+)-(?P<version>[\d.]+)$")


def _is_requirement(line):
    """Returns whether the line is a valid package requirement."""
    line = line.strip()
    return line and not line.startswith("#")


def _read_requirements(filename):
    """Parses a file for pip installation requirements.

    Returns two lists: one with package requirements, and the other with
    dependency links.
    """
    with open(filename) as requirements_file:
        contents = requirements_file.read()
        requirements = [line.strip() for line in contents.splitlines()
                        if _is_requirement(line)]
    packages = []
    links = []
    for req in requirements:
        if req.startswith("-e "):
            # Installation requires a dependency link.
            # The dependency link package must be included in the requirements.
            link = req.split()[-1]
            m = EGG_REGEX.match(link)
            if m:
                links.append(link)
                packages.append(m.groupdict()['package'])
            else:
                raise Exception("Could not get package name from "
                                "dependency link: {}".format(link))
        else:
            packages.append(req)
    return packages, links


base_packages, base_links = _read_requirements("requirements/base.txt")
test_packages, test_links = _read_requirements("requirements/tests.txt")


setup(
    name='dash',
    version=__import__('dash').__version__,
    license='BSD',
    install_requires=base_packages,
    tests_require=base_packages + test_packages,
    dependency_links=base_links + test_links,
    description="",
    long_description=open('README.md').read(),
    author='Nyaruka Team',
    author_email='code@nyaruka.com',
    url='http://www.nyaruka.com/#open',
    download_url='http://github.com/rapidpro/dash',

    include_package_data=True,
    packages=find_packages(),
    zip_safe=False,

    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ]
)
