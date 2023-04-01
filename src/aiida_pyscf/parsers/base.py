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

    def parse(self, retrieved_temporary_folder: str | None = None, **kwargs):  # pylint: disable=arguments-differ
        """Parse the contents of the output files stored in the ``retrieved`` output node.

        :returns: An exit code if the job failed.
        """
        ureg = UnitRegistry()

        files_retrieved = self.retrieved.list_object_names()
        dirpath_temporary = pathlib.Path(retrieved_temporary_folder) if retrieved_temporary_folder else None

        for filename, exit_code in (
            (PyscfCalculation.FILENAME_STDERR, PyscfCalculation.exit_codes.ERROR_OUTPUT_STDERR_MISSING),
            (PyscfCalculation.FILENAME_STDOUT, PyscfCalculation.exit_codes.ERROR_OUTPUT_STDOUT_MISSING),
        ):
            if filename not in files_retrieved:
                return exit_code

        if PyscfCalculation.FILENAME_RESULTS not in files_retrieved:
            return self.exit_codes.ERROR_OUTPUT_RESULTS_MISSING

        with self.retrieved.open(PyscfCalculation.FILENAME_RESULTS, 'rb') as handle:
            parsed_json = json.load(handle)

        if 'optimized_coordinates' in parsed_json:
            structure = self.node.inputs.structure.clone()
            structure.reset_sites_positions(parsed_json['optimized_coordinates'])
            self.out('structure', structure)

        if 'total_energy' in parsed_json:
            energy = parsed_json['total_energy'] * ureg.hartree
            parsed_json['total_energy'] = energy.to(ureg.electron_volt).magnitude
            parsed_json['total_energy_units'] = 'eV'

        if 'forces' in parsed_json:
            forces = parsed_json['forces'] * ureg.hartree / ureg.bohr
            parsed_json['forces'] = forces.to(ureg.electron_volt / ureg.angstrom).magnitude.tolist()
            parsed_json['forces_units'] = 'eV/Å'

        if dirpath_temporary:
            for filepath_cubegen in dirpath_temporary.glob('*.cube'):
                self.out(f'cubegen.{filepath_cubegen.stem}', SinglefileData(filepath_cubegen))

            for filepath_fcidump in dirpath_temporary.glob('*.fcidump'):
                self.out(f'fcidump.{filepath_fcidump.stem}', SinglefileData(filepath_fcidump))

        self.out('parameters', Dict(parsed_json))

        return ExitCode(0)
