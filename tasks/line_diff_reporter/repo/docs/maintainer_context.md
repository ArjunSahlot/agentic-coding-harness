# Maintainer Context

This reference file exists to make the benchmark more realistic for
context-management experiments. It contains useful details, historical
regressions, and non-goals. Not every paragraph maps directly to one test,
and some information is intentionally redundant with the README and tests.

## Task

- Id: `line_diff_reporter`
- Title: Line Diff Reporter
- Tags: diff, text, reporting
- Estimated context target: 10800 tokens

## Working Style

The preferred solution is small, deterministic, and easy to verify with the
standard-library unittest suite. The benchmark rewards fixes that preserve
the documented public API and make the implementation easier to reason
about. It does not reward adding external packages, shelling out to
platform-specific tools, or changing tests to match the broken behavior.

## Historical Scenarios


        ### Scenario 1: whitespace mode

        Reviewers sometimes ask for semantic diffs that ignore formatting churn. Comparison can normalize whitespace, but displayed hunk lines should remain original text.

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

        ### Scenario 2: one based starts

        Editor integrations use one-based line numbers. Raw SequenceMatcher indexes are zero-based, so hunk starts need adjustment after context expansion.

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

        ### Scenario 3: context expansion

        Each change should include nearby equal lines on both old and new sides. Context helps reviewers understand a compact hunk without opening the full file.

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

        ### Scenario 4: merged windows

        Two changes close together should appear as one hunk when their context overlaps. Separate overlapping hunks duplicate lines and confuse review comments.

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

        ### Scenario 5: insertions and deletions

        The same hunk format should support replacements, insertions, and deletions by allowing either side's line list to be empty after context is considered.

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


        ### Context Slice 1: whitespace mode

        Background signal: Reviewers sometimes ask for semantic diffs that ignore formatting churn. Comparison can normalize whitespace, but displayed hunk lines should remain original text. In previous reviews, this kind
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
        `whitespace mode` without growing unrelated code paths.

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

        ### Context Slice 2: one based starts

        Background signal: Editor integrations use one-based line numbers. Raw SequenceMatcher indexes are zero-based, so hunk starts need adjustment after context expansion. In previous reviews, this kind
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
        `one based starts` without growing unrelated code paths.

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

        ### Context Slice 3: context expansion

        Background signal: Each change should include nearby equal lines on both old and new sides. Context helps reviewers understand a compact hunk without opening the full file. In previous reviews, this kind
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
        `context expansion` without growing unrelated code paths.

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

        ### Context Slice 4: merged windows

        Background signal: Two changes close together should appear as one hunk when their context overlaps. Separate overlapping hunks duplicate lines and confuse review comments. In previous reviews, this kind
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
        `merged windows` without growing unrelated code paths.

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

        ### Context Slice 5: insertions and deletions

        Background signal: The same hunk format should support replacements, insertions, and deletions by allowing either side's line list to be empty after context is considered. In previous reviews, this kind
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
        `insertions and deletions` without growing unrelated code paths.

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
