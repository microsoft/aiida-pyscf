# -*- coding: utf-8 -*-
"""``CalcJob`` plugin for PySCF."""
from __future__ import annotations

import io
import numbers
import typing as t

from aiida.common.datastructures import CalcInfo, CodeInfo
from aiida.common.folders import Folder
from aiida.engine import CalcJob, CalcJobProcessSpec
from aiida.orm import Dict, SinglefileData, StructureData
from ase.io.xyz import write_xyz
from jinja2 import Environment, PackageLoader, PrefixLoader
import numpy as np

__all__ = ('PyscfCalculation',)


class PyscfCalculation(CalcJob):
    """``CalcJob`` plugin for PySCF."""

    FILENAME_SCRIPT: str = 'script.py'
    FILENAME_STDERR: str = 'aiida.err'
    FILENAME_STDOUT: str = 'aiida.out'
    FILENAME_RESULTS: str = 'results.json'
    MAIN_TEMPLATE: str = 'pyscf/script.py.j2'

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
        spec.output_namespace('cubegen', valid_type=SinglefileData, required=False, help='Computed cube files.')
        spec.output_namespace('fcidump', valid_type=SinglefileData, required=False, help='Computed fcidump files.')

        spec.exit_code(302, 'ERROR_OUTPUT_STDOUT_MISSING', message='The stdout output file was not retrieved.')
        spec.exit_code(303, 'ERROR_OUTPUT_STDERR_MISSING', message='The stderr output file was not retrieved.')
        spec.exit_code(304, 'ERROR_OUTPUT_RESULTS_MISSING', message='The results JSON file was not retrieved.')

    @classmethod
    def validate_parameters(cls, value: Dict | None, _) -> str | None:  # pylint: disable=too-many-return-statements,too-many-branches
        """Validate the parameters input."""
        if not value:
            return None

        parameters = value.get_dict()

        mean_field_method = parameters.get('mean_field', {}).get('method', None)
        valid_methods = ['RKS', 'RHF', 'DKS', 'DHF', 'GKS', 'GHF', 'HF', 'KS', 'ROHF', 'ROKS', 'UKS', 'UHF']

        if mean_field_method and mean_field_method not in valid_methods:
            options = ' '.join(valid_methods)
            return f'specified mean field method {mean_field_method} is not supported, choose from: {options}'

        if 'optimizer' in parameters:
            valid_solvers = ('geometric', 'berny')
            solver = parameters['optimizer'].get('solver')

            if solver is None:
                return f'No solver specified in `optimizer` parameters. Choose from: {valid_solvers}'

            if solver.lower() not in valid_solvers:
                return f'Invalid solver `{solver}` specified in `optimizer` parameters. Choose from: {valid_solvers}'

        if 'cubegen' in parameters:
            indices = parameters['cubegen'].get('indices')

            if indices is None:
                return 'If the `cubegen` key is specified, the `indices` key has to be defined with a list of indices.'

            if not isinstance(indices, list) or any(not isinstance(e, int) for e in indices):
                return f'The `cubegen.indices` parameter should be a list of integers, but got: {indices}'

        if 'fcidump' in parameters:
            active_spaces = parameters['fcidump'].get('active_spaces')
            occupations = parameters['fcidump'].get('occupations')
            arrays = []

            for key, data in (('active_spaces', active_spaces), ('occupations', occupations)):
                try:
                    array = np.array(data)
                except ValueError:
                    return f'The `fcipdump.{key}` should be a nested list of integers, but got: {data}'

                arrays.append(array)

                if len(array.shape) != 2 or not issubclass(array.dtype.type, numbers.Integral):
                    return f'The `fcipdump.{key}` should be a nested list of integers, but got: {data}'

            if arrays[0].shape != arrays[1].shape:
                return 'The `fcipdump.active_spaces` and `fcipdump.occupations` arrays have different shapes.'

    def get_template_environment(self) -> Environment:
        """Return the template environment that should be used for rendering.

        :returns: The :class:`jinja2.Environment` to be used for rending the input script template.
        """
        environment = Environment(loader=PrefixLoader({'pyscf': PackageLoader('aiida_pyscf.calculations.base')}))
        environment.trim_blocks = True
        environment.lstrip_blocks = True
        environment.keep_trailing_newline = True
        environment.filters['render_python'] = self.filter_render_python
        return environment

    def get_parameters(self) -> dict[str, t.Any]:
        """Return the parameters to use for renderning the input script.

        The base dictionary is formed by the ``parameters`` input node, which is supplemented by default values and
        values that are based off other inputs, such as the ``structure`` converted to XYZ format.

        :returns: Complete dictionary of parameters to render the input script.
        """
        if 'parameters' in self.inputs:  # type: ignore[operator]
            parameters = self.inputs.parameters.get_dict()  # type: ignore[union-attr]
        else:
            parameters = {}

        parameters.setdefault('structure', {})['xyz'] = self.prepare_structure_xyz()
        parameters.setdefault('mean_field', {})
        parameters.setdefault('results', {})['filename_output'] = self.FILENAME_RESULTS

        return parameters

    @classmethod
    def filter_render_python(cls, value: t.Any) -> t.Any:
        """Render the ``value`` in a template literally as it would be rendered in a Python script.

        For now, it simply ensures that string variables are rendered with quotes as the default behavior of Jinja is to
        strip these strings, since it is mostly intended to generate HTML markup and not Python code.
        This filter can be registered in a template environment and then used as:

            {{ variable|render_python }}

        :param value: Any value that needs to be rendered literally.
        :return: The rendered value
        """
        if isinstance(value, str):
            return f"'{value}'"
        return value

    def render_script(self) -> str:
        """Return the rendered input script.

        :returns: The input script template rendered with the parameters provided by ``get_parameters``.
        """
        parameters = self.get_parameters()
        environment = self.get_template_environment()
        return environment.get_template(self.MAIN_TEMPLATE).render(**parameters)

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
        script = self.render_script()
        parameters = self.get_parameters()

        with folder.open(self.FILENAME_SCRIPT, 'w') as handle:
            handle.write(script)

        codeinfo = CodeInfo()
        codeinfo.cmdline_params = [self.FILENAME_SCRIPT]
        codeinfo.code_uuid = self.inputs.code.uuid  # type: ignore[union-attr]
        codeinfo.stderr_name = self.FILENAME_STDERR
        codeinfo.stdout_name = self.FILENAME_STDOUT

        calcinfo = CalcInfo()
        calcinfo.codes_info = [codeinfo]
        calcinfo.retrieve_temporary_list = []
        calcinfo.retrieve_list = [
            self.FILENAME_RESULTS,
            self.FILENAME_STDERR,
            self.FILENAME_STDOUT,
        ]

        if 'cubegen' in parameters:
            calcinfo.retrieve_temporary_list.append('*.cube')

        if 'fcidump' in parameters:
            calcinfo.retrieve_temporary_list.append('*.fcidump')

        return calcinfo
