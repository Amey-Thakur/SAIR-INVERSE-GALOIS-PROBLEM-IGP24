# ==============================================================================
# File: discriminant.py
# Description: PARI/GP wrapper for the two discriminants IGP24 scores on. It
#   mirrors the official commands exactly: an exact number-field discriminant
#   nfdisc(Polrev([a0,...,a24])) under a timeout, and the mixed fallback
#   nfdisc([f, 100000]) used for non-baseline pairs when the exact value times
#   out. Requires the `gp` binary (PARI/GP 2.15+) on PATH; without it every
#   call reports GP_NOT_FOUND rather than a wrong number.
# Usage: py src/evaluation/discriminant.py
# Tech Stack: Python 3.10+, PARI/GP 2.15+
# ==============================================================================

from __future__ import annotations

import subprocess


def _run_gp(script: str, timeout: int) -> str:
    try:
        result = subprocess.run(
            ["gp", "-q"],
            input=script.encode("utf-8"),
            capture_output=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return "GP_NOT_FOUND"
    except subprocess.TimeoutExpired:
        return "TIMEOUT"

    if result.returncode != 0:
        return "ERROR"
    return result.stdout.decode("utf-8").strip()


def _polrev(coeffs_asc: list[int]) -> str:
    return "Polrev([" + ",".join(str(c) for c in coeffs_asc) + "])"


def exact_nfdisc(coeffs_asc: list[int], timeout: int = 60) -> str:
    """Absolute exact number-field discriminant, the value that scores non
    baseline pairs and unlocks baseline pairs. Returns a decimal string, or
    TIMEOUT / ERROR / GP_NOT_FOUND."""
    script = f"print(abs(nfdisc({_polrev(coeffs_asc)})))"
    return _run_gp(script, timeout)


def mixed_disc(coeffs_asc: list[int], bound: int = 100000, timeout: int = 60) -> str:
    """The mixed fallback nfdisc([f, B]) used for non-baseline pairs when the
    exact computation times out. Not accepted for baseline improvements."""
    script = f"f={_polrev(coeffs_asc)};print(abs(nfdisc([f,{bound}])))"
    return _run_gp(script, timeout)


if __name__ == "__main__":
    # x^24 + x + 1, the competition's format example.
    coeffs = [1, 1] + [0] * 22 + [1]
    print("exact nfdisc:", exact_nfdisc(coeffs, timeout=30))
    print("mixed  disc :", mixed_disc(coeffs, timeout=30))
