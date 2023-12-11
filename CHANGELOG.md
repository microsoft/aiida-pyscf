# Change log

## `v0.4.2` - 2023-12-11

### Features

- `PyscfCalculation`: Add support to localize orbitals
  [\[d7923f2\]](https://github.com/microsoft/aiida-pyscf/commit/d7923f2158867b999dde4d90d41733cf6126d542)
- `PyscfCalculation`: Make the pickling of the model optional
  [\[671245e\]](https://github.com/microsoft/aiida-pyscf/commit/671245e7fec23e3a78f7b0b91fd1e47e4a8e77dc)

### Fixes

- `PyscfCalculation`: Fix bug in serializing model for `opt` attribute
  [\[5411429\]](https://github.com/microsoft/aiida-pyscf/commit/5411429b429d1274a9757b83e5ef21fbaa1ced07)
- `PyscfCalculation`: Make `cubegen` output namespace optional
  [\[c367633\]](https://github.com/microsoft/aiida-pyscf/commit/c367633055912b39ecdc9cad3fb70f841792bbb6)
- `PyscfCalculation`: Validate `parameters` for unknown arguments
  [\[f3d3278\]](https://github.com/microsoft/aiida-pyscf/commit/f3d32789c6d3fa991fb08df47bd240954032b2f4)

### Dependencies

- Put upper limit `pyscf<2.4`
  [\[aba7e1e\]](https://github.com/microsoft/aiida-pyscf/commit/aba7e1ed199057f6ba917772c92cf7c87c653ece)

### Devops

- Set `strategy.fail-fast` to `false` for CI
  [\[bf610fd\]](https://github.com/microsoft/aiida-pyscf/commit/bf610fde03034fc1b086adbb8a204914e25530b7)
- Pre-commit: Add automatic formatters for TOML and YAML files
  [\[45ef89e\]](https://github.com/microsoft/aiida-pyscf/commit/45ef89eabb752614f5b17b560bc729d7b07b763c)
- Pre-commit: Add markdown formatter
  [\[edcb7ae\]](https://github.com/microsoft/aiida-pyscf/commit/edcb7aea0fb16fb1ec806658400312451687cca6)
- Pre-commit: Migrate to `ruff`
  [\[5a5d721\]](https://github.com/microsoft/aiida-pyscf/commit/5a5d721a494b4f00372e84afc0e9f5946c2d284b)

## `v0.4.1` - 2023-08-16

### Features

- `PyscfCalculation`: Store serialized model as output
  [(a072ea6)](https://github.com/microsoft/aiida-pyscf/commit/a072ea6171b2204f94af8a6772a57fced0a0cef5)
- `PyscfCalculation`: Add support for computing the Hessian
  [(05cefef)](https://github.com/microsoft/aiida-pyscf/commit/05cefefe5bac8ce59b59747c47f6e99d8f6abd37)

## `v0.4.0` - 2023-06-13

### Features

- `PyscfCalculation`: Add support to compute charge density and MEP
  [(98445f4)](https://github.com/microsoft/aiida-pyscf/commit/98445f411a2a129d5e498299832fe4344b712551)
- `PyscfCalculation`: Add the `trajectory` output
  [(78de8e0)](https://github.com/microsoft/aiida-pyscf/commit/78de8e033a5f11b7253b2208cec12a3edf23bf8f)
- `PyscfBaseWorkChain`: Handle failed electronic convergence
  [(f138e71)](https://github.com/microsoft/aiida-pyscf/commit/f138e718b538460ae81f98cb5e7a038a907ad5c5)
- `PyscfCalculation`: Add the `checkpoint` input
  [(d596f3d)](https://github.com/microsoft/aiida-pyscf/commit/d596f3dfae659c065e30c78673f4d24c2220cc1d)
- `PyscfCalculation`: Add `checkpoint` file as output if not converged
  [(df15f83)](https://github.com/microsoft/aiida-pyscf/commit/df15f83553704470243bcc1da440557d9cc6155c)
- `PyscfCalculation`: Add molecular orbital details to `parameters` output
  [(40eb22d)](https://github.com/microsoft/aiida-pyscf/commit/40eb22dba21eadf7dfe22ee0b02bb5c06082bc4a)
- `PyscfCalculation`: Configure logging of geometric optimizer
  [(4308fca)](https://github.com/microsoft/aiida-pyscf/commit/4308fca2a1b6cb1e11baf273824a303a398e9504)
- `PyscfCalculation`: Add `ERROR_IONIC_CONVERGENCE_NOT_REACHED` exit code
  [(711b7f8)](https://github.com/microsoft/aiida-pyscf/commit/711b7f8b5def5091519d66d4d3f79cba473096ac)
- `PyscfBaseWorkChain`: Handle `ERROR_IONIC_CONVERGENCE_NOT_REACHED`
  [(7bb09f8)](https://github.com/microsoft/aiida-pyscf/commit/7bb09f8428c5ee753078a1c7822357d715f8cd17)
- `PyscfBaseWorkChain`: Handle `ERROR_SCHEDULER_OUT_OF_WALLTIME`
  [(3075bfa)](https://github.com/microsoft/aiida-pyscf/commit/3075bfa0a3ee8cbecda380f9747bd6a7a90daff5)
- `PyscfBaseWorkChain`: Handle `ERROR_SCHEDULER_NODE_FAILURE`
  [(6f494e7)](https://github.com/microsoft/aiida-pyscf/commit/6f494e761c1651f3c5efffaf564762ed0ddc4d0a)

### Changes

- `PyscfCalculation`: Change filename format of FCIDUMP files
  [(5cd9094)](https://github.com/microsoft/aiida-pyscf/commit/5cd9094973edb63fe4fa6096ad224dcad6f5464f)
- `PyscfCalculation`: Nest molecular orbitals in `cubegen` inputs/outputs
  [(68b204a)](https://github.com/microsoft/aiida-pyscf/commit/68b204a6102f51fea0c0334b16167273d9c0da3e)
- `PyscfCalculation`: Improve the layout of the `parameters` output
  [(0145f2c)](https://github.com/microsoft/aiida-pyscf/commit/0145f2cd87b43f0fb4bdae330c633af5cb0586cd)
- `PyscfCalculation`: Remove redirection of stderr to separate file
  [(90a7d07)](https://github.com/microsoft/aiida-pyscf/commit/90a7d07274fa97d9f43ff901fb3e198387b0f391)
- `PyscfCalculation`: Remove the default `mean_field.method`
  [(6d223ad)](https://github.com/microsoft/aiida-pyscf/commit/6d223ada1e12a0027a717e93d5bc550605bade7d)

### Fixes

- `PyscfCalculation`: Fix bug in script if SCF does not converge
  [(03f03a0)](https://github.com/microsoft/aiida-pyscf/commit/03f03a002303ead896efe731bbd36240d4cbf3a8)
- `PyscfParser`: Fix incorrect units of parsed optimized coordinates
  [(cfb5e5b)](https://github.com/microsoft/aiida-pyscf/commit/cfb5e5b7ff20d5685df9a214c682c88c2d7c79dc)
- `PyscfParser`: Do not override scheduler exit code if set
  [(47dd59b)](https://github.com/microsoft/aiida-pyscf/commit/47dd59bf4d69c31d8ab777d62eafe7388a467506)

### Dependencies

- Dependencies: Update requirement `mypy==1.3.0`
  [(631cf5f)](https://github.com/microsoft/aiida-pyscf/commit/631cf5f545a7d51b3a3afaa8e3c21cd9a561c5f1)

### Devops

- `PyscfParser`: Add unit tests for parsing of FCIDUMP and CUBE files
  [(017757c)](https://github.com/microsoft/aiida-pyscf/commit/017757ceae3e99ca77d3ed4503c464350c16de6d)

## `v0.3.0` - 2023-04-03

### Features

- `PyscfCalculation`: Add support for writing FCIDUMP files [(#17)](https://github.com/microsoft/aiida-pyscf/pull/17)
- `PyscfCalculation`: Add support for computing orbital cube files
  [(#20)](https://github.com/microsoft/aiida-pyscf/pull/20)
- `PyscfCalculation`: Ensure strings are rendered with quotes in templates
  [(#19)](https://github.com/microsoft/aiida-pyscf/pull/19)
- `PyscfCalculation`: Add validation for `optimizer` parameters
  [(#16)](https://github.com/microsoft/aiida-pyscf/pull/16)
- `PyscfCalculation`: Refactor to simplify subclassing [(#22)](https://github.com/microsoft/aiida-pyscf/pull/22)

### Documentation

- Docs: Add setup and run instructions to `README.md` [(#18)](https://github.com/microsoft/aiida-pyscf/pull/18)
- Docs: Add badges and table of contents to `README.md` [(#23)](https://github.com/microsoft/aiida-pyscf/pull/23)

### Devops

- CI: Update `pip` and install `wheel` [(#21)](https://github.com/microsoft/aiida-pyscf/pull/21)

## `v0.2.0` - 2023-03-28

### Improvements

- `PyscfCalculation`: Use `PrefixLoader` for template environment loader
  [(#12)](https://github.com/microsoft/aiida-pyscf/pull/12)
- `PyscfCalculation`: Improve white-space in rendered script [(#13)](https://github.com/microsoft/aiida-pyscf/pull/13)

## `v0.1.0` - 2023-03-27

First release of the package.
