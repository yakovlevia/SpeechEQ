import os
import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.abspath('..'))

# ---------------------------------------------------------------------------
# Mock
# ---------------------------------------------------------------------------
class _AutoMock(MagicMock):
    @classmethod
    def __getattr__(cls, name):
        return MagicMock()


class _AutoMockFinder:
    _MOCK_PREFIXES = (
        # ML / DL
        'torch',
        'torchaudio',
        'speechbrain',
        'einops',           # ← NEW: установлен в venv, проверяет torch.__version__
        # Audio
        'soundfile',
        'librosa',
        'pyaudio',
        'sounddevice',
        # Scientific
        'numpy',
        'scipy',
        # gRPC
        'grpc',
        'google.protobuf',  # namespace-пакет, не трогаем весь 'google'
        # GUI
        'PySide6',
        # Protobuf generated — устаревший файл, несовместимые версии
        'src.proto',
    )

    def find_module(self, fullname, path=None):
        if any(
            fullname == p or fullname.startswith(p + '.')
            for p in self._MOCK_PREFIXES
        ):
            return self
        return None

    def load_module(self, fullname):
        if fullname in sys.modules:
            return sys.modules[fullname]

        mock = _AutoMock()
        mock.__name__    = fullname
        mock.__loader__  = self
        mock.__spec__    = None
        mock.__path__    = []
        mock.__package__ = fullname.rpartition('.')[0]
        mock.__all__     = []  # ← NEW: fix "__all__ should be a list of strings"

        sys.modules[fullname] = mock

        # Прикрепляем к родителю — иначе "module 'src' has no attribute 'proto'"
        parent, _, child = fullname.rpartition('.')
        if parent and parent in sys.modules:
            try:
                setattr(sys.modules[parent], child, mock)
            except (AttributeError, TypeError):
                pass

        return mock


sys.meta_path.insert(0, _AutoMockFinder())

# ---------------------------------------------------------------------------
# Project information
# ---------------------------------------------------------------------------
project   = 'SpeechEQ'
copyright = '2024, Author'
author    = 'Author'
release   = '0.1.0'

# ---------------------------------------------------------------------------
# Extensions
# ---------------------------------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
]

templates_path   = ['_templates']
exclude_patterns = [
    '_build',
    'Thumbs.db',
    '.DS_Store',
    'source/modules.rst',   # ← автогенерируется apidoc, нам не нужен
]

# Подавляем предупреждения об осиротевших документах
suppress_warnings = [
    'toc.excluded',         # source/modules.rst исключён намеренно
]
language         = 'ru'

# ---------------------------------------------------------------------------
# Autodoc
# ---------------------------------------------------------------------------
autodoc_default_options = {
    'members':          True,
    'undoc-members':    True,
    'show-inheritance': True,
    'private-members':  False,
    'special-members':  '__init__',
}

autodoc_member_order       = 'bysource'
autodoc_typehints          = 'description'
autodoc_typehints_format   = 'short'
autodoc_inherit_docstrings = True

# ---------------------------------------------------------------------------
# Napoleon
# ---------------------------------------------------------------------------
napoleon_google_docstring      = True
napoleon_numpy_docstring       = True
napoleon_include_init_with_doc = True
napoleon_attr_annotations      = True

# ---------------------------------------------------------------------------
# Intersphinx
# ---------------------------------------------------------------------------
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
html_theme       = 'sphinx_rtd_theme'
html_static_path = ['_static']

html_theme_options = {
    'navigation_depth':    6,
    'collapse_navigation': False,
    'titles_only':         False,
    'includehidden':       True,
    # display_version убран — удалён в sphinx-rtd-theme >= 2.0  ← FIX
}
