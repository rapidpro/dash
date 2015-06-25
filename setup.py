from setuptools import setup, find_packages


setup(
    name='dash',
    version=__import__('dash').__version__,
    license='BSD',
    install_requires=['django==1.7.2',
                      'smartmin',
                      'coverage',
                      'django-nose',
                      'django-celery',
                      'django-compressor',
                      'celery-with-redis',
                      'Pillow',
                      'mock',
                      'requests',
                      'hamlpy',
                      'sorl-thumbnail==12.1c',
                      'django-timezones',
                      'phonenumbers',
                      'django-redis',
                      'rapidpro-python',
                      'enum34',
                      'python-dateutil'],
    dependency_links=['https://github.com/nyaruka/smartmin.git#egg=smartmin-dev',
                      'https://github.com/rapidpro/rapidpro-python#egg=rapidpro-python'],
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
