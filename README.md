# `aiida-pyscf`

[![PyPI version](https://badge.fury.io/py/aiida-pyscf.svg)](https://badge.fury.io/py/aiida-pyscf)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/aiida-pyscf.svg)](https://pypi.python.org/pypi/aiida-pyscf)
[![CI](https://github.com/microsoft/aiida-pyscf/workflows/ci/badge.svg)](https://github.com/microsoft/aiida-pyscf/actions/workflows/ci.yml)

An [AiiDA](https://www.aiida.net) plugin for the
[Python-based Simulations of Chemistry Framework (PySCF)](https://pyscf.org/index.html).

1. [Installation](#installation)
1. [Requirements](#requirements)
1. [Setup](#setup)
1. [Examples](#examples)
   - [Mean-field calculation](#mean-field-calculation)
   - [Customizing the structure](#customizing-the-structure)
   - [Optimizing geometry](#optimizing-geometry)
   - [Writing Hamiltonian to FCIDUMP files](#writing-hamiltonian-to-fcidump-files)
   - [Writing orbitals to CUBE files](#writing-orbitals-to-cube-files)
   - [Restarting unconverged calculations](#restarting-unconverged-calculations)
   - [Automatic error recovery](#automatic-error-recovery)
   - [Pickled model](#pickled-model)

## Installation

The recommended method of installation is through [`pip`](https://pip.pypa.io/en/stable/):

```
pip install aiida-pyscf
```

## Requirements

To use `aiida-pyscf` a configured AiiDA profile is required. Please refer to the
[documentation of `aiida-core`](https://aiida.readthedocs.io/projects/aiida-core/en/latest/intro/get_started.html) for
detailed instructions.

## Setup

To run a PySCF calculation through AiiDA using the `aiida-pyscf` plugin, the computer needs to be configured where PySCF
should be run. Please refer to the
[documentation of `aiida-core`](https://aiida.readthedocs.io/projects/aiida-core/en/latest/howto/run_codes.html#computer-setup)
for detailed instructions.

Then the PySCF code needs to be configured. The following YAML configuration file can be taken as a starting point:

```yaml
label: pyscf
description: PySCF
computer: localhost
filepath_executable: python
default_calc_job_plugin: pyscf.base
use_double_quotes: false
with_mpi: false
prepend_text: ''
append_text: ''

```

Write the contents to a file named `pyscf.yml`, making sure to update the value of `computer` to the label of the
computer configured in the previous step. To configure the code, execute:

```bash
verdi code create core.code.installed --config pyscf.yml -n
```

This should now have created the code with the label `pyscf` that will be used in the following examples.

## Examples

### Mean-field calculation

The default calculation is to perform a mean-field calculation. At a very minimum, the structure and the mean-field
method should be defined:

```python
from ase.build import molecule
from aiida.engine import run
from aiida.orm import Dict, StructureData, load_code

builder = load_code('pyscf').get_builder()
builder.structure = StructureData(ase=molecule('H2O'))
builder.parameters = Dict({'mean_field': {'method': 'RHF'}})
results, node = run.get_node(builder)
```

This runs a Hartree-Fock calculation on the geometry of a water molecule.

The main results are stored in the `parameters` output, which by default contain the computed `total_energy` and
`forces`, details on the molecular orbitals, as well as some timing information:

```python
print(results['parameters'].get_dict())
{
    'mean_field': {
        'forces': [
            [-6.4898366104394e-16, 3.0329042995656e-15, 2.2269765466236],
            [1.122487932593e-14, 0.64803103141326, -1.1134882733107],
            [-1.0575895664886e-14, -0.64803103141331, -1.1134882733108]
        ],
        'forces_units': 'eV/Å',
        'molecular_orbitals': {
            'labels': [
                '0 O 1s',
                '0 O 2s',
                '0 O 2px',
                '0 O 2py',
                '0 O 2pz',
                '1 H 1s',
                '2 H 1s'
            ],
            'energies': [
                -550.86280025028,
                -34.375426862456,
                -16.629598134599,
                -12.323304634736,
                -10.637428057751,
                16.200273277782,
                19.796075801491
            ],
            'occupations': [2.0, 2.0, 2.0, 2.0, 2.0, 0.0, 0.0]
        },
        'total_energy': -2039.8853743664,
        'total_energy_units': 'eV',
    },
    'timings': {
        'total': 1.3238215579768, 'mean_field': 0.47364449803717
    },
}
```

### Customizing the structure

The geometry of the structure is fully defined through the `structure` input, which is provided by a `StructureData`
node. Any other properties, e.g., the charge and what basis set to use, can be specified through the `structure`
dictionary in the `parameters` input:

```python
from ase.build import molecule
from aiida.engine import run
from aiida.orm import Dict, StructureData, load_code

builder = load_code('pyscf').get_builder()
builder.structure = StructureData(ase=molecule('H2O'))
builder.parameters = Dict({
    'mean_field': {'method': 'RHF'},
    'structure': {
        'basis ': 'sto-3g',
        'charge': 0,
    }
})
results, node = run.get_node(builder)
```

Any attribute of the [`pyscf.gto.Mole` class](https://pyscf.org/user/gto.html) which is used to define the structure can
be set through the `structure` dictionary, with the exception of the `atom` and `unit` attributes, which are set
automatically by the plugin based on the `StructureData` input.

### Optimizing geometry

The geometry can be optimized by specifying the `optimizer` dictionary in the input `parameters`. The `solver` has to be
specified, and currently the solvers `geometric` and `berny` are supported. The `convergence_parameters` accepts the
parameters for the selected solver (see
[PySCF documentation](https://pyscf.org/user/geomopt.html?highlight=geometry+optimization) for details):

```python
from ase.build import molecule
from aiida.engine import run
from aiida.orm import Dict, StructureData, load_code

builder = load_code('pyscf').get_builder()
builder.structure = StructureData(ase=molecule('H2O'))
builder.parameters = Dict({
    'mean_field': {'method': 'RHF'},
    'optimizer': {
        'solver': 'geometric',
        'convergence_parameters': {
            'convergence_energy': 1e-6,  # Eh
            'convergence_grms': 3e-4,    # Eh/Bohr
            'convergence_gmax': 4.5e-4,  # Eh/Bohr
            'convergence_drms': 1.2e-3,  # Angstrom
            'convergence_dmax': 1.8e-3,  # Angstrom
        }
    }
})
results, node = run.get_node(builder)
```

The optimized structure is returned in the form of a `StructureData` under the `structure` output label. The structure
and energy of each frame in the geometry optimization trajectory, are stored in the form of a `TrajectoryData` under the
`trajectory` output label. The total energies can be retrieved as follows:

```python
results['trajectory'].get_array('energies')
```

### Localizing orbitals

To compute localized orbitals, specify the desired method in the `parameters.localize_orbitals.method` input:

```python
from ase.build import molecule
from aiida.engine import run
from aiida.orm import Dict, StructureData, load_code

builder = load_code('pyscf').get_builder()
builder.structure = StructureData(ase=molecule('H2O'))
builder.parameters = Dict({
    'mean_field': {'method': 'RHF'},
    'localize_orbitals': {'method': 'ibo'}
})
results, node = run.get_node(builder)
```

The following methods are supported: `boys`, `cholesky`, `edmiston`, `iao`, `ibo`, `lowdin`, `nao`, `orth`, `pipek`,
`vvo`. For more information, please refer to the [PySCF documentation](https://pyscf.org/user/lo.html).

### Computing the Hessian

In order to compute the Hessian, specify an empty dictionary for the `hessian` key in the `parameters` input:

```python
from ase.build import molecule
from aiida.engine import run
from aiida.orm import Dict, StructureData, load_code

builder = load_code('pyscf').get_builder()
builder.structure = StructureData(ase=molecule('H2O'))
builder.parameters = Dict({
    'mean_field': {'method': 'RHF'},
    'hessian': {}
})
results, node = run.get_node(builder)
```

The computed Hessian will be attached as an `ArrayData` node with the link label `hessian`. Use
`node.outputs.hessian.get_array('hessian')` to retrieve the computed Hessian as a numpy array for further processing.

### Writing Hamiltonian to FCIDUMP files

To instruct the calculation to dump a representation of the Hamiltonian to FCIDUMP files, add the `fcidump` dictionary
to the `parameters` input:

```python
from ase.build import molecule
from aiida.engine import run
from aiida.orm import Dict, StructureData, load_code

builder = load_code('pyscf').get_builder()
builder.structure = StructureData(ase=molecule('N2'))
builder.parameters = Dict({
    'mean_field': {'method': 'RHF'},
    'fcidump': {
        'active_spaces': [[5, 6, 8, 9]],
        'occupations': [[1, 1, 1, 1]]
    }
})
results, node = run.get_node(builder)
```

The `active_spaces` and `occupations` keys are requires and each take a list of list of integers. For each element in
the list, a FCIDUMP file is generated for the corresponding active spaces and the occupations of the orbitals. The shape
of the `active_spaces` and `occupations` array has to be identical.

The generated FCIDUMP files are attached as `SinglefileData` output nodes in the `fcidump` namespace, where the label is
determined by the index of the corresponding active space in the list:

```python
print(results['fcidump']['active_space_0'].get_content())
 &FCI NORB=   4,NELEC= 4,MS2=0,
  ORBSYM=1,1,1,1,
  ISYM=1,
 &END
  0.5832127121682998       1    1    1    1
  0.5359642500498074       1    1    2    2
 -2.942091015256668e-15    1    1    3    2
  0.5381290185905914       1    1    3    3
 -3.782672959584676e-15    1    1    4    1
  ...
```

### Generating CUBE files

The `pyscf.tools.cubegen` module provides functions to compute various properties of the system and write them as CUBE
files. The `PyscfCalculation` plugin currently supports computing the following:

- molecular orbitals
- charge density
- molecular electrostatic potential

To instruct the calculation to dump a representation of any of these quantities to CUBE files, add the `cubegen`
dictionary to the `parameters` input:

```python
from ase.build import molecule
from aiida.engine import run
from aiida.orm import Dict, StructureData, load_code

builder = load_code('pyscf').get_builder()
builder.structure = StructureData(ase=molecule('N2'))
builder.parameters = Dict({
    'mean_field': {'method': 'RHF'},
    'cubegen': {
        'orbitals: {
            'indices': [5, 6],
            'parameters': {
                'nx': 40,
                'ny': 40,
                'nz': 40,
            }
        },
        'density': {
            'parameters': {
                'resolution': 300,
            }
        },
        'mep': {
            'parameters': {
                'resolution': 300,
            }
        }
    }
})
results, node = run.get_node(builder)
```

The `indices` key has to be specified for the `orbitals` subdictionary and takes a list of integers, indicating the
indices of the molecular orbitals that should be written to file. Additional parameters can be provided in the
`parameters` subdictionary (see the
[PySCF documentation](https://pyscf.org/pyscf_api_docs/pyscf.tools.html?highlight=fcidump#module-pyscf.tools.cubegen)
for details). The `parameters` subdictionaries for the `density` and `mep` dictionaries are optional. To compute the
charge density and molecular electrostatic potential, the and empty dictionary for the `density` and `mep` keys,
respectively, is sufficient.

The generated CUBE files are attached as `SinglefileData` output nodes in the `cubegen` namespace, with the `orbitals`,
`density` and `mep` subnamespaces. For the `orbitals` subnamespace, the label is determined by the corresponding
molecular orbital index:

```python
print(results['cubegen']['orbitals']['mo_5'].get_content())
Orbital value in real space (1/Bohr^3)
PySCF Version: 2.1.1  Date: Sun Apr  2 15:59:19 2023
    2   -3.000000   -3.000000   -4.067676
   40    0.153846    0.000000    0.000000
   40    0.000000    0.153846    0.000000
   40    0.000000    0.000000    0.208599
    7    0.000000    0.000000    0.000000    1.067676
    7    0.000000    0.000000    0.000000   -1.067676
 -1.10860E-04 -1.56874E-04 -2.16660E-04 -2.92099E-04 -3.84499E-04 -4.94299E-04
 -6.20809E-04 -7.62048E-04 -9.14724E-04 -1.07439E-03 -1.23579E-03 -1.39331E-03
  ...
```

> **Warning** PySCF is known to fail when computing the MEP with DHF, DKS, GHF and GKS references.

### Restarting unconverged calculations

The plugin will automatically instruct PySCF to write a checkpoint file. If the calculation did not converge, it will
finish with exit status `410` and the checkpoint file is attached as a `SinglefileData` as the `checkpoint` output node.
This node can then be passed as input to a new calculation to restart from the checkpoint:

```python
failed_calculation = load_node(IDENTIFIER)
builder = failed_calculation.get_builder_restart()
builder.checkpoint = failed_calculation.outputs.checkpoint
submit(builder)
```

The plugin will write the checkpoint file of the failed calculation to the working directory such that PySCF can start
of from there.

### Post-processing

The `PyscfCalculation` plugin does not support all PySCF functionality; it aims to support most functionality that is
computationally intensive, as in this case it is important to be able to offload these calculations as a calcjob on a
remote compute resource. Most post-processing utilities are computationally inexpensive, and since the API is in Python,
they can be called directly in AiiDA workflows as `calcfunction`s. Many PySCF utilities require the _model_ of the
system as an argument, where model is the main object used in PySCF, i.e. the object assigned to the `mean_field`
variable in the following:

```python
from pyscf import scf
mean_field = scf.RHF(..)
mean_field.kernel()
```

The `kernel` method is often computationally expensive, but its results (stored on the model object) are lost when the
`PyscfCalculation` finishes as the Python interpreter of the calcjob shuts down and so the `mean_field` object no longer
exists. This would force post-processing code to reconstruct the model from scratch and rerun the expensive kernel.
Therefore, the `PyscfCalculation` serializes the PySCF model that was computed and stores it as a `PickledData` output
node with the link label `model` in the provenance graph. This allows recreating the model in another Python interpreter
and have it ready to be used for post-processing:

```python
from pyscf.hessian import thermo
node = load_node()  # Load the completed `PyscfCalculation`
mean_field = node.outputs.model.load()  # Reconstruct the model by calling the `load()` method
hessian = mean_field.Hessian().kernel()
freq_info = thermo.harmonic_analysis(mean_field.mol, hessian)
```

### Automatic error recovery

There are a variety of reasons why a PySCF calculation may not finish with the intended result. Examples are the
self-consistent field cycle not converging or the job getting killed by the scheduler because it ran out of the
requested walltime. The `PyscfBaseWorkChain` is designed to try and automatically recover from these kinds of errors
whenever it can potentially be handled. It is a simple wrapper around the `PyscfCalculation` plugin that automatically
restarts a new `PyscfCalculation` if the previous iterations failed. Launching a `PyscfBaseWorkChain` is almost
identical to launching a `PyscfCalculation` directly; the inputs just have to be "nested" inside the `pyscf` namespace:

```python
from aiida.engine import run
from aiida.orm import Dict, StructureData, load_code, load_node
from aiida_pyscf.workflows.base import PyscfBaseWorkChain
from ase.build import molecule

builder = PyscfBaseWorkChain.get_builder()
builder.pyscf.code = load_code('pyscf')
builder.pyscf.structure = StructureData(ase=molecule('H2O'))
builder.pyscf.parameters = Dict({
    'mean_field': {
        'method': 'RHF',
        'max_cycle': 3,
    }
})
results, node = run.get_node(builder)
```

In this example, we purposefully set the maximum number of iterations in the self-consistent field cycle to 3
(`'mean_field.max_cycle' = 3`), which will cause the first iteration to fail to reach convergence. The
`PyscfBaseWorkChain` detects the error, indicated by exit status `410` on the `PyscfCalculation`, and automatically
restarts the calculation from the saved checkpoint. After three iterations, the calculation converges:

```console
$ verdi process status IDENTIFIER
PyscfBaseWorkChain<30126> Finished [0] [2:results]
    ├── PyscfCalculation<30127> Finished [410]
    ├── PyscfCalculation<30132> Finished [410]
    └── PyscfCalculation<30137> Finished [0]
```

The following error modes are currently handled by the `PyscfBaseWorkChain`:

- `120`: Out of walltime: The calculation will be restarted from the last checkpoint if available, otherwise the work
  chain is aborted
- `140`: Node failure: The calculation will be restarted from the last checkpoint
- `410`: Electronic convergence not achieved: The calculation will be restarted from the last checkpoint
- `500`: Ionic convergence not achieved: The geometry optmizization did not converge, calculation will be restarted from
  the last checkpoint and structure

### Pickled model

The main objective of a `PyscfCalculation` is to solve the mean-field problem for a given structure. The results of
this, often computationally expensive, step are stored in the `mean_field_run` variable in the main script:

```python
mean_field = scf.RHF(structure)
density_matrix = mean_field.from_chk('restart.chk')
mean_field_run = mean_field.run(density_matrix)
```

The `mean_field_run` object can be used for a number of further post-processing operations implemented in PySCF. To keep
the `PyscfCalculation` interface simple, not all of this functionality is supported. However, as soon as the calculation
job finishes, the `mean_field_run` variable is lost and can no longer be accessed to be used for further processing.

As a workaround, the `PyscfCalculation` will ["pickle"](https://docs.python.org/3/library/pickle.html) the
`mean_field_run` object and attach it as the `model` output to the calculation. The `model` output node can be
"unpickled" to restore the original `mean_field_run` object such that it can be used for further processing:

```python
from aiida.engine import run
inputs = {}
results, node = run.get_node(PyscfCalculation, **inputs)
mean_field = node.outputs.model.load()
print(mean_field.e_tot)
```

> **Warning** For certain cases, the calculation may fail to pickle the model and will except. In this case, one can set
> the `pickle_model` input to the `PyscfCalculation` to `False`.

## Contributing

This project welcomes contributions and suggestions. Most contributions require you to agree to a Contributor License
Agreement (CLA) declaring that you have the right to, and actually do, grant us the rights to use your contribution. For
details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide a CLA and decorate
the PR appropriately (e.g., status check, comment). Simply follow the instructions provided by the bot. You will only
need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or contact
[opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks
or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft
sponsorship. Any use of third-party trademarks or logos are subject to those third-party's policies.
