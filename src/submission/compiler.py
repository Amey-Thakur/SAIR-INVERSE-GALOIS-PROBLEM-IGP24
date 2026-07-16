# ==============================================================================
# File: compiler.py
# Description: Aggregates candidate polynomials into the strict 1000-line submission limit.
# Tech Stack: Python 3.10+
# ==============================================================================

import os
import sys

# Add parent directory to path to import verifier
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evaluation.verifier import verify_polynomial_line

def compile_submission(candidate_dir: str, output_file: str = "submission.txt", max_lines: int = 1000):
    """
    Scans a directory for valid polynomial strings, verifies their strict formatting,
    and aggregates them into the final submission payload, strictly capping at max_lines.
    
    Args:
        candidate_dir: Directory containing raw .txt outputs from search scripts.
        output_file: Final compiled payload.
        max_lines: The SAIR server daily submission limit.
    """
    if not os.path.isdir(candidate_dir):
        print(f"Error: {candidate_dir} is not a valid directory.")
        return

    compiled_count = 0
    
    with open(output_file, 'w') as out_f:
        for filename in os.listdir(candidate_dir):
            if not filename.endswith(".txt"):
                continue
                
            filepath = os.path.join(candidate_dir, filename)
            with open(filepath, 'r') as in_f:
                for line in in_f:
                    line = line.strip()
                    if verify_polynomial_line(line):
                        out_f.write(line + "\n")
                        compiled_count += 1
                        
                        if compiled_count >= max_lines:
                            print(f"Submission limit reached ({max_lines} lines). Compilation halted.")
                            return compiled_count
                            
    print(f"Compilation complete. {compiled_count} valid lines written to {output_file}.")
    return compiled_count

if __name__ == "__main__":
    # Example execution
    os.makedirs("candidates", exist_ok=True)
    compile_submission("candidates")
