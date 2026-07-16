# ==============================================================================
# File: discriminant.py
# Description: PARI/GP subprocess wrapper for exact nfdisc calculation.
# Tech Stack: Python 3.10+, PARI/GP 2.15+
# ==============================================================================

import subprocess
import os

def calculate_exact_discriminant(coeffs_asc: list[int], timeout: int = 60) -> str:
    """
    Uses PARI/GP to calculate the absolute number-field discriminant (nfdisc).
    Mimics the SAIR evaluation server's strict timeout execution.
    
    Args:
        coeffs_asc: 25 integers in ascending power order (a_0 ... a_24=1)
        timeout: Execution timeout in seconds.
        
    Returns:
        String representation of the discriminant (as it can exceed standard int bounds),
        or "TIMEOUT" / "ERROR".
    """
    # PARI/GP expects descending powers or strings like x^24 + ...
    # Easiest way is to construct the polynomial string:
    terms = []
    for power, coef in enumerate(coeffs_asc):
        if coef == 0:
            continue
        if power == 0:
            terms.append(str(coef))
        elif power == 1:
            terms.append(f"{coef}*x")
        else:
            terms.append(f"{coef}*x^{power}")
            
    poly_str = " + ".join(terms)
    # The GP command: print(nfdisc(poly_str))
    # We use abs() because the competition scores on absolute discriminant.
    gp_script = f"print(abs(nfdisc({poly_str})))"
    
    try:
        # Relies on 'gp' being in the system PATH
        result = subprocess.run(
            ['gp', '-q'], 
            input=gp_script.encode('utf-8'),
            capture_output=True,
            timeout=timeout
        )
        if result.returncode != 0:
            return "ERROR"
            
        return result.stdout.decode('utf-8').strip()
        
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except FileNotFoundError:
        return "ERROR_GP_NOT_FOUND"

if __name__ == "__main__":
    # Test with x^24 - x - 1
    coeffs = [-1, -1] + [0]*22 + [1]
    disc = calculate_exact_discriminant(coeffs, timeout=10)
    print(f"Discriminant: {disc}")
