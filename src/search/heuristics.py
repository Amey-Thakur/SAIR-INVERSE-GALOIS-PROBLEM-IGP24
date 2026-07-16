# ==============================================================================
# File: heuristics.py
# Description: Local perturbation matrices to optimize known field discriminants.
# Tech Stack: Python 3.10+, NumPy
# ==============================================================================

import numpy as np

def perturb_coefficients(coeffs_asc: list[int], max_delta: int = 1, sparsity: float = 0.8) -> list[list[int]]:
    """
    Generates adjacent polynomials by slightly shifting coefficients.
    Used to sweep the local neighborhood of a known realization in an 
    attempt to discover a "simpler" field (smaller discriminant) that 
    shares the exact same Galois group.
    
    Args:
        coeffs_asc: Base polynomial coefficients (length 25).
        max_delta: Maximum integer shift per coefficient.
        sparsity: Probability of NOT shifting a specific coefficient.
        
    Returns:
        List of new polynomial coefficient arrays.
    """
    if len(coeffs_asc) != 25 or coeffs_asc[-1] != 1:
        raise ValueError("Invalid polynomial format.")
        
    base = np.array(coeffs_asc)
    candidates = []
    
    # Generate 100 random local perturbations
    for _ in range(100):
        # Only perturb a_0 to a_23
        mask = np.random.random(24) > sparsity
        shifts = np.random.randint(-max_delta, max_delta + 1, size=24) * mask
        
        # Ensure a_0 remains non-zero
        new_poly = base.copy()
        new_poly[:24] += shifts
        
        if new_poly[0] != 0:
            candidates.append(new_poly.tolist())
            
    return candidates
