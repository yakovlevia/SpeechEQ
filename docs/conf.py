import os
import sys
sys.path.insert(0, os.path.abspath('../src'))

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx_autodoc_typehints'
]

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
html_theme = 'alabaster'