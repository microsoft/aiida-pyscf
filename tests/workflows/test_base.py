# -*- coding: utf-8 -*-
"""Tests for the :mod:`aiida_pyscf.workflows.base` module."""
import io

from aiida.engine import ProcessHandlerReport
from aiida.orm import SinglefileData

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


def test_handle_electronic_convergence_not_reached(generate_workchain_pyscf_base):
    """Test ``PyscfBaseWorkChain.handle_electronic_convergence_not_reached``."""
    process = generate_workchain_pyscf_base(
        exit_code=PyscfCalculation.exit_codes.ERROR_ELECTRONIC_CONVERGENCE_NOT_REACHED,
        outputs={'checkpoint': SinglefileData(io.StringIO('dummy checkpoint'))},
    )
    process.setup()

    result = process.handle_electronic_convergence_not_reached(process.ctx.children[-1])
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert process.ctx.inputs.checkpoint


def test_handle_out_of_walltime(generate_workchain_pyscf_base):
    """Test ``PyscfBaseWorkChain.handle_out_of_walltime``."""
    process = generate_workchain_pyscf_base(
        exit_code=PyscfCalculation.exit_codes.ERROR_SCHEDULER_OUT_OF_WALLTIME,
        outputs={'checkpoint': SinglefileData(io.StringIO('dummy checkpoint'))},
    )
    process.setup()

    # If the failed node has a ``checkpoint`` output, it should restart from that.
    result = process.handle_out_of_walltime(process.ctx.children[-1])
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert process.ctx.inputs.checkpoint

    process = generate_workchain_pyscf_base(exit_code=PyscfCalculation.exit_codes.ERROR_SCHEDULER_OUT_OF_WALLTIME)
    process.setup()

    # If the failed node has no ``checkpoint`` output, the work chain should abort.
    result = process.handle_out_of_walltime(process.ctx.children[-1])
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert result.exit_code.status == PyscfBaseWorkChain.exit_codes.ERROR_NO_CHECKPOINT_TO_RESTART.status
