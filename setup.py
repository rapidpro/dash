from setuptools import setup, find_packages

setup(
    name = 'dash',
    version = '0.0.1',
    licence = 'BSD',
    install_requires = ['django==1.7',
                        'smartmin==1.7',
                        'coverage',
                        'django-nose',
                        'django-celery',
                        'django-compressor',
                        'celery-with-redis',
                        'Pillow',
                        'mock',
                        'requests',
                        'hamlpy',
                        'sorl-thumbnail==11.12.1b'],
    dependency_links = ['http://github.com/nyaruka/smartmin.git@to_django_1_7#egg=smartmin-dev',],
    description = "",
    long_description = open('README.rst').read(),
    author = 'Nyaruka Team',
    author_email = 'code@nyaruka.com',
    url = 'http://www.nyaruka.com/#open',
    download_url = 'http://github.com/rapidpro/dash',

    include_package_data = True,
    packages = find_packages(),
    zip_safe = False,

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