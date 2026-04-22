# Configuration file for the Sphinx documentation builder.
# Generated for SpeechEQ project

import os
import sys
from pathlib import Path

docs_dir = Path(__file__).parent.resolve()
project_root = docs_dir.parent
sys.path.insert(0, str(project_root))

# -- Project information -----------------------------------------------------
project = 'SpeechEQ'
copyright = '2026, Ivan Yakovlev'
author = 'Ivan Yakovlev'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx_autodoc_typehints',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
]

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Autodoc settings --------------------------------------------------------
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
    'member-order': 'bysource',
}
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'
autodoc_typehints_description_target = 'documented'

# Mock imports for heavy/optional dependencies
autodoc_mock_imports = [
    'torch', 'torchaudio', 'speechbrain', 'einops',
    'rotary_embedding_torch', 'pyloudnorm', 'noisereduce',
    'PySide6', 'PySide6.QtCore', 'PySide6.QtWidgets',
    'PySide6.QtGui', 'PySide6.QtUiTools', 'PySide6.QtMultimedia',
    'PySide6.QtMultimediaWidgets', 'shiboken6',
]

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_title = 'SpeechEQ Documentation'
html_short_title = 'SpeechEQ'
html_logo = None  # Path to logo if you have one
html_favicon = None  # Path to favicon if you have one

html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'titles_only': False,
    'includehidden': True,
}

# Show full module paths in headings
add_module_names = True

# Sidebar configuration for better navigation
html_sidebars = {
    '**': [
        'globaltoc.html',
        'relations.html',
        'sourcelink.html',
        'searchbox.html',
    ]
}

# -- Internationalization ----------------------------------------------------
language = 'ru'
locale_dirs = ['locale/']
gettext_compact = False

# -- Intersphinx mapping (optional) ------------------------------------------
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'torch': ('https://pytorch.org/docs/stable', None),
}