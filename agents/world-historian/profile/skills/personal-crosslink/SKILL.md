---
name: personal-crosslink
description: Link already-public Chronicle events inward to read-only personal history while enforcing a one-way privacy boundary.
---

# Cross-link world history to personal history

Before doing this work, read
[references/privacy-boundary.md](references/privacy-boundary.md) and enforce it
as a hard boundary.

Begin with public events already present in the Chronicle. Use their public
entities, time windows, and concepts to retrieve relevant personal event or
observation IDs through the approved read-only personal-history interface.
Create `PersonalLink` records only when evidence supports a named relation and
an inspectable explanation.

Do not copy private source text into the world database. Store only the minimum
personal record IDs and evidence needed for the link. This is a background job;
read [the PersonalLink bundle fields](references/personal-link-bundle.md),
persist links, and finish with exactly `[SILENT]`.
