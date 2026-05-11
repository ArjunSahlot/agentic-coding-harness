# Maintainer Context

This reference file exists to make the benchmark more realistic for
context-management experiments. It contains useful details, historical
regressions, and non-goals. Not every paragraph maps directly to one test,
and some information is intentionally redundant with the README and tests.

## Task

- Id: `semver_resolver`
- Title: Semver Resolver
- Tags: semver, sorting, constraints
- Estimated context target: 13100 tokens

## Working Style

The preferred solution is small, deterministic, and easy to verify with the
standard-library unittest suite. The benchmark rewards fixes that preserve
the documented public API and make the implementation easier to reason
about. It does not reward adding external packages, shelling out to
platform-specific tools, or changing tests to match the broken behavior.

## Historical Scenarios


        ### Scenario 1: numeric ordering

        Package feeds are strings, but SemVer components are numbers. Versions like 1.10.0 must sort after 1.9.9 even though lexical ordering says otherwise.

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

        ### Scenario 2: yanked releases

        A yanked release can stay visible for lockfile reproducibility, but new resolution should skip it unless a future policy explicitly pins it. The current resolver never pins yanked versions.

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

        ### Scenario 3: caret ranges

        Caret ranges are common in ecosystem manifests. The allowed upper bound is sensitive to leading zero components, so 0.2.x and 0.0.x behave differently from 1.x.

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

        ### Scenario 4: pre-release opt-in

        Release candidates should not appear in ordinary stable ranges. They become eligible only when a constraint operand itself mentions a pre-release version.

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

        ### Scenario 5: highest satisfying candidate

        Resolution should evaluate all constraints first, then choose the maximum SemVer candidate. Early return behavior can pick a lower version by accident.

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


        ### Context Slice 1: numeric ordering

        Background signal: Package feeds are strings, but SemVer components are numbers. Versions like 1.10.0 must sort after 1.9.9 even though lexical ordering says otherwise. In previous reviews, this kind
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
        `numeric ordering` without growing unrelated code paths.

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

        ### Context Slice 2: yanked releases

        Background signal: A yanked release can stay visible for lockfile reproducibility, but new resolution should skip it unless a future policy explicitly pins it. The current resolver never pins yanked versions. In previous reviews, this kind
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
        `yanked releases` without growing unrelated code paths.

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

        ### Context Slice 3: caret ranges

        Background signal: Caret ranges are common in ecosystem manifests. The allowed upper bound is sensitive to leading zero components, so 0.2.x and 0.0.x behave differently from 1.x. In previous reviews, this kind
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
        `caret ranges` without growing unrelated code paths.

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

        ### Context Slice 4: pre-release opt-in

        Background signal: Release candidates should not appear in ordinary stable ranges. They become eligible only when a constraint operand itself mentions a pre-release version. In previous reviews, this kind
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
        `pre-release opt-in` without growing unrelated code paths.

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

        ### Context Slice 5: highest satisfying candidate

        Background signal: Resolution should evaluate all constraints first, then choose the maximum SemVer candidate. Early return behavior can pick a lower version by accident. In previous reviews, this kind
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
        `highest satisfying candidate` without growing unrelated code paths.

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
