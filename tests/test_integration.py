# -*- coding: utf-8 -*-
"""Module with integration tests."""
from aiida import engine, orm
import numpy

from aiida_pyscf.calculations.base import PyscfCalculation
from aiida_pyscf.workflows.base import PyscfBaseWorkChain


def test_pyscf_base_mean_field(aiida_local_code_factory, generate_structure, data_regression, num_regression):
    """Test running a default mean field ``PyscfCalculation`` job."""
    code = aiida_local_code_factory('pyscf.base', 'python')
    builder = code.get_builder()
    builder.structure = generate_structure()
    builder.parameters = orm.Dict({'mean_field': {'method': 'RHF'}})

    results, node = engine.run_get_node(builder)
    assert node.is_finished_ok

    parameters = results['parameters'].get_dict()

    # Timings differ from run to run, so we just check the expected keys exist and are floats.
    timings = parameters.pop('timings')
    for key in ('total', 'mean_field'):
        assert key in timings
        assert isinstance(timings[key], float)

    # The structure is a water molecule with ideal structure so forces are close to zero. They are compared using the
    # ``num_regression`` fixture to account for negligible float value differences. The same goes for the total energy.
    num_regression.check(
        {
            'forces': numpy.array(parameters['mean_field'].pop('forces')).flatten(),
            'total_energy': parameters['mean_field'].pop('total_energy'),
            'mo_energies': parameters['mean_field']['molecular_orbitals'].pop('energies'),
        },
        default_tolerance={
            'atol': 1e-4,
            'rtol': 1e-18
        },
    )
    data_regression.check(parameters)


def test_pyscf_base_geometry_optimization(
    aiida_local_code_factory, generate_structure, data_regression, num_regression
):
    """Test running a geometry optimization ``PyscfCalculation`` job."""
    code = aiida_local_code_factory('pyscf.base', 'python')
    builder = code.get_builder()
    builder.structure = generate_structure()
    builder.parameters = orm.Dict({
        'mean_field': {
            'method': 'RHF'
        },
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
    # ``num_regression`` fixture to account for negligible float value differences. The same goes for the total energy.
    num_regression.check(
        {
            'cell': numpy.array(results['structure'].cell).flatten(),
            'positions': numpy.array([site.position for site in results['structure'].sites]).flatten(),
            'forces': numpy.array(parameters['mean_field'].pop('forces')).flatten(),
            'total_energy': parameters['mean_field'].pop('total_energy'),
            'mo_energies': parameters['mean_field']['molecular_orbitals'].pop('energies'),
        },
        default_tolerance={
            'atol': 1e-4,
            'rtol': 1e-18
        },
    )
    data_regression.check(parameters)


def test_pyscf_base_hessian(aiida_local_code_factory, generate_structure):
    """Test a ``PyscfCalculation`` job with calculation of the Hessian."""
    code = aiida_local_code_factory('pyscf.base', 'python')
    builder = code.get_builder()
    builder.structure = generate_structure(formula='N2')
    builder.parameters = orm.Dict({'mean_field': {'method': 'RHF'}, 'hessian': {}})

    results, node = engine.run_get_node(builder)
    assert node.is_finished_ok
    assert 'hessian' in results
    assert isinstance(results['hessian'], orm.ArrayData)


def test_pyscf_base_cubegen(aiida_local_code_factory, generate_structure):
    """Test a ``PyscfCalculation`` job with an ``cubegen`` calculation."""
    code = aiida_local_code_factory('pyscf.base', 'python')
    builder = code.get_builder()
    builder.structure = generate_structure(formula='N2')
    builder.parameters = orm.Dict({
        'mean_field': {
            'method': 'RHF'
        },
        'cubegen': {
            'orbitals': {
                'indices': [5, 6],
            },
            'density': {},
            'mep': {},
        }
    })

    results, node = engine.run_get_node(builder)
    assert node.is_finished_ok
    assert 'cubegen' in results
    assert all(isinstance(node, orm.SinglefileData) for node in results['cubegen']['orbitals'].values())
    assert isinstance(results['cubegen']['density'], orm.SinglefileData)
    assert isinstance(results['cubegen']['mep'], orm.SinglefileData)


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


def test_pyscf_base_work_chain(aiida_local_code_factory, generate_structure):
    """Test a ``PyscfBaseWorkChain``: test the automatic restart after SCF fails to converge."""
    builder = PyscfBaseWorkChain.get_builder()
    builder.pyscf.code = aiida_local_code_factory('pyscf.base', 'python')  # pylint: disable=no-member
    builder.pyscf.structure = generate_structure(formula='H2O')  # pylint: disable=no-member
    builder.pyscf.parameters = orm.Dict(  # pylint: disable=no-member
        {
            'mean_field': {
                'method': 'RHF',
                'max_cycle': 3,
            }
        }
    )
    results, node = engine.run_get_node(builder)
    assert node.is_finished_ok
    assert [calcjob.exit_status for calcjob in sorted(node.called, key=lambda n: n.ctime)] == [410, 410, 0]
    assert 'parameters' in results


def test_failed_electronic_convergence(aiida_local_code_factory, generate_structure):
    """Test a ``PyscfCalculation`` job that fails to converge in the SCF cycle."""
    code = aiida_local_code_factory('pyscf.base', 'python')
    builder = code.get_builder()
    builder.structure = generate_structure(formula='NO')
    builder.parameters = orm.Dict({
        'mean_field': {
            'method': 'UKS',
            'xc': 'LDA',
        },
        'structure': {
            'symmetry': True,
            'basis': '6-31G',
            'spin': 1,
        }
    })
    results, node = engine.run_get_node(builder)
    assert node.is_failed
    assert node.exit_status == PyscfCalculation.exit_codes.ERROR_ELECTRONIC_CONVERGENCE_NOT_REACHED.status
    assert 'parameters' in results
    assert results['parameters'].get_dict()['mean_field']['is_converged'] is False
