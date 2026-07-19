# ==============================================================================
# File: verifier.py
# Description: Fast format pre-filter for a single submission line: 25 integer
#   coefficients, monic, nonzero constant term. This is a cheap gate for
#   streaming candidates; it does NOT check irreducibility. The authoritative
#   pre-submission gate, which also proves irreducibility over Q and rejects
#   baseline duplicates, is scripts/validate_submission.py.
# Tech Stack: Python 3.10+
# ==============================================================================

def verify_polynomial_line(line: str) -> bool:
    """
    Format check against the IGP24 coefficient rules.

    25 comma-separated integers, ascending powers a_0..a_24, monic (a_24 == 1),
    nonzero constant term (a_0 != 0). A trailing '#' comment is allowed and
    ignored. Irreducibility is left to scripts/validate_submission.py.
    """
    line = line.split("#", 1)[0].strip()
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
    # x^24 + x + 1, the format example from the competition rules.
    example = "1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1"
    print(f"Format valid: {verify_polynomial_line(example)}")
