# ==============================================================================
# File: verifier.py
# Description: Sandbox simulator validating the exact IGP24 submission format.
# Tech Stack: Python 3.10+
# ==============================================================================

def verify_polynomial_line(line: str) -> bool:
    """
    Validates a single string against the strict SAIR IGP24 constraints.
    
    Format: 25 comma-separated integers.
    Ascending powers: a_0, a_1, ..., a_24
    Monic: a_24 == 1
    Irreducible (trivial check): a_0 != 0
    """
    line = line.strip()
    if not line:
        return False
        
    parts = line.split(",")
    if len(parts) != 25:
        return False
        
    try:
        coeffs = [int(p.strip()) for p in parts]
    except ValueError:
        return False # Must be strictly integers
        
    # Check monic constraint (degree 24)
    if coeffs[24] != 1:
        return False
        
    # Trivial non-zero root check
    if coeffs[0] == 0:
        return False
        
    return True

def verify_file(filepath: str) -> tuple[int, int]:
    """
    Scans a submission file.
    Returns (valid_count, total_count).
    """
    valid = 0
    total = 0
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                total += 1
                if verify_polynomial_line(line):
                    valid += 1
                    
    return valid, total

if __name__ == "__main__":
    # Example valid line (x^24 - 1 ... wait, x^24 - 1 has a_0 = -1, a_24 = 1, others 0)
    example = "-1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1"
    print(f"Validation: {verify_polynomial_line(example)}")
