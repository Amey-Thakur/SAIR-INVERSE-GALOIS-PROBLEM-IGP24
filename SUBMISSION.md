<!--
  File: SUBMISSION.md
  Purpose: How submission.txt is built, checked, and sent to the evaluator.
-->

# Submitting to IGP24

The ready artifact is [`submission.txt`](./submission.txt): 847 degree 24
monic irreducible polynomials, one per line, coefficients `a_0,...,a_24` in
ascending powers, 64 KB (well under the 1,000,000 byte and 1,000 line
limits).

## How it was built

```
py scripts/generate_submission.py   # writes submission.txt
py scripts/validate_submission.py   # independent gate, must print PASS
```

`generate_submission.py` draws only from constructions that reach rare, low
index transitive groups, since dense random polynomials collapse into S24 or
A24 that every team already holds:

- **Cyclotomic abelian fields**: the polynomials of Q(zeta_n) with
  phi(n) = 24. Small discriminant, totally complex, rare abelian groups.
- **Compositions** f(g(x)) with deg f times deg g = 24, including nested
  chains like 2x2x2x3. These realize imprimitive groups whose block systems
  follow the chain, the deepest well of distinct degree 24 labels.
- **Sparse trinomials** x^24 + a x^b + c, spread across many middle terms,
  to reach primitive and large groups cheaply.

`validate_submission.py` re-parses the file exactly as the official evaluator
does and re-derives every constraint from scratch: 25 integer coefficients
before any trailing comment, monic, nonzero constant term, coefficient gcd 1,
irreducible over Q, no duplicate field, valid `poly_disc_primes` hints, and
the byte ceiling. No line ships unless this script re-confirms it.

The `24Tt` Galois label and real root count `r` are computed by the official
Magma verifier, not here, so nothing in this repository claims a group it
cannot prove.

## Sending it

**Website.** Open the IGP24 competition page, choose **Submit Submission**,
upload `submission.txt` (or paste its lines), and add the provenance note
below.

**API** (same rate limits, any team member):

```
curl -X POST "https://api.sair.foundation/api/public/v1/competitions/igp24/submissions" \
  -H "Authorization: Bearer $SAIR_API_KEY" \
  -H "Content-Type: application/json" \
  --data-binary @scripts/api_payload.json
```

`scripts/build_api_payload.py` turns `submission.txt` into `api_payload.json`
in the shape the API expects (`{"payload":{"polynomials":[...]}}`).

## Provenance note for the form

> All polynomials are degree 24 monic irreducible over Q, generated
> reproducibly by scripts/generate_submission.py and independently checked by
> scripts/validate_submission.py in this repository. Constructions: cyclotomic
> fields Phi_n with phi(n)=24, polynomial compositions f(g(x)) with deg product
> 24, and sparse trinomials. No coefficients were copied from external tables.

## Rate limits

Each team starts at 5 submissions per day. After 5 distinct scoreable
`(24Tt, r)` pairs, the cap rises to 1,000 per day. Each upload is one
submission regardless of how many polynomials it carries, so send the whole
file at once.
