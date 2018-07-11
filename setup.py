import io

from setuptools import setup, find_packages


def get_long_description():
    with io.open('README.md', encoding='utf-8') as f:
        return f.read()


requirements = [
    # Project settings requirements
    'Django~=1.11',
    'django-environ>=0.4.3',
    'colorlog',

    # Django applications
    'djangorestframework',
    'django-dramatiq',
    'django-fsm',
    'django-model-utils',

    # Additional dependencies
    'beautifulsoup4',
    'dramatiq>=1.2.0',
    'elasticsearch>=6',
    'elasticsearch-dsl>=6',
    'jsonfield2',
    'nltk',
    'progressbar2',
    'redis',
    'scrapy',
    'shortuuid',
    'terminaltables',
]


setup(
    name='yurika',
    version='0.0.0',
    author='ITNG',
    url='https://github.com/ITNG/yurika',
    description='Unstructured Text Analytics Platform',
    long_description=get_long_description(),
    license='BSD',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    include_package_data=True,
    install_requires=requirements,
    extras_require={
        'sentry': ['raven'],
        'dev': ['tox', 'tox-venv', 'pip-tools'],
    },
    entry_points={
        'console_scripts': [
            'yurika = yurika.__main__:main',
            'yurika-setup = yurika.__main__:init',
        ],
    },
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Framework :: Django',
        'Framework :: Django :: 1.11',
        'Framework :: Scrapy',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
)
