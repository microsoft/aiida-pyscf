# -*- coding: utf-8 -*-
"""Parser for a :class:`aiida_pyscf.calculations.base.PyscfCalculation` job."""
from __future__ import annotations

import json
import pathlib

import dill
import numpy
from aiida.engine import ExitCode
from aiida.orm import ArrayData, Dict, SinglefileData, TrajectoryData
from aiida.parsers.parser import Parser
from aiida_shell.data import PickledData
from ase.io.extxyz import read_extxyz
from pint import UnitRegistry

from aiida_pyscf.calculations.base import PyscfCalculation

ureg = UnitRegistry()


class PyscfParser(Parser):
    """Parser for a :class:`aiida_pyscf.calculations.base.PyscfCalculation` job."""

    def __init__(self, *args, **kwargs):
        """Construct a new instance."""
        self.dirpath_temporary: pathlib.Path | None = None
        super().__init__(*args, **kwargs)

    def parse(self, retrieved_temporary_folder: str | None = None, **kwargs):  # noqa: PLR0912, PLR0915
        """Parse the contents of the output files stored in the ``retrieved`` output node.

        :returns: An exit code if the job failed.
        """
        self.dirpath_temporary = pathlib.Path(retrieved_temporary_folder) if retrieved_temporary_folder else None

        if 'parameters' in self.node.inputs:
            parameters = self.node.inputs.parameters.get_dict()
        else:
            parameters = {}

        try:
            with self.retrieved.base.repository.open(PyscfCalculation.FILENAME_STDOUT, 'r') as handle:
                handle.read()
        except FileNotFoundError:
            return self.handle_failure('ERROR_OUTPUT_STDOUT_MISSING')

        try:
            with self.retrieved.base.repository.open(PyscfCalculation.FILENAME_RESULTS, 'rb') as handle:
                parsed_json = json.load(handle)
        except FileNotFoundError:
            return self.handle_failure('ERROR_OUTPUT_RESULTS_MISSING')

        try:
            with self.retrieved.base.repository.open(PyscfCalculation.FILENAME_MODEL, 'rb') as handle:
                model = dill.load(handle)
        except FileNotFoundError:
            if parameters.get('results', {}).get('pickle_model', True):
                self.logger.warning(f'The pickled model file `{PyscfCalculation.FILENAME_MODEL}` could not be read.')
        except dill.UnpicklingError:
            self.logger.warning(f'The pickled model file `{PyscfCalculation.FILENAME_MODEL}` could not be unpickled.')
        else:
            self.out('model', PickledData(model))

        results_mean_field = parsed_json.setdefault('mean_field', {})

        if 'optimized_coordinates' in parsed_json.get('optimizer', {}):
            structure = self.node.inputs.structure.clone()
            optimized_coordinates = parsed_json['optimizer'].pop('optimized_coordinates') * ureg.bohr
            structure.reset_sites_positions(optimized_coordinates.to(ureg.angstrom).magnitude.tolist())
            self.out('structure', structure)

        if 'total_energy' in results_mean_field:
            energy = results_mean_field['total_energy'] * ureg.hartree
            results_mean_field['total_energy'] = energy.to(ureg.electron_volt).magnitude
            results_mean_field['total_energy_units'] = 'eV'

        if 'molecular_orbitals' in results_mean_field:
            labels = results_mean_field['molecular_orbitals']['labels']
            energies = results_mean_field['molecular_orbitals']['energies'] * ureg.hartree
            results_mean_field['molecular_orbitals']['energies'] = energies.to(ureg.electron_volt).magnitude.tolist()
            results_mean_field['molecular_orbitals']['labels'] = [label.strip() for label in labels]

        if 'forces' in results_mean_field:
            forces = results_mean_field['forces'] * ureg.hartree / ureg.bohr
            results_mean_field['forces'] = forces.to(ureg.electron_volt / ureg.angstrom).magnitude.tolist()
            results_mean_field['forces_units'] = 'eV/Å'

        if self.dirpath_temporary:
            for filepath_cubegen in self.dirpath_temporary.glob('mo_*.cube'):
                self.out(f'cubegen.orbitals.{filepath_cubegen.stem}', SinglefileData(filepath_cubegen))

            for filepath_density in self.dirpath_temporary.glob('density.cube'):
                self.out('cubegen.density', SinglefileData(filepath_density))

            for filepath_mep in self.dirpath_temporary.glob('mep.cube'):
                self.out('cubegen.mep', SinglefileData(filepath_mep))

            for filepath_fcidump in self.dirpath_temporary.glob('*.fcidump'):
                self.out(f'fcidump.{filepath_fcidump.stem}', SinglefileData(filepath_fcidump))

            for filepath_hessian in self.dirpath_temporary.glob('hessian.npy'):
                with filepath_hessian.open('rb') as handle:
                    hessian = numpy.load(handle)
                    array = ArrayData()
                    array.set_array('hessian', hessian)
                    self.out('hessian', array)

            filepath_trajectory = list(self.dirpath_temporary.glob('*_optim.xyz'))
            if filepath_trajectory:
                # There should be only one file that matches the pattern in the glob.
                trajectory = self.build_output_trajectory(filepath_trajectory[0])
                self.out('trajectory', trajectory)

        self.out('parameters', Dict(parsed_json))

        if results_mean_field['is_converged'] is False:
            return self.handle_failure('ERROR_ELECTRONIC_CONVERGENCE_NOT_REACHED', override_scheduler=True)

        if 'optimizer' in parsed_json and parsed_json['optimizer']['is_converged'] is False:
            return self.handle_failure('ERROR_IONIC_CONVERGENCE_NOT_REACHED', override_scheduler=True)

        return ExitCode(0)

    def build_output_trajectory(self, filepath_trajectory: pathlib.Path) -> TrajectoryData:
        """Build the ``TrajectoryData`` output node from the optimization file.

        :param filepath_trajectory: The filepath to the file containing the trajectory frames in XYZ format.
        :returns: The trajectory output node.
        """
        positions = []
        energies = []

        def batch(iterable, batch_size):
            """Split an iterable into a list of elements which size ``batch_size."""
            return [iterable[i : i + batch_size] for i in range(0, len(iterable), batch_size)]

        with filepath_trajectory.open() as handle:
            for atoms in read_extxyz(handle, index=slice(None, None)):
                positions.append(atoms.positions.tolist())
                # The ``atoms.info`` contains the parsed contents of the comment line in the XYZ frame. The geometry
                # optimizer does not use proper extended XYZ format, which is parsed by ASE as:
                #   {'Iteration': True, '0': True, 'Energy': True, '-74.96440482': True}
                # We convert this into a dictionary to extract the energy.
                properties = dict(batch(list(atoms.info), 2))
                energies.append(float(properties['Energy']))

        # Since the geometry optimization only supports atomic relaxation, the cell is fixed. The cells and the arrays
        # of symbols are therefore static and the input cell and symbol list can be copied for the number of frames.
        nframes = len(positions)
        trajectory = TrajectoryData()
        trajectory.set_trajectory(
            stepids=numpy.arange(nframes),
            cells=numpy.array([self.node.inputs.structure.cell] * nframes),
            symbols=[site.kind_name for site in self.node.inputs.structure.sites],
            positions=numpy.array(positions),
        )
        energies = (numpy.array(energies) * ureg.hartree).to(ureg.electron_volt).magnitude  # type: ignore[attr-defined]
        trajectory.set_array('energies', energies)

        return trajectory

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
