# Converge acceptance target

This file exists only on the `converge-acceptance` test line. The branch is an isolated external target
for validating Converge's document-driven autonomous workflow and must not be treated as the production
`main` branch of this training repository.

The acceptance baseline intentionally contains a small deterministic `shared_tools.fake_terminal` test
surface and an `Acceptance CI` pull-request workflow. Requirements used by Converge remain outside this
repository and are frozen separately before the live acceptance run.

Changes produced by the live acceptance exercise are expected to merge only into
`converge-acceptance`. They are release-test evidence for Converge, not a development plan for
`mas-training-ground/main`.
