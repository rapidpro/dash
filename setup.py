from setuptools import setup, find_packages


try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst', 'md')
except ImportError:
    print("Warning: pypandoc module not found, could not convert Markdown to RST")
    long_description = open('README.md', 'r').read()


def _is_requirement(line):
    """Returns whether the line is a valid package requirement."""
    line = line.strip()
    return line and not (line.startswith("-r") or line.startswith("#"))


def _read_requirements(filename):
    """Returns a list of package requirements read from the file."""
    requirements_file = open(filename).read()
    return [line.strip() for line in requirements_file.splitlines() if _is_requirement(line)]


base_packages = _read_requirements("requirements/base.txt")
test_packages = _read_requirements("requirements/tests.txt")

setup(
    name='rapidpro-dash',
    version=__import__('dash').__version__,
    description="Support library for RapidPro dashboards",
    long_description=long_description,

    keywords="rapidpro dashboard",
    url='https://github.com/rapidpro/dash',
    license='BSD',

    author='Nyaruka Team',
    author_email='code@nyaruka.com',

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],

    install_requires=base_packages,
    tests_require=base_packages + test_packages,
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
