# -*- coding: utf-8 -*-
"""``CalcJob`` plugin for PySCF."""
from __future__ import annotations

import io

from aiida.common.datastructures import CalcInfo, CodeInfo
from aiida.common.folders import Folder
from aiida.engine import CalcJob, CalcJobProcessSpec
from aiida.orm import Dict, StructureData
from ase.io.xyz import write_xyz
from jinja2 import Environment, PackageLoader

__all__ = ('PyscfCalculation',)


class PyscfCalculation(CalcJob):
    """``CalcJob`` plugin for PySCF."""

    FILENAME_SCRIPT: str = 'script.py'
    FILENAME_STDERR: str = 'aiida.err'
    FILENAME_STDOUT: str = 'aiida.out'
    FILENAME_RESULTS: str = 'results.json'

    @classmethod
    def define(cls, spec: CalcJobProcessSpec):  # type: ignore[override]
        """Define the process specification.

        :param spec: The object to use to build up the process specification.
        """
        super().define(spec)
        spec.input(
            'structure',
            valid_type=StructureData,
            required=True,
            help='Input structure with molecular structure definition.',
        )
        spec.input(
            'parameters',
            valid_type=Dict,
            validator=cls.validate_parameters,
            required=False,
            help='Input parameters used to render the PySCF script template.',
        )
        spec.inputs['code'].required = True

        options = spec.inputs['metadata']['options']  # type: ignore[index]
        options['parser_name'].default = 'pyscf.base'  # type: ignore[index]
        options['resources'].default = {'num_machines': 1, 'tot_num_mpiprocs': 1}  # type: ignore[index]

        spec.output(
            'parameters',
            valid_type=Dict,
            required=False,
            help='Various computed properties parsed from the `FILENAME_RESULTS` output file.'
        )
        spec.output(
            'structure',
            valid_type=StructureData,
            required=False,
            help='The optimized structure if the input parameters contained the `optimizer` key.',
        )

        spec.exit_code(302, 'ERROR_OUTPUT_STDOUT_MISSING', message='The stdout output file was not retrieved.')
        spec.exit_code(303, 'ERROR_OUTPUT_STDERR_MISSING', message='The stderr output file was not retrieved.')
        spec.exit_code(304, 'ERROR_OUTPUT_RESULTS_MISSING', message='The results JSON file was not retrieved.')

    @classmethod
    def validate_parameters(cls, value: Dict | None, _) -> str | None:
        """Validate the parameters input."""
        if not value:
            return None

        parameters = value.get_dict()

        mean_field_method = parameters.get('mean_field', {}).get('method', None)
        valid_methods = ['RKS', 'RHF', 'DKS', 'DHF', 'GKS', 'GHF', 'HF', 'KS', 'ROHF', 'ROKS', 'UKS']

        if mean_field_method and mean_field_method not in valid_methods:
            options = ' '.join(valid_methods)
            return f'specified mean field method {mean_field_method} is not supported, choose from: {options}'

    def prepare_structure_xyz(self) -> str:
        """Return the input structure in XYZ format without the two leading header lines."""
        stream = io.StringIO()
        write_xyz(stream, [self.inputs.structure.get_ase()])  # type: ignore[union-attr]
        stream.seek(0)
        return '\n'.join(stream.read().split('\n')[2:])

    def prepare_for_submission(self, folder: Folder) -> CalcInfo:
        """Prepare the calculation for submission.

        :param folder: A temporary folder on the local file system.
        :returns: A :class:`aiida.common.datastructures.CalcInfo` instance.
        """
        env = Environment(loader=PackageLoader('aiida_pyscf.calculations.base'),)

        if 'parameters' in self.inputs:  # type: ignore[operator]
            parameters = self.inputs.parameters.get_dict()  # type: ignore[union-attr]
        else:
            parameters = {}

        parameters.setdefault('structure', {})['xyz'] = self.prepare_structure_xyz()

        script_structure = env.get_template('structure.py.j2').render(**parameters.get('structure', {}))
        script_mean_field = env.get_template('mean_field.py.j2').render(**parameters.get('mean_field', {}))
        script_results = env.get_template('results.py.j2').render(results={'filename_output': self.FILENAME_RESULTS})

        if 'optimizer' in parameters:
            script_optimizer = env.get_template('optimizer.py.j2').render(**parameters['optimizer'])
        else:
            script_optimizer = ''

        script = env.get_template('script.py.j2').render(
            script_structure=script_structure,
            script_mean_field=script_mean_field,
            script_optimizer=script_optimizer,
            script_results=script_results,
        )

        with folder.open(self.FILENAME_SCRIPT, 'w') as handle:
            handle.write(script)

        codeinfo = CodeInfo()
        codeinfo.cmdline_params = [self.FILENAME_SCRIPT]
        codeinfo.code_uuid = self.inputs.code.uuid  # type: ignore[union-attr]
        codeinfo.stderr_name = self.FILENAME_STDERR
        codeinfo.stdout_name = self.FILENAME_STDOUT

        calcinfo = CalcInfo()
        calcinfo.codes_info = [codeinfo]
        calcinfo.retrieve_list = [
            self.FILENAME_RESULTS,
            self.FILENAME_STDERR,
            self.FILENAME_STDOUT,
        ]

        return calcinfo
