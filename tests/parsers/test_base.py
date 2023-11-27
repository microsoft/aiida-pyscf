# -*- coding: utf-8 -*-
"""Tests for the :mod:`aiida_pyscf.parsers.base` module."""
from aiida.orm import SinglefileData
from aiida_pyscf.calculations.base import PyscfCalculation
from aiida_shell.data import PickledData
from pyscf.scf.hf import RHF


def test_default(generate_calc_job_node, generate_parser, data_regression):
    """Test parsing a default output case."""
    node = generate_calc_job_node('pyscf.base', 'default')
    parser = generate_parser('pyscf.base')
    results, calcfunction = parser.parse_from_node(node, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_finished_ok, calcfunction.exit_message
    data_regression.check({'parameters': results['parameters'].get_dict()})


def test_relax(generate_calc_job_node, generate_parser, generate_structure, data_regression):
    """Test parsing the outputs of a job that optimizes the geometry."""
    inputs = {'structure': generate_structure('H2')}
    node, tmp_path = generate_calc_job_node('pyscf.base', 'relax', inputs, retrieve_temporary_list=['*_optim.xyz'])
    parser = generate_parser('pyscf.base')
    results, calcfunction = parser.parse_from_node(node, retrieved_temporary_folder=tmp_path, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_finished_ok, calcfunction.exit_message
    assert 'structure' in results
    data_regression.check(
        {
            'parameters': results['parameters'].get_dict(),
            'structure': results['structure'].base.attributes.all,
            'trajectory': results['trajectory'].base.attributes.all,
            'energies': results['trajectory'].get_array('energies').flatten().tolist(),
            'positions': results['trajectory'].get_array('positions').flatten().tolist(),
        }
    )


def test_failed_out_of_walltime(generate_calc_job_node, generate_parser):
    """Test parsing a retrieved folder where the job got interrupted by the scheduler because it ran out of walltime."""
    node = generate_calc_job_node('pyscf.base', 'failed_out_of_walltime')
    node.set_exit_status(PyscfCalculation.exit_codes.ERROR_SCHEDULER_OUT_OF_WALLTIME.status)
    parser = generate_parser('pyscf.base')
    _, calcfunction = parser.parse_from_node(node, store_provenance=False)

    assert calcfunction.is_failed
    assert calcfunction.exit_status == PyscfCalculation.exit_codes.ERROR_SCHEDULER_OUT_OF_WALLTIME.status


def test_failed_missing_result(generate_calc_job_node, generate_parser):
    """Test parsing a retrieved folder where the result output file is missing."""
    node = generate_calc_job_node('pyscf.base', 'failed_missing_result')
    parser = generate_parser('pyscf.base')
    _, calcfunction = parser.parse_from_node(node, store_provenance=False)

    assert calcfunction.is_failed
    assert calcfunction.exit_status == PyscfCalculation.exit_codes.ERROR_OUTPUT_RESULTS_MISSING.status


def test_failed_electronic_convergence(generate_calc_job_node, generate_parser):
    """Test parsing the results of a calculation that failed to converge electronically."""
    node, tmp_path = generate_calc_job_node(
        'pyscf.base', 'failed_electronic_convergence', retrieve_temporary_list=['*.chk']
    )
    parser = generate_parser('pyscf.base')
    _, calcfunction = parser.parse_from_node(node, retrieved_temporary_folder=tmp_path, store_provenance=False)

    assert calcfunction.is_failed
    assert calcfunction.exit_status == PyscfCalculation.exit_codes.ERROR_ELECTRONIC_CONVERGENCE_NOT_REACHED.status


def test_cubegen(generate_calc_job_node, generate_parser, generate_structure):
    """Test parsing the outputs of a job that computed CUBE files."""
    inputs = {'structure': generate_structure('N2')}
    node, tmp_path = generate_calc_job_node('pyscf.base', 'cubegen', inputs, retrieve_temporary_list=['*.cube'])
    parser = generate_parser('pyscf.base')
    results, calcfunction = parser.parse_from_node(node, retrieved_temporary_folder=tmp_path, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_finished_ok, calcfunction.exit_message
    assert 'cubegen' in results
    assert all(isinstance(node, SinglefileData) for node in results['cubegen']['orbitals'].values())
    assert isinstance(results['cubegen']['density'], SinglefileData)
    assert isinstance(results['cubegen']['mep'], SinglefileData)


def test_fcidump(generate_calc_job_node, generate_parser, generate_structure):
    """Test parsing the outputs of a job that computed FCIDUMP files."""
    inputs = {'structure': generate_structure('N2')}
    node, tmp_path = generate_calc_job_node('pyscf.base', 'fcidump', inputs, retrieve_temporary_list=['*.fcidump'])
    parser = generate_parser('pyscf.base')
    results, calcfunction = parser.parse_from_node(node, retrieved_temporary_folder=tmp_path, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_finished_ok, calcfunction.exit_message
    assert 'fcidump' in results
    assert all(isinstance(node, SinglefileData) for node in results['fcidump'].values())


def test_model_valid(generate_calc_job_node, generate_parser, generate_structure):
    """Test (de)serialization of model."""
    inputs = {'structure': generate_structure('N2')}
    node, tmp_path = generate_calc_job_node(
        'pyscf.base', 'model_valid', inputs, retrieve_temporary_list=[PyscfCalculation.FILENAME_MODEL]
    )
    parser = generate_parser('pyscf.base')
    results, calcfunction = parser.parse_from_node(node, retrieved_temporary_folder=tmp_path, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_finished_ok, calcfunction.exit_message
    assert 'model' in results
    assert isinstance(results['model'], PickledData)
    assert isinstance(results['model'].load(), RHF)


def test_model_invalid(generate_calc_job_node, generate_parser, generate_structure, caplog):
    """Test case for invalid serialized model.

    In this case, the parser should not except but log a warning.
    """
    inputs = {'structure': generate_structure('N2')}
    node, tmp_path = generate_calc_job_node(
        'pyscf.base', 'model_invalid', inputs, retrieve_temporary_list=[PyscfCalculation.FILENAME_MODEL]
    )
    parser = generate_parser('pyscf.base')
    results, calcfunction = parser.parse_from_node(node, retrieved_temporary_folder=tmp_path, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_finished_ok, calcfunction.exit_message
    assert f'The pickled model file `{PyscfCalculation.FILENAME_MODEL}` could not be unpickled.' in caplog.text
    assert 'model' not in results
