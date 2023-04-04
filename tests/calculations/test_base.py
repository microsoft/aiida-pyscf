# -*- coding: utf-8 -*-
"""Tests for the :mod:`aiida_pyscf.calculations.base` module."""
# pylint: disable=redefined-outer-name
import textwrap

from aiida.manage.tests.pytest_fixtures import recursive_merge
from aiida.orm import Dict
from jinja2 import BaseLoader, Environment
import pytest

from aiida_pyscf.calculations.base import PyscfCalculation


@pytest.fixture
def generate_inputs_pyscf(aiida_local_code_factory, generate_structure):
    """Return a dictionary of inputs for the ``PyscfCalculation`."""

    def factory(**kwargs):
        parameters = {'mean_field': {'method': 'RHF'}}
        recursive_merge(parameters, kwargs.pop('parameters', {}))

        inputs = {
            'code': aiida_local_code_factory('pyscf.base', 'python'),
            'structure': generate_structure(),
            'parameters': Dict(parameters),
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


def test_parameters_structure(generate_calc_job, generate_inputs_pyscf, file_regression):
    """Test the ``structure`` key of the ``parameters`` input."""
    parameters = {
        'structure': {
            'basis': {
                'O': 'sto-3g',
                'H': 'cc-pvdz'
            },
            'cart': True,
            'charge': 1,
            'spin': 2,
        },
    }
    inputs = generate_inputs_pyscf(parameters=parameters)
    tmp_path, _ = generate_calc_job(PyscfCalculation, inputs=inputs)

    content_input_file = (tmp_path / PyscfCalculation.FILENAME_SCRIPT).read_text()
    file_regression.check(content_input_file, encoding='utf-8', extension='.pyr')


def test_parameters_mean_field(generate_calc_job, generate_inputs_pyscf, file_regression):
    """Test the ``mean_field`` key of the ``parameters`` input."""
    parameters = {
        'mean_field': {
            'diis_start_cycle': 2,
            'method': 'RHF',
            'grids': {
                'level': 3
            },
            'xc': 'PBE',
        },
    }
    inputs = generate_inputs_pyscf(parameters=parameters)
    tmp_path, _ = generate_calc_job(PyscfCalculation, inputs=inputs)

    content_input_file = (tmp_path / PyscfCalculation.FILENAME_SCRIPT).read_text()
    file_regression.check(content_input_file, encoding='utf-8', extension='.pyr')


def test_parameters_optimizer(generate_calc_job, generate_inputs_pyscf, file_regression):
    """Test the ``optimizer`` key of the ``parameters`` input."""
    parameters = {
        'optimizer': {
            'solver': 'geomeTRIC',
            'convergence_parameters': {
                'convergence_energy': 2.0,
                'string': 'value',
            },
        },
    }
    inputs = generate_inputs_pyscf(parameters=parameters)
    tmp_path, _ = generate_calc_job(PyscfCalculation, inputs=inputs)

    content_input_file = (tmp_path / PyscfCalculation.FILENAME_SCRIPT).read_text()
    file_regression.check(content_input_file, encoding='utf-8', extension='.pyr')


def test_parameters_cubegen(generate_calc_job, generate_inputs_pyscf, file_regression):
    """Test the ``cubegen`` key of the ``parameters`` input."""
    parameters = {
        'cubegen': {
            'indices': [5, 6],
            'parameters': {
                'nx': 40,
                'ny': 40,
                'nz': 40,
                'margin': 3.0,
            }
        },
    }
    inputs = generate_inputs_pyscf(parameters=parameters)
    tmp_path, _ = generate_calc_job(PyscfCalculation, inputs=inputs)

    content_input_file = (tmp_path / PyscfCalculation.FILENAME_SCRIPT).read_text()
    file_regression.check(content_input_file, encoding='utf-8', extension='.pyr')


def test_parameters_fcidump(generate_calc_job, generate_inputs_pyscf, file_regression):
    """Test the ``fcidump`` key of the ``parameters`` input."""
    parameters = {
        'fcidump': {
            'active_spaces': [[5, 6], [5, 7]],
            'occupations': [[1, 1], [1, 1]],
        },
    }
    inputs = generate_inputs_pyscf(parameters=parameters)
    tmp_path, _ = generate_calc_job(PyscfCalculation, inputs=inputs)

    content_input_file = (tmp_path / PyscfCalculation.FILENAME_SCRIPT).read_text()
    file_regression.check(content_input_file, encoding='utf-8', extension='.pyr')


def test_invalid_parameters_mean_field_method(generate_calc_job, generate_inputs_pyscf):
    """Test validation of ``parameters.mean_field.method``."""
    parameters = {'mean_field': {'method': 'invalid'}}
    inputs = generate_inputs_pyscf(parameters=parameters)

    with pytest.raises(ValueError, match=r'Specified mean field method invalid is not supported'):
        generate_calc_job(PyscfCalculation, inputs=inputs)


@pytest.mark.parametrize(
    'parameters, expected', (
        ({}, r'No solver specified in `optimizer` parameters'),
        ({
            'solver': 'solve-this'
        }, r'Invalid solver `solve-this` specified in `optimizer` parameters'),
    )
)
def test_invalid_parameters_optimizer(generate_calc_job, generate_inputs_pyscf, parameters, expected):
    """Test validation of ``parameters.optimizer``."""
    with pytest.raises(ValueError, match=expected):
        generate_calc_job(PyscfCalculation, inputs=generate_inputs_pyscf(parameters=Dict({'optimizer': parameters})))


@pytest.mark.parametrize(
    'parameters, expected', (
        ({}, 'If the `cubegen` key is specified, the `indices` key has to be defined with a list of indices.'),
        ({
            'indices': 1
        }, r'The `cubegen.indices` parameter should be a list of integers, but got:.*'),
    )
)
def test_invalid_parameters_cubegen(generate_calc_job, generate_inputs_pyscf, parameters, expected):
    """Test validation of ``parameters.cubegen``."""
    with pytest.raises(ValueError, match=expected):
        generate_calc_job(PyscfCalculation, inputs=generate_inputs_pyscf(parameters=Dict({'cubegen': parameters})))


@pytest.mark.parametrize(
    'parameters, expected', (
        ({}, r'The `fcipdump.active_spaces` should be a nested list of integers.*'),
        ({
            'active_spaces': True
        }, r'The `fcipdump.*` should be a nested list of integers.*'),
        ({
            'active_spaces': [True]
        }, r'The `fcipdump.*` should be a nested list of integers.*'),
        ({
            'active_spaces': [[True]]
        }, r'The `fcipdump.*` should be a nested list of integers.*'),
        ({
            'active_spaces': [[1]],
            'occupations': [[1, 2]]
        }, r'The `.*` and `.*` arrays have different shapes\.'),
    )
)
def test_invalid_parameters_fcidump(generate_calc_job, generate_inputs_pyscf, parameters, expected):
    """Test validation of ``parameters.fcidump``."""
    with pytest.raises(ValueError, match=expected):
        generate_calc_job(PyscfCalculation, inputs=generate_inputs_pyscf(parameters=Dict({'fcidump': parameters})))


def test_filter_render_python(file_regression):
    """Test the :meth:`aiida_pyscf.calculations.base.PyscfCalculation.filter_render_value` method."""
    parameters = {
        'bool': True,
        'float': 1.0,
        'integer': 1,
        'string': 'string',
        'dictionary': {
            'a': 1,
            'b': 1.0,
            'c': 'str'
        },
    }

    template = textwrap.dedent(
        """
        {% for key, value in parameters.items() -%}
        obj.{{ key }} = {{ value|render_python }}
        {% endfor -%}"""
    )

    environment = Environment(loader=BaseLoader)
    environment.filters['render_python'] = PyscfCalculation.filter_render_python
    rendered = environment.from_string(template).render(parameters=parameters)
    file_regression.check(rendered, encoding='utf-8', extension='.pyr')
