# -*- coding: utf-8 -*-
"""Tests for the :mod:`aiida_pyscf.parsers.base` module."""
# pylint: disable=redefined-outer-name
from aiida_pyscf.calculations.base import PyscfCalculation


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
    node = generate_calc_job_node('pyscf.base', 'relax', inputs)
    parser = generate_parser('pyscf.base')
    results, calcfunction = parser.parse_from_node(node, store_provenance=False)

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_finished_ok, calcfunction.exit_message
    assert 'structure' in results
    data_regression.check({'structure': results['structure'].base.attributes.all})


def test_failed_missing_result(generate_calc_job_node, generate_parser):
    """Test parsing a retrieved folder where the result output file is missing."""
    node = generate_calc_job_node('pyscf.base', 'failed_missing_result')
    parser = generate_parser('pyscf.base')
    _, calcfunction = parser.parse_from_node(node, store_provenance=False)

    assert calcfunction.is_failed
    assert calcfunction.exit_status == PyscfCalculation.exit_codes.ERROR_OUTPUT_RESULTS_MISSING.status
