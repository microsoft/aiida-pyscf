# -*- coding: utf-8 -*-
"""Tests for the :mod:`aiida_pyscf.workflows.base` module."""
import io

from aiida.engine import ProcessHandlerReport
from aiida.orm import Log, SinglefileData

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
    outputs = {'checkpoint': SinglefileData(io.StringIO('dummy checkpoint'))}
    process = generate_workchain_pyscf_base(
        exit_code=PyscfCalculation.exit_codes.ERROR_ELECTRONIC_CONVERGENCE_NOT_REACHED, outputs=outputs
    )
    process.setup()

    result = process.handle_electronic_convergence_not_reached(process.ctx.children[-1])
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert process.ctx.inputs.checkpoint == outputs['checkpoint']


def test_handle_ionic_convergence_not_reached(generate_workchain_pyscf_base, generate_structure, generate_trajectory):
    """Test ``PyscfBaseWorkChain.handle_ionic_convergence_not_reached``."""
    outputs = {'checkpoint': SinglefileData(io.StringIO('dummy checkpoint')), 'structure': generate_structure()}
    process = generate_workchain_pyscf_base(
        exit_code=PyscfCalculation.exit_codes.ERROR_IONIC_CONVERGENCE_NOT_REACHED, outputs=outputs
    )
    process.setup()

    result = process.handle_ionic_convergence_not_reached(process.ctx.children[-1])
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert process.ctx.inputs.checkpoint == outputs['checkpoint']
    assert process.ctx.inputs.structure == outputs['structure']

    # Test that the trajectory is used if no output structure is available.
    outputs = {'checkpoint': SinglefileData(io.StringIO('dummy checkpoint')), 'trajectory': generate_trajectory()}
    process = generate_workchain_pyscf_base(
        exit_code=PyscfCalculation.exit_codes.ERROR_IONIC_CONVERGENCE_NOT_REACHED, outputs=outputs
    )
    process.setup()

    result = process.handle_ionic_convergence_not_reached(process.ctx.children[-1])
    expected_structure = outputs['trajectory'].get_step_structure(index=-1)
    expected_structure.pbc = process.node.inputs.pyscf.structure.pbc
    expected_structure.store()
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert process.ctx.inputs.checkpoint == outputs['checkpoint']
    assert process.ctx.inputs.structure.attributes == expected_structure.attributes

    # Test that if outputs contain neither structure nor trajectory, the input structure is used
    outputs = {'checkpoint': SinglefileData(io.StringIO('dummy checkpoint'))}
    process = generate_workchain_pyscf_base(
        exit_code=PyscfCalculation.exit_codes.ERROR_IONIC_CONVERGENCE_NOT_REACHED, outputs=outputs
    )
    process.setup()

    result = process.handle_ionic_convergence_not_reached(process.ctx.children[-1])
    assert 'no output `structure` or `trajectory`: restarting from input structure.' in [
        log.message for log in Log.collection.get_logs_for(process.node)
    ]
    assert isinstance(result, ProcessHandlerReport)
    assert result.do_break
    assert process.ctx.inputs.checkpoint == outputs['checkpoint']
    assert process.ctx.inputs.structure == process.node.inputs.pyscf.structure


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
