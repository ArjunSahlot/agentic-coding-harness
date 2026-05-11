# Maintainer Context

This reference file exists to make the benchmark more realistic for
context-management experiments. It contains useful details, historical
regressions, and non-goals. Not every paragraph maps directly to one test,
and some information is intentionally redundant with the README and tests.

## Task

- Id: `template_engine`
- Title: Mini Template Engine
- Tags: templating, parser, escaping
- Estimated context target: 14400 tokens

## Working Style

The preferred solution is small, deterministic, and easy to verify with the
standard-library unittest suite. The benchmark rewards fixes that preserve
the documented public API and make the implementation easier to reason
about. It does not reward adding external packages, shelling out to
platform-specific tools, or changing tests to match the broken behavior.

## Historical Scenarios


        ### Scenario 1: default escaping

        Templates render into HTML emails. Variables must be escaped by default so user-provided names and titles cannot inject markup.

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

        ### Scenario 2: safe values

        Some snippets are pre-rendered by trusted code. The safe filter is the explicit escape hatch and should not leak to unrelated variables.

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

        ### Scenario 3: loop context

        Simple receipt templates need a loop variable and loop.index for numbering. The implementation should create a child context per iteration instead of mutating shared caller state permanently.

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

        ### Scenario 4: conditionals

        If/else blocks only need dotted truthy lookup. Avoid eval or arbitrary Python expressions; deterministic lookup is enough for the benchmark.

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

        ### Scenario 5: filters with arguments

        The default filter receives a quoted string argument. Missing values and None should use it, while present falsey values such as 0 may still be meaningful.

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


        ### Context Slice 1: default escaping

        Background signal: Templates render into HTML emails. Variables must be escaped by default so user-provided names and titles cannot inject markup. In previous reviews, this kind
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
        `default escaping` without growing unrelated code paths.

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

        ### Context Slice 2: safe values

        Background signal: Some snippets are pre-rendered by trusted code. The safe filter is the explicit escape hatch and should not leak to unrelated variables. In previous reviews, this kind
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
        `safe values` without growing unrelated code paths.

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

        ### Context Slice 3: loop context

        Background signal: Simple receipt templates need a loop variable and loop.index for numbering. The implementation should create a child context per iteration instead of mutating shared caller state permanently. In previous reviews, this kind
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
        `loop context` without growing unrelated code paths.

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

        ### Context Slice 4: conditionals

        Background signal: If/else blocks only need dotted truthy lookup. Avoid eval or arbitrary Python expressions; deterministic lookup is enough for the benchmark. In previous reviews, this kind
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
        `conditionals` without growing unrelated code paths.

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

        ### Context Slice 5: filters with arguments

        Background signal: The default filter receives a quoted string argument. Missing values and None should use it, while present falsey values such as 0 may still be meaningful. In previous reviews, this kind
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
        `filters with arguments` without growing unrelated code paths.

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
