# -*- coding: utf-8 -*-
"""Tests for the :mod:`aiida_pyscf.calculations.base` module."""
# pylint: disable=redefined-outer-name
from aiida.orm import Dict
import pytest

from aiida_pyscf.calculations.base import PyscfCalculation


@pytest.fixture
def generate_inputs_pyscf(aiida_local_code_factory, generate_structure):
    """Return a dictionary of inputs for the ``PyscfCalculation`."""

    def factory(**kwargs):
        inputs = {
            'code': aiida_local_code_factory('pyscf.base', 'python'),
            'structure': generate_structure(),
            'metadata': {
                'options': {
                    'resources': {
                        'num_machines': 1
                    }
                }
            },
        }
        inputs.update(**kwargs)
        return inputs

    return factory


def test_default(generate_calc_job, generate_inputs_pyscf, file_regression):
    """Test the plugin for default inputs."""
    inputs = generate_inputs_pyscf()
    tmp_path, calc_info = generate_calc_job(PyscfCalculation, inputs=inputs)

    assert sorted(calc_info.retrieve_list) == sorted([
        PyscfCalculation.FILENAME_RESULTS,
        PyscfCalculation.FILENAME_STDERR,
        PyscfCalculation.FILENAME_STDOUT,
    ])

    content_input_file = (tmp_path / PyscfCalculation.FILENAME_SCRIPT).read_text()
    file_regression.check(content_input_file, encoding='utf-8', extension='.pyr')


def test_parameters_optimizer(generate_calc_job, generate_inputs_pyscf, file_regression):
    """Test the ``structure`` key of the ``parameters`` input."""
    parameters = {
        'optimizer': {
            'solver': 'geomeTRIC',
            'convergence_parameters': {
                'convergence_energy': 2.0
            },
        },
    }
    inputs = generate_inputs_pyscf(parameters=Dict(parameters))
    tmp_path, _ = generate_calc_job(PyscfCalculation, inputs=inputs)

    content_input_file = (tmp_path / PyscfCalculation.FILENAME_SCRIPT).read_text()
    file_regression.check(content_input_file, encoding='utf-8', extension='.pyr')


def test_invalid_parameters_mean_field_method(generate_calc_job, generate_inputs_pyscf):
    """Test validation of ``parameters.mean_field.method``."""
    parameters = {'mean_field': {'method': 'invalid'}}
    inputs = generate_inputs_pyscf(parameters=Dict(parameters))

    with pytest.raises(ValueError, match=r'specified mean field method invalid is not supported'):
        generate_calc_job(PyscfCalculation, inputs=inputs)
