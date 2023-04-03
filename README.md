# `aiida-pyscf`
[![PyPI version](https://badge.fury.io/py/aiida-pyscf.svg)](https://badge.fury.io/py/aiida-pyscf)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/aiida-pyscf.svg)](https://pypi.python.org/pypi/aiida-pyscf)
[![CI](https://github.com/microsoft/aiida-pyscf/workflows/ci/badge.svg)](https://github.com/microsoft/aiida-pyscf/actions/workflows/ci.yml)

An [AiiDA](https://www.aiida.net) plugin for the [Python-based Simulations of Chemistry Framework (PySCF)](https://pyscf.org/index.html).

1. [Installation](#installation)
2. [Requirements](#requirements)
3. [Setup](#setup)
4. [Examples](#examples)
    * [Mean-field calculation](#mean-field-calculation)
    * [Customizing the structure](#customizing-the-structure)
    * [Optimizing geometry](#optimizing-geometry)
    * [Writing Hamiltonian to FCIDUMP files](#writing-hamiltonian-to-fcidump-files)
    * [Writing orbitals to CUBE files](#writing-orbitals-to-cube-files)

## Installation

The recommended method of installation is through [`pip`](https://pip.pypa.io/en/stable/):

    pip install aiida-pyscf

## Requirements

To use `aiida-pyscf` a configured AiiDA profile is required.
Please refer to the [documentation of `aiida-core`](https://aiida.readthedocs.io/projects/aiida-core/en/latest/intro/get_started.html) for detailed instructions.

## Setup

To run a PySCF calculation through AiiDA using the `aiida-pyscf` plugin, the computer needs to be configured where PySCF should be run.
Please refer to the [documentation of `aiida-core`](https://aiida.readthedocs.io/projects/aiida-core/en/latest/howto/run_codes.html#computer-setup) for detailed instructions.

Then the PySCF code needs to be configured.
The following YAML configuration file can be taken as a starting point:
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
Write the contents to a file named `pyscf.yml`, making sure to update the value of `computer` to the label of the computer configured in the previous step.
To configure the code, execute:
```bash
verdi code create core.code.installed --config pyscf.yml -n
```
This should now have created the code with the label `pyscf` that will be used in the following examples.

## Examples

### Mean-field calculation

The default calculation is to perform a mean-field calculation.
At a very minimum, the structure and the mean-field method should be defined:
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

The main results are stored in the `parameters` output, which by default contain the computed `total_energy` and `forces`, as well as some timing information:
```python
print(results['parameters'].get_dict())
{
    'forces': [
        [-6.4898366104394e-16, 3.0329042995656e-15, 2.2269765466236],
        [1.122487932593e-14, 0.64803103141326, -1.1134882733107],
        [-1.0575895664886e-14, -0.64803103141331, -1.1134882733108]
    ],
    'forces_units': 'eV/Å',
    'total_energy': -2039.8853743664,
    'total_energy_units': 'eV'
    'timings': {
        'total': 1.3238215579768, 'mean_field': 0.47364449803717
    },
}
```

### Customizing the structure

The geometry of the structure is fully defined through the `structure` input, which is provided by a `StructureData` node.
Any other properties, e.g., the charge and what basis set to use, can be specified through the `structure` dictionary in the `parameters` input:
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
Any attribute of the [`pyscf.gto.Mole` class](https://pyscf.org/user/gto.html) which is used to define the structure can be set through the `structure` dictionary, with the exception of the `atom` and `unit` attributes, which are set automatically by the plugin based on the `StructureData` input.

### Optimizing geometry

The geometry can be optimized by specifying the `optimizer` dictionary in the input `parameters`.
The `solver` has to be specified, and currently the solvers `geometric` and `berny` are supported.
The `convergence_parameters` accepts the parameters for the selected solver (see [PySCF documentation](https://pyscf.org/user/geomopt.html?highlight=geometry+optimization) for details):
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
The `parameters` output will contain the optimized structure coordinates:
```python
print(results['parameters'].get_dict())
{
    ...
    'optimized_coordinates': [
        [3.6553814911922e-16, -4.4060505668964e-14, 0.2752230960058],
        [8.5698519337032e-15, 1.4325248445029, -0.926413468005],
        [-7.8373230766793e-15, -1.4325248445029, -0.92641346800501]
    ]
}
```
For convenience, the optimized structure is also returned in the form of a `StructureData` under the `structure` output label.

### Writing Hamiltonian to FCIDUMP files

To instruct the calculation to dump a representation of the Hamiltonian to FCIDUMP files, add the `fcidump` dictionary to the `parameters` input:
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
The `active_spaces` and `occupations` keys are requires and each take a list of list of integers.
For each element in the list, a FCIDUMP file is generated for the corresponding active spaces and the occupations of the orbitals.
The shape of the `active_spaces` and `occupations` array has to be identical.

The generated FCIDUMP files are attached as `SinglefileData` output nodes in the `fcidump` namespace, where the label is determined by the corresponding active space:
```python
print(results['fcidump']['active_space_5_6_7_8'].get_content())
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

### Writing orbitals to CUBE files

To instruct the calculation to dump a representation of molecular orbitals to CUBE files, add the `cubegen` dictionary to the `parameters` input:
```python
from ase.build import molecule
from aiida.engine import run
from aiida.orm import Dict, StructureData, load_code

builder = load_code('pyscf').get_builder()
builder.structure = StructureData(ase=molecule('N2'))
builder.parameters = Dict({
    'mean_field': {'method': 'RHF'},
    'cubegen': {
        'indices': [5, 6],
        'parameters': {
            'nx': 40,
            'ny': 40,
            'nz': 40,
        }
    }
})
results, node = run.get_node(builder)
```
The `indices` key has to be specified and takes a list of integers, indicating the indices of the molecular orbitals that should be written to file.
Additional parameters can be provided in the `parameters` subdictionary (see the [PySCF documentation](https://pyscf.org/pyscf_api_docs/pyscf.tools.html?highlight=fcidump#module-pyscf.tools.cubegen) for details).

The generated CUBE files are attached as `SinglefileData` output nodes in the `cubegen` namespace, where the label is determined by the corresponding molecular orbital index:
```python
print(results['cubegen']['mo_5'].get_content())
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

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft
trademarks or logos is subject to and must follow
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
