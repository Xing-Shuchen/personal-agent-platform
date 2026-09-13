# Output contract

Return one bare `historian.period-summary.v1` JSON object. The supplied
summary ID, revision, period, and ContextPack are fixed. `basis_refs` may only
name the ContextPack or selected ContextPack artifacts. Preserve coverage gaps
and contradictions. Do not include prose outside the JSON object.
