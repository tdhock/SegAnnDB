import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.org')).read()
CHANGES = open(os.path.join(here, 'NEWS_TODO.org')).read()

requires = [
    'pyramid',
    'seganndb_login',
    #'pyramid_debugtoolbar',
    'pyramid_chameleon',
    #'waitress',
    ]

setup(name='plotter',
      version='2015.11.19',
      description='plotter',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web pyramid pylons',
      packages=find_packages(),
      include_package_data=True,
      package_data={
          "templates":["*"],
          "static":["*"],
      },
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="plotter",
      entry_points="""\
      [paste.app_factory]
      main = plotter:main
      """,
      )
