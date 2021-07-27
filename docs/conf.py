# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

project = 'GloMPO'
copyright = '2021, Michael Freitas Gustavo'
author = 'Michael Freitas Gustavo'

# The full version, including alpha/beta/rc tags
release = 'v3.0.2'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.napoleon',
              'sphinx.ext.autosummary',
              'sphinx.ext.viewcode',
              'sphinx.ext.coverage',
              'sphinx.ext.intersphinx',
              'sphinx_rtd_theme',
              'sphinx.ext.autosectionlabel',
              ]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Other Sphinx settings -----------------------------------------------------
modindex_common_prefix = ['glompo.']
master_doc = 'index'
needs_sphinx = '1.8.5'
nitpicky = True
nitpick_ignore = [('py:class', 'List'),
                  ('py:class', 'Dict'),
                  ('py:class', 'Set'),
                  ('py:class', 'Sequence'),
                  ('py:class', 'Tuple'),
                  ('py:class', 'Any'),
                  ('py:class', 'Callable'),
                  ('py:class', 'Type'),
                  ('py:class', 'Union'),
                  ]

# Autodoc settings ----------------------------------------------------------
autodoc_mock_imports = ['matplotlib',
                        'ffmpeg',
                        'PySide2',
                        'scipy',
                        'pytest',
                        'cma',
                        'optsam',
                        'nevergrad',
                        'scm',
                        'dill',
                        'psutil',
                        ]

autodoc_typehints = 'both'
autoclass_content = 'class'

# Napoleon settings ----------------------------------------------------------
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_notes = True

# Autosummary settings -------------------------------------------------------
autosummary_generate = False
autosummary_generate_overwrite = True
autosummary_generate_autosummary_docs = True

# Intersphinx settings -------------------------------------------------------
intersphinx_mapping = {
    'python': ('https://docs.python.org/3.6', None),
    'tables': ('https://www.pytables.org', None),
    'dill': ('https://dill.readthedocs.io/en/latest/', None),
    'psutil': ('https://psutil.readthedocs.io/en/latest/', None),
    'matplotlib': ('http://matplotlib.sourceforge.net/', None),
    'numpy': ('http://docs.scipy.org/doc/numpy/', None),
}
