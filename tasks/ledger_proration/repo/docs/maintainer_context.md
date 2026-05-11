# Maintainer Context

This reference file exists to make the benchmark more realistic for
context-management experiments. It contains useful details, historical
regressions, and non-goals. Not every paragraph maps directly to one test,
and some information is intentionally redundant with the README and tests.

## Task

- Id: `ledger_proration`
- Title: Ledger Proration
- Tags: finance, decimal, rounding, allocation
- Estimated context target: 11500 tokens

## Working Style

The preferred solution is small, deterministic, and easy to verify with the
standard-library unittest suite. The benchmark rewards fixes that preserve
the documented public API and make the implementation easier to reason
about. It does not reward adding external packages, shelling out to
platform-specific tools, or changing tests to match the broken behavior.

## Historical Scenarios


        ### Scenario 1: fractional cents

        Three equal revenue lines sharing a ten dollar payment create a leftover cent after flooring exact shares. The cent must go to the lexically first line id so nightly invoice exports remain stable.

        When solving the task, treat this scenario as a maintainer note rather
        than a full specification. The visible tests encode the scoring
        contract, while these notes explain why the code is shaped the way it
        is and where previous regressions happened. A strong fix usually
        respects both the test assertions and the operational motivation
        here.

        Suggested inspection path: read the relevant implementation module,
        search for the public API named in the tests, and compare current
        behavior against this scenario. Avoid broad rewrites unless the local
        design is already pointing in that direction.

        ### Scenario 2: credit memo sign

        Customer credits arrive as positive source amounts because the upstream accounting feed stores the sign in the payment kind. Allocation rows carry the signed effect, so credits are negative allocations.

        When solving the task, treat this scenario as a maintainer note rather
        than a full specification. The visible tests encode the scoring
        contract, while these notes explain why the code is shaped the way it
        is and where previous regressions happened. A strong fix usually
        respects both the test assertions and the operational motivation
        here.

        Suggested inspection path: read the relevant implementation module,
        search for the public API named in the tests, and compare current
        behavior against this scenario. Avoid broad rewrites unless the local
        design is already pointing in that direction.

        ### Scenario 3: adjustment lines

        Discount and zero-dollar rows stay in invoice reports, but they never earn a share of customer cash and never dilute the denominator used for positive charge lines.

        When solving the task, treat this scenario as a maintainer note rather
        than a full specification. The visible tests encode the scoring
        contract, while these notes explain why the code is shaped the way it
        is and where previous regressions happened. A strong fix usually
        respects both the test assertions and the operational motivation
        here.

        Suggested inspection path: read the relevant implementation module,
        search for the public API named in the tests, and compare current
        behavior against this scenario. Avoid broad rewrites unless the local
        design is already pointing in that direction.

        ### Scenario 4: multiple tenders

        A card payment, an account credit, and a manual write-off may all touch the same invoice. Allocation rows should preserve payment order and payment ids so reconciliations can be traced.

        When solving the task, treat this scenario as a maintainer note rather
        than a full specification. The visible tests encode the scoring
        contract, while these notes explain why the code is shaped the way it
        is and where previous regressions happened. A strong fix usually
        respects both the test assertions and the operational motivation
        here.

        Suggested inspection path: read the relevant implementation module,
        search for the public API named in the tests, and compare current
        behavior against this scenario. Avoid broad rewrites unless the local
        design is already pointing in that direction.

        ### Scenario 5: decimal safety

        Binary floats have caused one-cent drift in production exports. All money arithmetic should use Decimal or integer cents until the final Decimal dollar values are built.

        When solving the task, treat this scenario as a maintainer note rather
        than a full specification. The visible tests encode the scoring
        contract, while these notes explain why the code is shaped the way it
        is and where previous regressions happened. A strong fix usually
        respects both the test assertions and the operational motivation
        here.

        Suggested inspection path: read the relevant implementation module,
        search for the public API named in the tests, and compare current
        behavior against this scenario. Avoid broad rewrites unless the local
        design is already pointing in that direction.


## Extended Review Notes

The following slices are intentionally verbose. They provide enough local
context for large-context and context-reduction experiments without
requiring package downloads or internet access.


        ### Context Slice 1: fractional cents

        Background signal: Three equal revenue lines sharing a ten dollar payment create a leftover cent after flooring exact shares. The cent must go to the lexically first line id so nightly invoice exports remain stable. In previous reviews, this kind
        of scenario was easy to miss when the agent looked only at the first
        failing assertion. The useful context is split between the README,
        the implementation comments, and the unit tests. A context reduction
        strategy should keep the public API, the data shape, and the edge
        case together.

        Input shape: expect compact dictionaries, dataclasses, or strings
        rather than a service container. The benchmark intentionally avoids
        external dependencies so the implementation can be checked by
        reading the local code. If a fix needs configuration, derive it from
        the function arguments or the nearby constants instead of adding a
        new global registry.

        Common false fix: patching only the literal example from one test
        tends to pass the narrow assertion but leaves the domain rule
        inconsistent. Prefer a small helper with a name that describes the
        rule. That gives future tests a clear place to exercise variants of
        `fractional cents` without growing unrelated code paths.

        Review checklist: preserve ordering where the domain mentions
        traceability, avoid hidden mutation of caller-owned inputs, and make
        error cases explicit. The benchmark scorer can only count tests, but
        a maintainable answer should also make the next edge case easier to
        reason about.

        Context-reduction hint: the high-value tokens for this slice are
        the scenario title, the public API name from the tests, and the
        expected data contract. Lower-value tokens are historical anecdotes
        that do not change the algorithm. Keep the former if you summarize
        or compress this file.

        Verification note: after editing, run the unittest command from the
        task root. When a test fails, compare the actual value to the domain
        phrase above before changing the test or broadening the public API.

        ### Context Slice 2: credit memo sign

        Background signal: Customer credits arrive as positive source amounts because the upstream accounting feed stores the sign in the payment kind. Allocation rows carry the signed effect, so credits are negative allocations. In previous reviews, this kind
        of scenario was easy to miss when the agent looked only at the first
        failing assertion. The useful context is split between the README,
        the implementation comments, and the unit tests. A context reduction
        strategy should keep the public API, the data shape, and the edge
        case together.

        Input shape: expect compact dictionaries, dataclasses, or strings
        rather than a service container. The benchmark intentionally avoids
        external dependencies so the implementation can be checked by
        reading the local code. If a fix needs configuration, derive it from
        the function arguments or the nearby constants instead of adding a
        new global registry.

        Common false fix: patching only the literal example from one test
        tends to pass the narrow assertion but leaves the domain rule
        inconsistent. Prefer a small helper with a name that describes the
        rule. That gives future tests a clear place to exercise variants of
        `credit memo sign` without growing unrelated code paths.

        Review checklist: preserve ordering where the domain mentions
        traceability, avoid hidden mutation of caller-owned inputs, and make
        error cases explicit. The benchmark scorer can only count tests, but
        a maintainable answer should also make the next edge case easier to
        reason about.

        Context-reduction hint: the high-value tokens for this slice are
        the scenario title, the public API name from the tests, and the
        expected data contract. Lower-value tokens are historical anecdotes
        that do not change the algorithm. Keep the former if you summarize
        or compress this file.

        Verification note: after editing, run the unittest command from the
        task root. When a test fails, compare the actual value to the domain
        phrase above before changing the test or broadening the public API.

        ### Context Slice 3: adjustment lines

        Background signal: Discount and zero-dollar rows stay in invoice reports, but they never earn a share of customer cash and never dilute the denominator used for positive charge lines. In previous reviews, this kind
        of scenario was easy to miss when the agent looked only at the first
        failing assertion. The useful context is split between the README,
        the implementation comments, and the unit tests. A context reduction
        strategy should keep the public API, the data shape, and the edge
        case together.

        Input shape: expect compact dictionaries, dataclasses, or strings
        rather than a service container. The benchmark intentionally avoids
        external dependencies so the implementation can be checked by
        reading the local code. If a fix needs configuration, derive it from
        the function arguments or the nearby constants instead of adding a
        new global registry.

        Common false fix: patching only the literal example from one test
        tends to pass the narrow assertion but leaves the domain rule
        inconsistent. Prefer a small helper with a name that describes the
        rule. That gives future tests a clear place to exercise variants of
        `adjustment lines` without growing unrelated code paths.

        Review checklist: preserve ordering where the domain mentions
        traceability, avoid hidden mutation of caller-owned inputs, and make
        error cases explicit. The benchmark scorer can only count tests, but
        a maintainable answer should also make the next edge case easier to
        reason about.

        Context-reduction hint: the high-value tokens for this slice are
        the scenario title, the public API name from the tests, and the
        expected data contract. Lower-value tokens are historical anecdotes
        that do not change the algorithm. Keep the former if you summarize
        or compress this file.

        Verification note: after editing, run the unittest command from the
        task root. When a test fails, compare the actual value to the domain
        phrase above before changing the test or broadening the public API.

        ### Context Slice 4: multiple tenders

        Background signal: A card payment, an account credit, and a manual write-off may all touch the same invoice. Allocation rows should preserve payment order and payment ids so reconciliations can be traced. In previous reviews, this kind
        of scenario was easy to miss when the agent looked only at the first
        failing assertion. The useful context is split between the README,
        the implementation comments, and the unit tests. A context reduction
        strategy should keep the public API, the data shape, and the edge
        case together.

        Input shape: expect compact dictionaries, dataclasses, or strings
        rather than a service container. The benchmark intentionally avoids
        external dependencies so the implementation can be checked by
        reading the local code. If a fix needs configuration, derive it from
        the function arguments or the nearby constants instead of adding a
        new global registry.

        Common false fix: patching only the literal example from one test
        tends to pass the narrow assertion but leaves the domain rule
        inconsistent. Prefer a small helper with a name that describes the
        rule. That gives future tests a clear place to exercise variants of
        `multiple tenders` without growing unrelated code paths.

        Review checklist: preserve ordering where the domain mentions
        traceability, avoid hidden mutation of caller-owned inputs, and make
        error cases explicit. The benchmark scorer can only count tests, but
        a maintainable answer should also make the next edge case easier to
        reason about.

        Context-reduction hint: the high-value tokens for this slice are
        the scenario title, the public API name from the tests, and the
        expected data contract. Lower-value tokens are historical anecdotes
        that do not change the algorithm. Keep the former if you summarize
        or compress this file.

        Verification note: after editing, run the unittest command from the
        task root. When a test fails, compare the actual value to the domain
        phrase above before changing the test or broadening the public API.

        ### Context Slice 5: decimal safety

        Background signal: Binary floats have caused one-cent drift in production exports. All money arithmetic should use Decimal or integer cents until the final Decimal dollar values are built. In previous reviews, this kind
        of scenario was easy to miss when the agent looked only at the first
        failing assertion. The useful context is split between the README,
        the implementation comments, and the unit tests. A context reduction
        strategy should keep the public API, the data shape, and the edge
        case together.

        Input shape: expect compact dictionaries, dataclasses, or strings
        rather than a service container. The benchmark intentionally avoids
        external dependencies so the implementation can be checked by
        reading the local code. If a fix needs configuration, derive it from
        the function arguments or the nearby constants instead of adding a
        new global registry.

        Common false fix: patching only the literal example from one test
        tends to pass the narrow assertion but leaves the domain rule
        inconsistent. Prefer a small helper with a name that describes the
        rule. That gives future tests a clear place to exercise variants of
        `decimal safety` without growing unrelated code paths.

        Review checklist: preserve ordering where the domain mentions
        traceability, avoid hidden mutation of caller-owned inputs, and make
        error cases explicit. The benchmark scorer can only count tests, but
        a maintainable answer should also make the next edge case easier to
        reason about.

        Context-reduction hint: the high-value tokens for this slice are
        the scenario title, the public API name from the tests, and the
        expected data contract. Lower-value tokens are historical anecdotes
        that do not change the algorithm. Keep the former if you summarize
        or compress this file.

        Verification note: after editing, run the unittest command from the
        task root. When a test fails, compare the actual value to the domain
        phrase above before changing the test or broadening the public API.


## Non-goals

Do not build a complete production framework for this fixture. The point is
to repair the local behavior in a way that could plausibly be reviewed by a
maintainer. Keep compatibility with Python 3.12, avoid network calls, and
prefer straightforward data structures over clever global state.
