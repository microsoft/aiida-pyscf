# -*- coding: utf-8 -*-
"""Workchain to run a pyscf calculation with automated error handling and restarts."""
from aiida.common import AttributeDict
from aiida.engine import BaseRestartWorkChain, ProcessHandlerReport, process_handler, while_
from aiida.plugins import CalculationFactory

PyscfCalculation = CalculationFactory('pyscf.base')


class PyscfBaseWorkChain(BaseRestartWorkChain):
    """Workchain to run a pyscf calculation with automated error handling and restarts."""

    _process_class = PyscfCalculation  # type: ignore[assignment]

    @classmethod
    def define(cls, spec):
        """Define the process specification."""
        super().define(spec)
        spec.expose_inputs(PyscfCalculation, namespace='pyscf')
        spec.expose_outputs(PyscfCalculation)
        spec.outline(
            cls.setup,
            while_(cls.should_run_process)(  # type: ignore[arg-type]
                cls.run_process,  # type: ignore[arg-type]
                cls.inspect_process,  # type: ignore[arg-type]
            ),
            cls.results,
        )
        spec.exit_code(
            300, 'ERROR_UNRECOVERABLE_FAILURE', message='The calculation failed with an unrecoverable error.'
        )
        spec.exit_code(
            310,
            'ERROR_NO_CHECKPOINT_TO_RESTART',
            message='The calculation failed and did not retrieve a checkpoint file from which can be restarted.',
        )

    def setup(self):
        """Call the `setup` of the `BaseRestartWorkChain` and then create the inputs dictionary in `self.ctx.inputs`.

        This `self.ctx.inputs` dictionary will be used by the `BaseRestartWorkChain` to submit the calculations in the
        internal loop.
        """
        super().setup()
        self.ctx.restart_calc = None
        self.ctx.inputs = AttributeDict(self.exposed_inputs(PyscfCalculation, 'pyscf'))  # type: ignore[arg-type]

    def report_error_handled(self, calculation, action):
        """Report an action taken for a calculation that has failed.

        This should be called in a registered error handler if its condition is met and an action was taken.

        :param calculation: the failed calculation node
        :param action: a string message with the action taken
        """
        arguments = [calculation.process_label, calculation.pk, calculation.exit_status, calculation.exit_message]
        self.report('{}<{}> failed with exit status {}: {}'.format(*arguments))
        self.report(f'Action taken: {action}')

    @process_handler(priority=600)
    def handle_unrecoverable_failure(self, node):
        """Handle calculations with an exit status below 400 which are unrecoverable, so abort the work chain."""
        if node.is_failed and node.exit_status < 400:
            self.report_error_handled(node, 'unrecoverable error, aborting...')
            return ProcessHandlerReport(True, self.exit_codes.ERROR_UNRECOVERABLE_FAILURE)

    @process_handler(
        priority=500,
        exit_codes=[
            PyscfCalculation.exit_codes.ERROR_IONIC_CONVERGENCE_NOT_REACHED,  # type: ignore[union-attr]
        ],
    )
    def handle_ionic_convergence_not_reached(self, node):
        """Handle ``ERROR_IONIC_CONVERGENCE_NOT_REACHED`` error.

        Simply restart the calculation using the ``checkpoint`` and ``structure`` outputs of the failed calculation as
        starting point.
        """
        self.ctx.inputs.checkpoint = node.outputs.checkpoint

        if 'structure' in node.outputs:
            self.ctx.inputs.structure = node.outputs.structure
        elif 'trajectory' in node.outputs:
            structure = node.outputs.trajectory.get_step_structure(index=-1)
            structure.pbc = self.ctx.inputs.structure.pbc
            structure.store()
            self.ctx.inputs.structure = structure
        else:
            self.logger.warning('no output `structure` or `trajectory`: restarting from input structure.')

        self.report_error_handled(node, 'restarting from the last checkpoint and structure.')
        return ProcessHandlerReport(True)

    @process_handler(
        priority=410,
        exit_codes=[
            PyscfCalculation.exit_codes.ERROR_ELECTRONIC_CONVERGENCE_NOT_REACHED,  # type: ignore[union-attr]
        ],
    )
    def handle_electronic_convergence_not_reached(self, node):
        """Handle ``ERROR_ELECTRONIC_CONVERGENCE_NOT_REACHED`` error.

        Simply restart the calculation using the ``checkpoint`` of the failed calculation as starting point.
        """
        self.ctx.inputs.checkpoint = node.outputs.checkpoint
        self.report_error_handled(node, 'restarting from the last checkpoint.')
        return ProcessHandlerReport(True)

    @process_handler(
        priority=110,
        exit_codes=[
            PyscfCalculation.exit_codes.ERROR_SCHEDULER_NODE_FAILURE,  # type: ignore[union-attr]
        ],
    )
    def handle_scheduler_node_failure(self, node):
        """Handle ``ERROR_SCHEDULER_NODE_FAILURE`` error.

        Simply restart the calculation using the last available ``checkpoint``, which is the output checkpoint of the
        failed calculation if available, or the previous checkpoint that was used in the inputs.
        """
        if 'checkpoint' in node.outputs:
            self.ctx.inputs.checkpoint = node.outputs.checkpoint

        self.report_error_handled(node, 'restarting from the last checkpoint.')
        return ProcessHandlerReport(True)

    @process_handler(
        priority=100,
        exit_codes=[
            PyscfCalculation.exit_codes.ERROR_SCHEDULER_OUT_OF_WALLTIME,  # type: ignore[union-attr]
        ],
    )
    def handle_out_of_walltime(self, node):
        """Handle ``ERROR_SCHEDULER_OUT_OF_WALLTIME`` error.

        Simply restart the calculation using the ``checkpoint`` if it was retrieved, otherwise abort since having to
        restart from scratch with the same walltime is likely going to fail again.
        """
        if 'checkpoint' not in node.outputs:
            self.report_error_handled(node, 'aborting because the failed calculation does not provide a checkpoint.')
            return ProcessHandlerReport(True, self.exit_codes.ERROR_NO_CHECKPOINT_TO_RESTART)

        self.ctx.inputs.checkpoint = node.outputs.checkpoint
        self.report_error_handled(node, 'restarting from the last checkpoint.')
        return ProcessHandlerReport(True)
