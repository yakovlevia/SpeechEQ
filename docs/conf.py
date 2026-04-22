import os
import sys

sys.path.insert(0, os.path.abspath('../src'))

project = 'SpeechEQ'
copyright = '2026, Ivan Yakovlev'
author = 'Ivan Yakovlev'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx_autodoc_typehints',
]

# Моки для тяжёлых / графических библиотек, которые не нужны при сборке документации
autodoc_mock_imports = [
    # ML и DSP (тяжелые)
    'torch',
    'torchaudio',
    'speechbrain',
    'einops',
    'rotary_embedding_torch',
    'pyloudnorm',
    'noisereduce',

    # PySide6 (Qt)
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtWidgets',
    'PySide6.QtGui',
    'PySide6.QtUiTools',
    'PySide6.QtMultimedia',
    'PySide6.QtMultimediaWidgets',
    'shiboken6',
]

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
}