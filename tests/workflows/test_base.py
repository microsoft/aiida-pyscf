# -*- coding: utf-8 -*-
"""Tests for the :mod:`aiida_pyscf.workflows.base` module."""
from aiida.engine import ProcessHandlerReport

from aiida_pyscf.calculations.base import PyscfCalculation
from aiida_pyscf.workflows.base import PyscfBaseWorkChain


def test_setup(generate_workchain_pyscf_base):
    """Test ``PyscfBaseWorkChain.setup``."""
    process = generate_workchain_pyscf_base()
    process.setup()
    assert isinstance(process.ctx.inputs, dict)


def test_handle_unrecoverable_failure(generate_workchain_pyscf_base):
    """Test ``PyscfBaseWorkChain.handle_unrecoverable_failure``."""
    process = generate_workchain_pyscf_base(exit_code=PyscfCalculation.exit_codes.ERROR_OUTPUT_RESULTS_MISSING)
    process.setup()

    result = process.handle_unrecoverable_failure(process.ctx.children[-1])
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert result.exit_code == PyscfBaseWorkChain.exit_codes.ERROR_UNRECOVERABLE_FAILURE

    result = process.inspect_process()
    assert result == PyscfBaseWorkChain.exit_codes.ERROR_UNRECOVERABLE_FAILURE
