# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name
"""Module with test fixtures."""
from __future__ import annotations

import collections
import pathlib

from aiida.common.folders import Folder
from aiida.common.links import LinkType
from aiida.engine.utils import instantiate_process
from aiida.manage.manager import get_manager
from aiida.orm import CalcJobNode, Dict, FolderData, StructureData
from aiida.plugins import ParserFactory, WorkflowFactory
from ase.build import molecule
from plumpy import ProcessState
import pytest

pytest_plugins = ['aiida.manage.tests.pytest_fixtures']  # pylint: disable=invalid-name


@pytest.fixture
def filepath_tests() -> pathlib.Path:
    """Return the path to the tests folder."""
    return pathlib.Path(__file__).resolve().parent


@pytest.fixture
def generate_workchain():
    """Return a factory to generate a :class:`aiida.engine.WorkChain` instance with the given inputs."""

    def factory(entry_point, inputs):
        """Generate a :class:`aiida.engine.WorkChain` instance with the given inputs.

        :param entry_point: entry point name of the work chain subclass.
        :param inputs: inputs to be passed to process construction.
        :return: a ``WorkChain`` instance.
        """
        process_class = WorkflowFactory(entry_point)
        runner = get_manager().get_runner()
        process = instantiate_process(runner, process_class, **inputs)

        return process

    return factory


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
def generate_calc_job_node(filepath_tests, aiida_computer_local):
    """Create and return a :class:`aiida.orm.CalcJobNode` instance."""

    def flatten_inputs(inputs, prefix=''):
        """Flatten inputs recursively like :meth:`aiida.engine.processes.process::Process._flatten_inputs`."""
        flat_inputs = []
        for key, value in inputs.items():
            if isinstance(value, collections.abc.Mapping):
                flat_inputs.extend(flatten_inputs(value, prefix=prefix + key + '__'))
            else:
                flat_inputs.append((prefix + key, value))
        return flat_inputs

    def factory(entry_point: str, test_name: str | None = None, inputs: dict = None):
        """Create and return a :class:`aiida.orm.CalcJobNode` instance."""
        node = CalcJobNode(computer=aiida_computer_local(), process_type=f'aiida.calculations:{entry_point}')

        if inputs:
            for link_label, input_node in flatten_inputs(inputs):
                input_node.store()
                node.base.links.add_incoming(input_node, link_type=LinkType.INPUT_CALC, link_label=link_label)

        node.store()

        if test_name:
            filepath_retrieved = filepath_tests / 'parsers' / 'fixtures' / entry_point.split('.')[-1] / test_name

            retrieved = FolderData()
            retrieved.base.repository.put_object_from_tree(filepath_retrieved)
            retrieved.base.links.add_incoming(node, link_type=LinkType.CREATE, link_label='retrieved')
            retrieved.store()

        return node

    return factory


@pytest.fixture(scope='session')
def generate_parser():
    """Fixture to load a parser class for testing parsers."""

    def factory(entry_point_name):
        """Fixture to load a parser class for testing parsers.

        :param entry_point_name: entry point name of the parser class
        :return: the `Parser` sub class
        """
        return ParserFactory(entry_point_name)

    return factory


@pytest.fixture
def generate_structure():
    """Return factory to generate a ``StructureData`` instance."""

    def factory(formula: str = 'H2O') -> StructureData:
        """Generate a ``StructureData`` instance."""
        atoms = molecule(formula)
        return StructureData(ase=atoms)

    return factory


@pytest.fixture
def generate_workchain_pyscf_base(generate_workchain, generate_inputs_pyscf, generate_calc_job_node):
    """Return a factory to generate a :class:`aiida_pyscf.workflows.base.PyscfBaseWorkChain` instance."""

    def factory(inputs=None, exit_code=None):
        """Generate a :class:`aiida_pyscf.workflows.base.PyscfBaseWorkChain` instance.``.

        :param inputs: inputs for the ``PyscfBaseWorkChain``.
        :param exit_code: exit code for the ``PyscfCalculation``.
        """
        process = generate_workchain('pyscf.base', {'pyscf': inputs or generate_inputs_pyscf()})
        node = generate_calc_job_node('pyscf.base', inputs={'parameters': Dict()})
        process.ctx.iteration = 1
        process.ctx.children = [node]

        if exit_code is not None:
            node.set_process_state(ProcessState.FINISHED)
            node.set_exit_status(exit_code.status)

        return process

    return factory


@pytest.fixture
def generate_inputs_pyscf(aiida_local_code_factory, generate_structure):
    """Return a factory to generate a :class:`aiida_pyscf.calculations.base.PyscfCalculation` instance."""

    def factory(inputs=None):
        """Generate a :class:`aiida_pyscf.calculations.base.PyscfCalculation` instance."""
        base_inputs = {
            'code': aiida_local_code_factory('pyscf.base', 'python'),
            'structure': generate_structure(),
        }

        if inputs:
            base_inputs.update(**inputs)

        return base_inputs

    return factory
