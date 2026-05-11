# Maintainer Context

This reference file exists to make the benchmark more realistic for
context-management experiments. It contains useful details, historical
regressions, and non-goals. Not every paragraph maps directly to one test,
and some information is intentionally redundant with the README and tests.

## Task

- Id: `log_window_rollups`
- Title: Log Window Rollups
- Tags: logs, datetime, aggregation
- Estimated context target: 10900 tokens

## Working Style

The preferred solution is small, deterministic, and easy to verify with the
standard-library unittest suite. The benchmark rewards fixes that preserve
the documented public API and make the implementation easier to reason
about. It does not reward adding external packages, shelling out to
platform-specific tools, or changing tests to match the broken behavior.

## Historical Scenarios


        ### Scenario 1: UTC buckets

        The log stream uses Z timestamps. Bucketing should be timezone-aware and then rendered back to a Z suffix so dashboard snapshots are portable across developer machines.

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

        ### Scenario 2: exclusive ends

        Window boundaries are start-inclusive and end-exclusive. A record exactly on the minute belongs to that minute's bucket, which avoids double counting during incremental refreshes.

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

        ### Scenario 3: empty gaps

        Charts need explicit empty windows between observed buckets. Missing rows make line charts visually compress outages and make alert backtests harder to compare.

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

        ### Scenario 4: severity threshold

        Filtering by minimum severity should use the ordering DEBUG, INFO, WARNING, ERROR, CRITICAL. String comparison is not a valid substitute.

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

        ### Scenario 5: group keys

        The dashboard flattens group dimensions into pipe-joined strings. Missing dimensions should become empty strings rather than crashing the rollup.

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


        ### Context Slice 1: UTC buckets

        Background signal: The log stream uses Z timestamps. Bucketing should be timezone-aware and then rendered back to a Z suffix so dashboard snapshots are portable across developer machines. In previous reviews, this kind
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
        `UTC buckets` without growing unrelated code paths.

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

        ### Context Slice 2: exclusive ends

        Background signal: Window boundaries are start-inclusive and end-exclusive. A record exactly on the minute belongs to that minute's bucket, which avoids double counting during incremental refreshes. In previous reviews, this kind
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
        `exclusive ends` without growing unrelated code paths.

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

        ### Context Slice 3: empty gaps

        Background signal: Charts need explicit empty windows between observed buckets. Missing rows make line charts visually compress outages and make alert backtests harder to compare. In previous reviews, this kind
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
        `empty gaps` without growing unrelated code paths.

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

        ### Context Slice 4: severity threshold

        Background signal: Filtering by minimum severity should use the ordering DEBUG, INFO, WARNING, ERROR, CRITICAL. String comparison is not a valid substitute. In previous reviews, this kind
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
        `severity threshold` without growing unrelated code paths.

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

        ### Context Slice 5: group keys

        Background signal: The dashboard flattens group dimensions into pipe-joined strings. Missing dimensions should become empty strings rather than crashing the rollup. In previous reviews, this kind
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
        `group keys` without growing unrelated code paths.

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
