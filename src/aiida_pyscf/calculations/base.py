# -*- coding: utf-8 -*-
"""``CalcJob`` plugin for PySCF."""
from __future__ import annotations

import copy
import io
import numbers
import pathlib
import typing as t

import numpy as np
from aiida.common.datastructures import CalcInfo, CodeInfo
from aiida.common.folders import Folder
from aiida.engine import CalcJob, CalcJobProcessSpec
from aiida.orm import ArrayData, Dict, SinglefileData, StructureData, TrajectoryData
from aiida_shell.data import PickledData
from ase.io.xyz import write_xyz
from jinja2 import Environment, PackageLoader, PrefixLoader
from plumpy.utils import AttributesFrozendict

__all__ = ('PyscfCalculation',)


class PyscfCalculation(CalcJob):
    """``CalcJob`` plugin for PySCF."""

    FILENAME_SCRIPT: str = 'script.py'
    FILENAME_STDOUT: str = 'aiida.out'
    FILENAME_RESULTS: str = 'results.json'
    FILENAME_MODEL: str = 'model.pickle'
    FILENAME_CHECKPOINT: str = 'checkpoint.chk'
    FILENAME_RESTART: str = 'restart.chk'
    FILEPATH_LOG_INI: pathlib.Path = pathlib.Path(__file__).parent / 'templates' / 'geometric_log.ini'
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
        spec.input(
            'checkpoint',
            valid_type=SinglefileData,
            required=False,
            help='Checkpoint of a previously completed calculation that failed to converge.',
        )
        spec.inputs['code'].required = True

        options = spec.inputs['metadata']['options']  # type: ignore[index]
        options['parser_name'].default = 'pyscf.base'  # type: ignore[index]
        options['resources'].default = {'num_machines': 1, 'tot_num_mpiprocs': 1}  # type: ignore[index]

        spec.output(
            'parameters',
            valid_type=Dict,
            required=False,
            help='Various computed properties parsed from the `FILENAME_RESULTS` output file.',
        )
        spec.output(
            'structure',
            valid_type=StructureData,
            required=False,
            help='The optimized structure if the input parameters contained the `optimizer` key.',
        )
        spec.output(
            'trajectory',
            valid_type=TrajectoryData,
            required=False,
            help='The geometry optimization trajectory if the input parameters contained the `optimizer` key.',
        )
        spec.output(
            'checkpoint',
            valid_type=SinglefileData,
            required=False,
            help='The checkpoint file in case the calculation did not converge. Can be used as an input for a restart.',
        )
        spec.output(
            'model',
            valid_type=PickledData,
            required=False,
            help='The model in serialized form. Can be deserialized and used without having to run the kernel again.',
        )
        spec.output_namespace('fcidump', valid_type=SinglefileData, required=False, help='Computed fcidump files.')
        spec.output_namespace(
            'cubegen.orbitals', valid_type=SinglefileData, required=False, help='Molecular orbitals in `.cube` format.'
        )
        spec.output(
            'cubegen.density', valid_type=SinglefileData, required=False, help='The charge density in `.cube` format.'
        )
        spec.output(
            'cubegen.mep',
            valid_type=SinglefileData,
            required=False,
            help='The molecular electrostatic potential (MEP) in `.cube` format.',
        )
        spec.outputs['cubegen'].required = False
        spec.output(
            'hessian',
            valid_type=ArrayData,
            required=False,
            help='The computed Hessian.',
        )

        spec.exit_code(302, 'ERROR_OUTPUT_STDOUT_MISSING', message='The stdout output file was not retrieved.')
        spec.exit_code(303, 'ERROR_OUTPUT_RESULTS_MISSING', message='The results JSON file was not retrieved.')
        spec.exit_code(
            410,
            'ERROR_ELECTRONIC_CONVERGENCE_NOT_REACHED',
            message='The electronic minimization cycle did not reach self-consistency.',
        )
        spec.exit_code(
            500,
            'ERROR_IONIC_CONVERGENCE_NOT_REACHED',
            message='The ionic minimization cycle did not converge for the given thresholds.',
        )

    @classmethod
    def validate_parameters(cls, value: Dict | None, _) -> str | None:  # noqa: PLR0911, PLR0912
        """Validate the parameters input."""
        if not value:
            return None

        parameters = copy.deepcopy(value.get_dict())

        mean_field = parameters.pop('mean_field', {})
        mean_field_method = mean_field.pop('method', None)
        valid_methods = ['RKS', 'RHF', 'DKS', 'DHF', 'GKS', 'GHF', 'HF', 'KS', 'ROHF', 'ROKS', 'UKS', 'UHF']
        options = ' '.join(valid_methods)

        if mean_field_method is None:
            return f'The `mean_field.method` has to be specified in the `parameters` input, choose from: {options}'

        if mean_field_method not in valid_methods:
            return f'Specified mean field method {mean_field_method} is not supported, choose from: {options}'

        if 'chkfile' in mean_field:
            return (
                'The `chkfile` cannot be specified in the `mean_field` parameters. It is set automatically by the '
                'plugin if the `checkpoint` input is provided.'
            )

        if (localize_orbitals := parameters.pop('localize_orbitals', None)) is not None:
            valid_lo = ('boys', 'cholesky', 'edmiston', 'iao', 'ibo', 'lowdin', 'nao', 'orth', 'pipek', 'vvo')
            method = localize_orbitals.get('method')
            if method is None:
                return f'No method specified in `localize_orbitals` parameters. Choose from: {valid_lo}'

            if method.lower() not in valid_lo:
                return f'Invalid method `{method}` specified in `localize_orbitals` parameters. Choose from: {valid_lo}'

        if (optimizer := parameters.pop('optimizer', None)) is not None:
            valid_solvers = ('geometric', 'berny')
            solver = optimizer.get('solver')

            if solver is None:
                return f'No solver specified in `optimizer` parameters. Choose from: {valid_solvers}'

            if solver.lower() not in valid_solvers:
                return f'Invalid solver `{solver}` specified in `optimizer` parameters. Choose from: {valid_solvers}'

        if (cubegen := parameters.pop('cubegen', None)) is not None:
            orbitals = cubegen.get('orbitals')
            indices = orbitals.get('indices') if orbitals is not None else None

            if orbitals is not None and indices is None:
                return (
                    'If the `cubegen.orbitals` key is specified, the `cubegen.orbitals.indices` key has to be defined '
                    'with a list of indices.'
                )

            if indices is not None and (not isinstance(indices, list) or any(not isinstance(e, int) for e in indices)):
                return f'The `cubegen.orbitals.indices` parameter should be a list of integers, but got: {indices}'

        if (fcidump := parameters.pop('fcidump', None)) is not None:
            active_spaces = fcidump.get('active_spaces')
            occupations = fcidump.get('occupations')
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

        # Remove other known arguments
        for key in ('hessian', 'results', 'structure'):
            parameters.pop(key, None)

        if unknown_keys := list(parameters.keys()):
            return f'The following arguments are not supported: {", ".join(unknown_keys)}'

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

    @property
    def inputs(self) -> AttributesFrozendict:
        """Return the inputs attribute dictionary or an empty one.

        This overrides the property of the base class because that can also return ``None``. This override ensures
        calling functions that they will always get an instance of ``AttributesFrozenDict``.
        """
        return super().inputs or AttributesFrozendict()

    def get_parameters(self) -> dict[str, t.Any]:
        """Return the parameters to use for renderning the input script.

        The base dictionary is formed by the ``parameters`` input node, which is supplemented by default values and
        values that are based off other inputs, such as the ``structure`` converted to XYZ format.

        :returns: Complete dictionary of parameters to render the input script.
        """
        if 'parameters' in self.inputs:
            parameters = self.inputs.parameters.get_dict()
        else:
            parameters = {}

        parameters.setdefault('structure', {})['xyz'] = self.prepare_structure_xyz()
        parameters.setdefault('mean_field', {})
        parameters.setdefault('results', {})['filename_output'] = self.FILENAME_RESULTS
        parameters.setdefault('results', {})['filename_model'] = self.FILENAME_MODEL
        parameters.setdefault('results', {}).setdefault('pickle_model', True)

        if 'optimizer' in parameters:
            parameters['optimizer'].setdefault('convergence_parameters', {})['logIni'] = 'log.ini'

        parameters['mean_field']['chkfile'] = self.FILENAME_CHECKPOINT

        if 'checkpoint' in self.inputs:
            parameters['mean_field']['checkpoint'] = self.FILENAME_RESTART

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
        write_xyz(stream, [self.inputs.structure.get_ase()])
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
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.stdout_name = self.FILENAME_STDOUT

        calcinfo = CalcInfo()
        calcinfo.codes_info = [codeinfo]
        calcinfo.provenance_exclude_list = []
        calcinfo.retrieve_temporary_list = [self.FILENAME_CHECKPOINT]
        calcinfo.retrieve_list = [
            self.FILENAME_RESULTS,
            self.FILENAME_MODEL,
            self.FILENAME_STDOUT,
        ]

        if 'checkpoint' in self.inputs:
            with self.inputs.checkpoint.open(mode='rb') as handle:
                folder.create_file_from_filelike(handle, self.FILENAME_RESTART)
            calcinfo.provenance_exclude_list.append(self.FILENAME_RESTART)

        if 'hessian' in parameters:
            calcinfo.retrieve_temporary_list.append('hessian.npy')

        if 'cubegen' in parameters:
            calcinfo.retrieve_temporary_list.append('*.cube')

        if 'fcidump' in parameters:
            calcinfo.retrieve_temporary_list.append('*.fcidump')

        if 'optimizer' in parameters:
            calcinfo.retrieve_temporary_list.append('*_optim.xyz')

            with self.FILEPATH_LOG_INI.open('rb') as handle:
                folder.create_file_from_filelike(handle, 'log.ini')

        return calcinfo
