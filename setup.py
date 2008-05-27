import numpy.distutils.core as core

# Configure our C modules that are built with f2py.
tridiag = core.Extension(name = 'dadi.tridiag',
                         sources = ['dadi/tridiag.pyf', 'dadi/tridiag.c'])
int_c = core.Extension(name = 'dadi.integration_c',
                       sources = ['dadi/integration_c.pyf', 
                                  'dadi/integration1D.c',
                                  'dadi/integration2D.c', 
                                  'dadi/integration3D.c',
                                  'dadi/integration_shared.c',
                                  'dadi/tridiag.c'])

core.setup(name='dadi',
           version='devel',
           author='Ryan Gutenkunst',
           author_email='rng7@cornell.edu',
           packages=['dadi'], 
           scripts=['scripts/ms_jsfs'],
           ext_modules = [tridiag, int_c]
           )
