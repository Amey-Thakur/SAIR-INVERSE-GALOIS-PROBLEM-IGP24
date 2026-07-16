# SAIR Inverse Galois Problem Challenge (IGP24)

![SAIR IGP24 Challenge](./social_preview.png)

**Prepared by**: [Amey Thakur](https://github.com/Amey-Thakur)

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PARI/GP 2.15+](https://img.shields.io/badge/PARI%2FGP-2.15+-004B87.svg)](https://pari.math.u-bordeaux.fr/)
[![LMFDB Integrated](https://img.shields.io/badge/Database-LMFDB-FF9900.svg)](https://www.lmfdb.org/)

Repository for the **SAIR Inverse Galois Problem Challenge (IGP24)**. An algebraic laboratory tracking and synthesizing explicit integer polynomial realizations for the 25,000 transitive permutation groups of degree 24.

---

## Research Scope

The Inverse Galois Problem over $\mathbb{Q}$ remains an open frontier. Degree 24 represents a critical computational boundary. This repository implements:
1. **LMFDB Integration**: Automated tracking and baseline comparison for known $(24T_t, r)$ realizations.
2. **Discriminant Optimization**: Local scoring tools interfacing with PARI/GP (`nfdisc`) to measure absolute number-field discriminants.
3. **Sandbox Validation**: Strict formatting parsers evaluating monic constraints and ascending coefficient layouts.
4. **Heuristic Search**: Sub-exponential bounds and algebraic construction strategies for missing transitive signatures.

---

## Directory Architecture

*   **[`docs/`](./docs/)**: Competition mechanics, mathematical background, and strategy literature.
*   **[`src/datasets/`](./src/datasets/)**: LMFDB baseline synchronization clients.
*   **[`src/evaluation/`](./src/evaluation/)**: PARI/GP discriminant wrappers and sandbox format verifiers.
*   **[`src/search/`](./src/search/)**: Mathematical search scaffolds and coefficient optimization algorithms.
*   **[`src/submission/`](./src/submission/)**: Pipeline compilers for 1,000-line daily submission limits.
*   **[`scripts/`](./scripts/)**: Standalone utilities.

---

## Development Workflow

1. **Synchronization**: Execute `src/datasets/lmfdb_client.py` to map current baseline discriminants.
2. **Evaluation**: Run `src/evaluation/verifier.py` to validate polynomial formatting locally.
3. **Scoring**: Evaluate exact discriminants using `src/evaluation/discriminant.py` prior to remote submission.
4. **Submission**: Aggregate candidate polynomials using `src/submission/compiler.py`.

---

## Acknowledgements

- **SAIR Foundation**: Challenge infrastructure and evaluation servers.
- **LMFDB**: L-functions and Modular Forms Database cataloging.
- **PARI/GP Team**: Number theory computational backend.