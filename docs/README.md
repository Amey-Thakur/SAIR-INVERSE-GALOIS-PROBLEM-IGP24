<div align="center">

# Documentation

**The rules, the mathematics, and the strategies that follow from both.**

[Back to the repository](../README.md) &nbsp;·&nbsp;
[Pipeline](../scripts/README.md) &nbsp;·&nbsp;
[Submitting](../SUBMISSION.md) &nbsp;·&nbsp;
[Competition](https://competition.sair.foundation/competitions/igp24/overview)

</div>

---

| Document | What it answers |
| :--- | :--- |
| [competition_rules.md](competition_rules.md) | The submission format, the limits, how verification and discriminant computation work, and what counts as a scoreable pair |
| [mathematical_background.md](mathematical_background.md) | The inverse Galois problem, transitive groups of degree 24, signatures, discriminants, and what Shafarevich does and does not give |
| [search_strategies.md](search_strategies.md) | The constructions available for realising groups, and which of them are practical without a computer algebra licence |

<br>

## The three facts everything else follows from

**The surface is enormous and the known part is tiny.** There are 25,000
transitive groups of degree 24 and 165,836 possible `(24Tt, r)` pairs. The
frozen baseline covers 622 of them.

**Scoring is exponential in crowding.** A pair is worth `2^(1−k)` adjusted
mildly by discriminant, where `k` counts the teams holding it. Ten teams on a
pair leaves each with about two thousandths of a point. Rarity is the whole
game.

**The label cannot be computed here.** Magma settles it. Everything in
[`../scripts/`](../scripts/README.md) is built around predicting cheaply,
submitting, and learning from what comes back.

<br>

## What the search actually met

The strategies in `search_strategies.md` were all implemented, and the outcome
is recorded plainly in the [root README](../README.md) under *What was learned*.
The short version: the constructions available without Magma reach groups that
other teams reach too, and the pairs still unclaimed sit on groups these methods
do not produce.

> [!NOTE]
> That is a result rather than a failure, and it is the most reusable thing in
> this repository. Anyone attempting degree 24 with fingerprinting and PARI/GP
> alone can expect the same ceiling, and can plan around it instead of
> rediscovering it.

**[Back to the repository](../README.md)** &nbsp;·&nbsp;
**[On to the pipeline](../scripts/README.md)**
