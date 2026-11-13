# Discoverability and independent adoption

**Status (2026-11-14):** GitHub releases `v0.1.0`, `v0.1.1` and `v0.1.2` exist, but
the repository has no verified independent installation, downstream CI usage,
or external feedback. A GitHub Marketplace listing and PyPI availability
have **not** been verified. This is a preparation plan, not a report of adoption.

## GitHub repository About (requires repository-settings access)

Suggested description (copy into **About → Edit**):

> Check Python sdist-to-wheel Core Metadata consistency (PEP 643) in CI. Dependency-free Python CLI and GitHub Action.

Suggested GitHub topics: `python`, `python-packaging`, `github-action`,
`sdist`, `wheel`, `metadata`, `pep-643`, `continuous-integration`.

This is an optional one-time repository owner step. We cannot mark it complete
from a README edit, GitHub CI result or absence of an error.

## Publish the composite Action in GitHub Marketplace

Source of truth: [GitHub's Marketplace publication instructions](https://docs.github.com/en/actions/how-tos/create-and-publish-actions/publish-in-github-marketplace).

The repository already has a public root-level `action.yml` with `name`,
`description` and `branding`, plus tagged GitHub releases and a passing
[tagged Action smoke test](https://github.com/swiast/dist-parity/actions/runs/43484099851).

Publication still requires account-level operations and verification:

1. Check that the Action name **dist-parity** is available in Marketplace;
   uniqueness cannot be inferred from the repository name.
2. Sign in as the GitHub repository owner, accept the **GitHub Marketplace
   Developer Agreement** if needed, and use an account with two-factor
   authentication.
3. Open `action.yml` in GitHub and use the Marketplace publication prompt
   to draft an **Action release**. Select **Publish this Action to the GitHub
   Marketplace** and resolve any validation warnings.
4. Choose the closest supported primary category (e.g. code quality), review
   release version and notes, and publish. The existing `v0.1.0`, `v0.1.1` and `v0.1.2`
   tags and assets must not be rewritten. GitHub currently reports
   `immutable: false` for `v0.1.2`; platform-level immutability is not established. If GitHub cannot add the
   Marketplace listing to an existing release, plan this for a **new,
   independently tested release**, rather than inventing a release version.
5. Check that the resulting **Marketplace listing URL is public** and
   names the correct `swiast/dist-parity` repository. Record that URL and
   the publication date only after confirmation.

**Do not claim Marketplace publication based solely on a GitHub release.**
The manual PyPI workflow is a *separate* process and remains account-gated.

## First-time external evaluation

- [Two-minute trial using the GitHub-released wheel](TRY_IT.md)
- [Structured external feedback form](https://github.com/swiast/dist-parity/issues/new?template=feedback.yml)
- [Public maintainer-authored invitation](https://github.com/swiast/dist-parity/issues/7)
- [Proven GitHub wheel installation / tagged Action checks](RELEASE_VALIDATION.md)

Report feedback accurately:

| Evidence | What may be claimed |
| --- | --- |
| Our own CI, issue, pull request or smoke test | Active maintainer development; **not** external adoption |
| Genuine outside docs-only review | Independent review, but **not** an install |
| Genuine outside CLI run with reproduction details | Independent evaluation of the CLI |
| Public downstream workflow containing `uses: swiast/dist-parity@...` and successful run | Verified downstream CI integration |
| Public Marketplace listing | Improved discoverability; **not** actual downloads or users |
| PyPI project exists with release files | Published on PyPI; **not** necessarily downloaded |

Never solicit fake stars, comments, installations or screenshots. Do not
contact external repositories or communities without reviewing their
contribution and AI/LLM policies, and avoid unrelated promotional issues.
