# Competition Mechanics and Scoring Rules

This document outlines the strict evaluation boundaries, scoring mechanics, and submission protocols for the SAIR IGP24 (Inverse Galois Problem, Degree 24) challenge.

## Objective

The core objective is to discover monic, irreducible integer polynomials of degree 24 that realize specific transitive permutation groups ($24T_1 \dots 24T_{25000}$) with specific numbers of real roots ($r$).

## Scoring Formula

Points are awarded dynamically based on rarity and mathematical optimization. For each unique $(24T_t, r)$ pair:

$$ \text{Points} = 2^{1-k} \cdot \frac{\log D_0}{\log D} $$

- $k$: The number of distinct teams that have discovered a valid polynomial for this pair.
- $D$: Your best (smallest) official absolute scoring discriminant for this pair.
- $D_0$: The global baseline (the smallest discriminant found by any team for this pair).

**Key Takeaway**: Points decay exponentially as more teams discover a group. Optimizing the discriminant $D$ offers a logarithmic score multiplier.

## Discriminant Evaluation Protocol

The evaluation server relies on PARI/GP for exact field calculations.

### Exact Discriminant (`nfdisc`)
The system attempts to compute the absolute number-field discriminant using PARI/GP's `nfdisc` function, bound by a strict 60-second execution timeout. If successful, this exact discriminant $D$ is recorded.

### Mixed Discriminant (Fallback)
If `nfdisc` times out, a fallback "mixed discriminant" is calculated using prime bounds. 

> [!WARNING]
> Mixed discriminants cannot be used to break existing exact discriminant baselines. If a baseline $D_0$ is exact, you must submit a polynomial that yields a strictly smaller exact `nfdisc` within the 60-second timeout to claim the optimization multiplier.

## Submission Constraints

Submissions must adhere to a strict structural contract:

1. **Format**: A plain text file where each line represents a single polynomial.
2. **Coefficient Order**: 25 comma-separated integers in ascending powers ($a_0, a_1, \dots, a_{24}$).
3. **Monic Requirement**: The leading coefficient must be strictly $a_{24} = 1$.
4. **Irreducibility**: $a_0 \neq 0$.
5. **Volume Limits**: 
   - Initial threshold: 5 submissions per day.
   - Unlocked threshold: 1,000 lines per day (unlocked after successfully discovering 5 distinct $(24T_t, r)$ pairs).

## Tie-Breaking

If a single submission file contains multiple valid polynomials that map to the exact same $(24T_t, r)$ pair, the evaluation server strictly accepts only the first verified polynomial based on line order. Subsequent redundant lines are discarded.
