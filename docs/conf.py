# Sphinx configuration file

import os
import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
# src/ находится уровнем выше docs/
sys.path.insert(0, os.path.abspath('../src'))

# ---------------------------------------------------------------------------
# Mock тяжёлых и GUI-зависимостей (не нужны для генерации docs)
# ---------------------------------------------------------------------------
class Mock(MagicMock):
    @classmethod
    def __getattr__(cls, name):
        return MagicMock()

MOCK_MODULES = [
    # GUI
    'PySide6', 'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
    'PySide6.QtMultimedia', 'PySide6.QtNetwork', 'PySide6.QtOpenGL',
    # ML / DL
    'torch', 'torch.nn', 'torch.nn.functional', 'torch.optim',
    'torch.utils', 'torch.utils.data',
    'torchaudio', 'torchaudio.transforms', 'torchaudio.functional',
    # Audio
    'soundfile', 'librosa', 'librosa.core', 'librosa.feature',
    'pyaudio', 'sounddevice',
    # Scientific
    'numpy', 'numpy.typing',
    'scipy', 'scipy.signal', 'scipy.fft', 'scipy.io',
    # gRPC / Protobuf
    'grpc', 'grpc.aio',
    'google', 'google.protobuf', 'google.protobuf.descriptor',
]

sys.modules.update({mod: Mock() for mod in MOCK_MODULES})

# ---------------------------------------------------------------------------
# Project information
# ---------------------------------------------------------------------------
project   = 'SpeechEQ'
copyright = '2026, Ivan Yakovlev'
author    = 'Ivan Yakovlev'
release   = '1.0.0'

# ---------------------------------------------------------------------------
# Extensions
# ---------------------------------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',           # Документирование из docstrings
    'sphinx.ext.autosummary',       # Сводные таблицы API
    'sphinx.ext.napoleon',          # Google / NumPy docstrings
    'sphinx.ext.viewcode',          # Ссылки «View source»
    'sphinx.ext.intersphinx',       # Кросс-ссылки на внешние docs
    'sphinx_autodoc_typehints',     # Типы из аннотаций Python
]

templates_path   = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
language         = 'ru'

# ---------------------------------------------------------------------------
# Autodoc
# ---------------------------------------------------------------------------
autodoc_default_options = {
    'members':          True,           # Все публичные члены
    'undoc-members':    True,           # Даже без docstring
    'show-inheritance': True,           # Родительские классы
    'private-members':  False,          # Пропускать _private
    'special-members':  '__init__',     # Но __init__ включаем
}

autodoc_member_order     = 'bysource'   # Порядок — как в исходнике
autodoc_typehints        = 'description'# Типы в описании, не в сигнатуре
autodoc_inherit_docstrings = True

# ---------------------------------------------------------------------------
# Napoleon
# ---------------------------------------------------------------------------
napoleon_google_docstring       = True
napoleon_numpy_docstring        = True
napoleon_include_init_with_doc  = True
napoleon_attr_annotations       = True

# ---------------------------------------------------------------------------
# sphinx-autodoc-typehints
# ---------------------------------------------------------------------------
always_document_param_types = True
typehints_fully_qualified   = False

# ---------------------------------------------------------------------------
# Intersphinx
# ---------------------------------------------------------------------------
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy':  ('https://numpy.org/doc/stable/', None),
}

# ---------------------------------------------------------------------------
# HTML / RTD Theme
# ---------------------------------------------------------------------------
html_theme       = 'sphinx_rtd_theme'
html_static_path = ['_static']

html_theme_options = {
    'navigation_depth':    6,      # Глубина вложенности в боковом меню
    'collapse_navigation': False,  # Не сворачивать дерево навигации
    'titles_only':         False,  # Показывать все заголовки, не только разделы
    'includehidden':       True,
    'display_version':     True,
}
