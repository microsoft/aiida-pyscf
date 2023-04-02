# -*- coding: utf-8 -*-
"""Module with integration tests."""
from aiida import engine, orm
import numpy


def test_pyscf_base_mean_field(aiida_local_code_factory, generate_structure, data_regression, num_regression):
    """Test running a default mean field ``PyscfCalculation`` job."""
    code = aiida_local_code_factory('pyscf.base', 'python')
    builder = code.get_builder()
    builder.structure = generate_structure()

    results, node = engine.run_get_node(builder)
    assert node.is_finished_ok

    parameters = results['parameters'].get_dict()

    # Timings differ from run to run, so we just check the expected keys exist and are floats.
    timings = parameters.pop('timings')
    for key in ('total', 'mean_field'):
        assert key in timings
        assert isinstance(timings[key], float)

    # The structure is a water molecule with ideal structure so forces are close to zero. They are compared using the
    # ``num_regression`` fixture to account for negligible float value differences.
    forces = parameters.pop('forces')
    num_regression.check({'forces': numpy.array(forces).flatten()}, default_tolerance={'atol': 1e-4, 'rtol': 1e-18})

    data_regression.check(parameters)


def test_pyscf_base_geometry_optimization(
    aiida_local_code_factory, generate_structure, data_regression, num_regression
):
    """Test running a geometry optimization ``PyscfCalculation`` job."""
    code = aiida_local_code_factory('pyscf.base', 'python')
    builder = code.get_builder()
    builder.structure = generate_structure()
    builder.parameters = orm.Dict({
        'optimizer': {
            'solver': 'geomeTRIC',
        },
    })
    results, node = engine.run_get_node(builder)
    assert node.is_finished_ok

    parameters = results['parameters'].get_dict()

    # Timings differ from run to run, so we just check the expected keys exist and are floats.
    timings = parameters.pop('timings')
    for key in ('total', 'mean_field', 'optimizer'):
        assert key in timings
        assert isinstance(timings[key], float)

    # The structure is a water molecule with ideal structure so forces are close to zero. They are compared using the
    # ``num_regression`` fixture to account for negligible float value differences. The same goes for the optimized
    # coordinates which can have small fluctuations due to randomness in the relaxation path.
    forces = parameters.pop('forces')
    optimized_coordinates = parameters.pop('optimized_coordinates')
    num_regression.check(
        {
            'forces': numpy.array(forces).flatten(),
            'optimized_coordinates': numpy.array(optimized_coordinates).flatten()
        },
        default_tolerance={
            'atol': 1e-4,
            'rtol': 1e-18
        },
    )
    data_regression.check(parameters)


def test_pyscf_base_fcidump(aiida_local_code_factory, generate_structure):
    """Test a ``PyscfCalculation`` job with an ``fcidump`` calculation."""
    code = aiida_local_code_factory('pyscf.base', 'python')
    builder = code.get_builder()
    builder.structure = generate_structure(formula='N2')
    builder.parameters = orm.Dict({
        'mean_field': {
            'method': 'RHF'
        },
        'fcidump': {
            'active_spaces': [[5, 6, 8, 9]],
            'occupations': [[1, 1, 1, 1]]
        }
    })

    results, node = engine.run_get_node(builder)
    assert node.is_finished_ok
    assert 'fcidump' in results
    assert all(isinstance(node, orm.SinglefileData) for node in results['fcidump'].values())
