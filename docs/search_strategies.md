# Search Strategies and Algebraic Constructions

This document details the primary computational and mathematical search vectors for identifying new $(24T_t, r)$ realizations and optimizing their discriminants.

## 1. Brute Force and Heuristic Search

For groups with small minimal discriminants (typically small solvable groups), bounded exhaustive searches over integer coefficients are viable.

- **Coefficient Bounding**: Restrict the coefficient space $a_0 \dots a_{23}$ to $[-B, B]$.
- **Local Optimization**: Given a valid polynomial for $24T_t$, apply heuristic perturbations (e.g., small shifts or targeted lattice reductions) to minimize the discriminant without breaking the Galois group structure.
- **Filtering**: Before executing costly Galois group computations in PARI/GP, filter candidates aggressively by checking their factorization patterns modulo small primes (Frobenius elements).

## 2. Algebraic Constructions and Specialization

For non-solvable groups or complex solvable structures, brute force is computationally impossible. We rely on algebraic geometry and generic polynomials.

### Generic Polynomials
If a generic polynomial $P(t, x)$ over $\mathbb{Q}(t)$ has Galois group $G$, the Hilbert Irreducibility Theorem states that $P(t_0, x)$ will have Galois group $G$ for "most" rational specializations $t_0 \in \mathbb{Q}$.

1. Identify or construct generic polynomials for degree 24 subgroups.
2. Sweep $t_0$ across a targeted rational grid.
3. Compute the discriminant for each specialized polynomial.
4. Keep the specialization that minimizes the number-field discriminant.

### Subfield Constructions
Many transitive groups of degree 24 can be constructed as extensions of smaller fields (e.g., a degree 4 extension over a degree 6 base field). 
By carefully selecting base fields with very small discriminants and engineering the extension polynomials, the composite degree 24 field's discriminant can be strictly controlled.

## 3. Discriminant Minimization Tactics

To maximize the SAIR score multiplier $\left( \frac{\log D_0}{\log D} \right)$:

1. **Target Ramification**: Minimize the primes that ramify in the field. Construct polynomials such that their polynomial discriminants have very few, very small prime factors.
2. **Polredabs**: Use PARI/GP's `polredabs` function. While `polredabs` does not change the number-field discriminant, it produces a "simpler" polynomial for the same field, which often executes much faster in the `nfdisc` evaluation timeout window (60 seconds).

> [!TIP]
> Always run `polredabs` on a discovered polynomial before submission. A massive polynomial that correctly realizes a group might trigger the 60-second timeout, forcing the server to fall back to the mixed discriminant and costing you the exact discriminant multiplier.
