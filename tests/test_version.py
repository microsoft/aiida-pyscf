# -*- coding: utf-8 -*-
"""Tests for the :mod:`aiida_pyscf` module."""
from packaging.version import Version, parse

import aiida_pyscf


def test_version():
    """Test that :attr:`aiida_pyscf.__version__` is a PEP-440 compatible version identifier."""
    assert hasattr(aiida_pyscf, '__version__')
    assert isinstance(aiida_pyscf.__version__, str)
    assert isinstance(parse(aiida_pyscf.__version__), Version)
