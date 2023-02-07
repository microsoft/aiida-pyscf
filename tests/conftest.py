# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name
"""Module with test fixtures."""
from aiida.common.folders import Folder
from aiida.engine.utils import instantiate_process
from aiida.manage.manager import get_manager
from aiida.orm import StructureData
from ase.build import molecule
import pytest

pytest_plugins = ['aiida.manage.tests.pytest_fixtures']  # pylint: disable=invalid-name


@pytest.fixture
def generate_calc_job(tmp_path):
    """Return a factory to generate a :class:`aiida.engine.CalcJob` instance with the given inputs.

    The fixture will call ``prepare_for_submission`` and return a tuple of the temporary folder that was passed to it,
    as well as the ``CalcInfo`` instance that it returned.
    """

    def factory(process_class, inputs=None, return_process=False):
        """Create a :class:`aiida.engine.CalcJob` instance with the given inputs."""
        manager = get_manager()
        runner = manager.get_runner()
        process = instantiate_process(runner, process_class, **inputs or {})
        calc_info = process.prepare_for_submission(Folder(tmp_path))

        if return_process:
            return process

        return tmp_path, calc_info

    return factory


@pytest.fixture
def generate_structure():
    """Return factory to generate a ``StructureData`` instance."""

    def factory() -> StructureData:
        """Generate a ``StructureData`` instance."""
        atoms = molecule('H2O')
        return StructureData(ase=atoms)

    return factory
