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
