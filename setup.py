"""Gryffin: An algorithm for Bayesian optimization of categorical variables informed by expert knowledge
"""

__author__ = 'Florian Hase, Matteo Aldeghi'

import versioneer
import glob
import os
import sys
from setuptools import setup, find_packages
from setuptools import Extension, Command
from setuptools.command.build_ext import build_ext


# readme file
def readme():
    with open('README.md') as f:
        return f.read()

# Cython compilation code copied from https://github.com/OpenPTV/openptv
class PrepareCommand(Command):
    # We must make some preparations before we can build the extension.
    # We convert the pyx files to c files, so the package can be installed from source without requiring Cython
    description = "Convert pyx files to C before building"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        self.convert_to_c()

    def convert_to_c(self):
        print('Converting pyx files to C sources...')
        pyx_files = glob.glob('./src/gryffin/bayesian_network/*.pyx')
        for pyx in pyx_files:
            self.cython(pyx)

    def cython(self, pyx):
        from Cython.Compiler.CmdLine import parse_command_line
        from Cython.Compiler.Main import compile
        options, sources = parse_command_line(['-2', pyx])
        result = compile(sources, options)
        if result.num_errors > 0:
            print('Errors converting %s to C' % pyx, file=sys.stderr)
            raise Exception('Errors converting %s to C' % pyx)
        self.announce('Converted %s to C' % pyx)


class BuildExt(build_ext, object):
    def run(self):
        if not glob.glob('./src/gryffin/bayesian_network/*.c'):
            print('You must run setup.py prepare before building the extension', file=sys.stderr)
            raise Exception('You must run setup.py prepare before building the extension')
        self.add_include_dirs()
        super(BuildExt, self).run()

        # We inherited from object to make super() work, see here: https://stackoverflow.com/a/18392639/871910

    @staticmethod
    def get_numpy_include_dir():
        # Get the numpy include directory, adapted from the following  RLs:
        # https://www.programcreek.com/python/example/60953/__builtin__.__NUMPY_SETUP__
        # https://github.com/astropy/astropy-helpers/blob/master/astropy_helpers/utils.py
        import builtins
        if hasattr(builtins, '__NUMPY_SETUP__'):
            del builtins.__NUMPY_SETUP__
        import importlib
        import numpy
        importlib.reload(numpy)

        try:
            return numpy.get_include()
        except AttributeError:
            return numpy.get_include_dir()

    def add_include_dirs(self):
        # All the Extension objects do not have their include_dir specified, we add it here as it requires
        # importing numpy, which we do not want to do unless build_ext is really running.
        # This allows pip to install numpy as it processes dependencies before building extensions
        np_include_dir = BuildExt.get_numpy_include_dir()
        include_dirs = [np_include_dir, '.', './src/gryffin/bayesian_network/']

        for extension in self.extensions:  # We dug into setuptools and distutils to find the properties to change
            extension.include_dirs = include_dirs


# ----------
# Extensions
# ----------
def mk_ext(name, files):
    # Do not specify include dirs, as they require numpy to be installed. Add them in BuildExt
    return Extension(name, files)


ext_modules = [
    mk_ext('gryffin.bayesian_network.kernel_evaluations', ['src/gryffin/bayesian_network/kernel_evaluations.c']),
    mk_ext('gryffin.bayesian_network.kernel_prob_reshaping', ['src/gryffin/bayesian_network/kernel_prob_reshaping.c'])]

# -----
# cmdclass - get versioneer one and add building hooks
# -----
cmdclass = versioneer.get_cmdclass()

cmdclass['build_ext'] = BuildExt
cmdclass['prepare'] = PrepareCommand

# -----
# Setup
# -----
setup(name='gryffin',
      version=versioneer.get_version(),
      cmdclass=cmdclass,
      description='Bayesian optimization for continuous and categorical variables',
      long_description=readme(),
      long_description_content_type='text/markdown',
      classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering',
      ],
      url='https://github.com/aspuru-guzik-group/gryffin',
      author='Florian Hase, Matteo Aldeghi',
      author_email='matteo.aldeghi@vectorinstitute.ai',
      license='Apache License 2.0',
      packages=find_packages('./src'),
      package_dir={'': 'src'},
      zip_safe=False,
      tests_require=['pytest'],
      install_requires=['numpy', 'sqlalchemy', 'rich', 'pandas', 'matter-chimera', 'deap', 'torch', 'torchbnn'],
      python_requires=">=3.7",
      ext_modules=ext_modules,
      entry_points={"console_scripts": ["gryffin = gryffin.cli:entry_point"]}
      )
