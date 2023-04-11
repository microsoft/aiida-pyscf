# -*- coding: utf-8 -*-
"""Parser for a :class:`aiida_pyscf.calculations.base.PyscfCalculation` job."""
from __future__ import annotations

import json
import pathlib

from aiida.engine import ExitCode
from aiida.orm import Dict, SinglefileData
from aiida.parsers.parser import Parser
from pint import UnitRegistry

from aiida_pyscf.calculations.base import PyscfCalculation


class PyscfParser(Parser):
    """Parser for a :class:`aiida_pyscf.calculations.base.PyscfCalculation` job."""

    def __init__(self, *args, **kwargs):
        """Construct a new instance."""
        self.dirpath_temporary: pathlib.Path | None = None
        super().__init__(*args, **kwargs)

    def parse(self, retrieved_temporary_folder: str | None = None, **kwargs):  # pylint: disable=arguments-differ,too-many-locals
        """Parse the contents of the output files stored in the ``retrieved`` output node.

        :returns: An exit code if the job failed.
        """
        ureg = UnitRegistry()
        self.dirpath_temporary = pathlib.Path(retrieved_temporary_folder) if retrieved_temporary_folder else None

        try:
            with self.retrieved.base.repository.open(PyscfCalculation.FILENAME_STDOUT, 'r') as handle:
                stdout = handle.read()  # pylint: disable=unused-variable
        except FileNotFoundError:
            return self.handle_failure('ERROR_OUTPUT_STDOUT_MISSING')

        try:
            with self.retrieved.base.repository.open(PyscfCalculation.FILENAME_RESULTS, 'rb') as handle:
                parsed_json = json.load(handle)
        except FileNotFoundError:
            return self.handle_failure('ERROR_OUTPUT_RESULTS_MISSING')

        if 'optimized_coordinates' in parsed_json:
            structure = self.node.inputs.structure.clone()
            optimized_coordinates = parsed_json.pop('optimized_coordinates') * ureg.bohr
            structure.reset_sites_positions(optimized_coordinates.to(ureg.angstrom).magnitude.tolist())
            self.out('structure', structure)

        if 'total_energy' in parsed_json:
            energy = parsed_json['total_energy'] * ureg.hartree
            parsed_json['total_energy'] = energy.to(ureg.electron_volt).magnitude
            parsed_json['total_energy_units'] = 'eV'

        if 'molecular_orbitals' in parsed_json:
            labels = parsed_json['molecular_orbitals']['labels']
            energies = parsed_json['molecular_orbitals']['energies'] * ureg.hartree
            parsed_json['molecular_orbitals']['energies'] = energies.to(ureg.electron_volt).magnitude
            parsed_json['molecular_orbitals']['labels'] = [label.strip() for label in labels]

        if 'forces' in parsed_json:
            forces = parsed_json['forces'] * ureg.hartree / ureg.bohr
            parsed_json['forces'] = forces.to(ureg.electron_volt / ureg.angstrom).magnitude.tolist()
            parsed_json['forces_units'] = 'eV/Å'

        if self.dirpath_temporary:
            for filepath_cubegen in self.dirpath_temporary.glob('*.cube'):
                self.out(f'cubegen.{filepath_cubegen.stem}', SinglefileData(filepath_cubegen))

            for filepath_fcidump in self.dirpath_temporary.glob('*.fcidump'):
                self.out(f'fcidump.{filepath_fcidump.stem}', SinglefileData(filepath_fcidump))

        self.out('parameters', Dict(parsed_json))

        if parsed_json['is_converged'] is False:
            return self.handle_failure('ERROR_ELECTRONIC_CONVERGENCE_NOT_REACHED', override_scheduler=True)

        return ExitCode(0)

    def handle_failure(self, exit_code_label: str, override_scheduler: bool = False) -> ExitCode:
        """Return the exit code corresponding to the given label unless the scheduler.

        This method also takes care of attaching the checkfile as an output if it was retrieved.

        :param override_scheduler: If set to ``True``, will return the given exit code even if one had already been set
            by the scheduler plugin.
        :returns: The exit code that should be returned by the caller.
        """
        self.attach_checkpoint_output()

        # If ``override_scheduler`` is ``False`` and an exit status has already been set by the scheduler, keep that by
        # returning it as is.
        if not override_scheduler and self.node.exit_status is not None:
            return ExitCode(self.node.exit_status, self.node.exit_message)

        # Either the scheduler parser did not return an exit code or we should override it regardless.
        return getattr(self.exit_codes, exit_code_label)

    def attach_checkpoint_output(self) -> None:
        """Attach the checkpoint file as an output if it was retrieved in the temporary folder."""
        if self.dirpath_temporary is None:
            return

        self.out('checkpoint', SinglefileData(self.dirpath_temporary / PyscfCalculation.FILENAME_CHECKPOINT))
