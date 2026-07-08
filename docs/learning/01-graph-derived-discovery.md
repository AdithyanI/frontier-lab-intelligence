# Graph-derived Discovery

**Where we used it:** `src/fli/digg.py` turns Digg rankings and top-follower
rows into candidate people and `follows`-style edges.

**The problem it solves here:** A hand-written list of famous AI people misses
the layer below obvious leaders. A raw follower list is too big and noisy.
Graph-derived discovery starts from who the AI/tech community already pays
attention to, then gives us candidates to validate.

**How it works:** Treat each account as a node and each Digg top-follower row
as an edge. If Yann LeCun, Ian Goodfellow, and Chris Olah appear as top
followers for Karpathy, that is evidence that Karpathy sits near the center of
the technical AI graph. We do not promote anyone automatically; the graph only
decides who deserves review first.

**Why we chose it over alternatives:** X API full follower extraction is
expensive and mostly noise. X lists are useful but hard to export completely.
Digg already precomputes a smaller graph signal from roughly 9 million follow
relationships, so it is the cheapest first discovery layer.

**If asked about this at the on-site:** "I used Digg as a graph-derived
candidate generator. It gives ranked AI accounts and top-follower edges, which
is a better starting point than scraping millions of raw followers. Then I
validate candidates against primary sources before they enter the registry."
