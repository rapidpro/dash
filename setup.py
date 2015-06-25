from setuptools import setup, find_packages


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
            link = req.split()[-1]
            package = link.split("#")[-1].split("=")[-1].rsplit("-", 1)[0]
            links.append(link)
            packages.append(package)
        else:
            packages.append(req)
    return packages, links


install_requires, dependency_links = _read_requirements("pip-requires.txt")


setup(
    name='dash',
    version=__import__('dash').__version__,
    license='BSD',
    install_requires=install_requires,
    dependency_links=dependency_links,
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
