# Publish dist-parity to PyPI (manual, trusted, no API tokens)

The repository has a GitHub release at [v0.1.2](https://github.com/swiast/dist-parity/releases/tag/v0.1.2), but **this does not establish a PyPI release**.

The workflow [`pypi-publish.yml`](../.github/workflows/pypi-publish.yml) is manual-only. It downloads the *existing* GitHub release's wheel and sdist, checks their SHA-256 digests against the verified release assets, then publishes via PyPI's GitHub OIDC Trusted Publisher mechanism. It needs no long-lived PyPI token or repository secret. **It will not publish until a maintainer explicitly runs it.**

## One-time trusted publisher setup

1. Sign in to [PyPI](https://pypi.org/) with an account under your control and complete any account/2FA requirements.
2. Confirm that the normalized project name `dist-parity` is available, or that you already control it. PyPI prevents overwriting someone else's project. Do **not** choose an ambiguous or typo-squatting name if the name is unavailable.
3. For a brand-new project, use [PyPI account Publishing](https://pypi.org/manage/account/publishing/) to register a **pending GitHub trusted publisher**. For an existing project you own, use that project's **Manage → Publishing** page instead.
4. Fill in the publisher fields **exactly**:

| PyPI field | Value |
| --- | --- |
| PyPI project name (pending publisher only) | `dist-parity` |
| GitHub repository owner | `swiast` |
| GitHub repository name | `dist-parity` |
| GitHub workflow filename | `pypi-publish.yml` |
| GitHub environment name | `pypi` |

5. In [GitHub repository Settings → Environments](https://github.com/swiast/dist-parity/settings/environments), create or review the `pypi` environment. Prefer restricting deployments to protected branches and requiring an approval when practical.
6. Open [Actions → Publish v0.1.2 to PyPI (manual)](https://github.com/swiast/dist-parity/actions/workflows/pypi-publish.yml), select **Run workflow**, choose `main`, and run it **once**.
7. Check the run logs for success and verify the release at `https://pypi.org/project/dist-parity/0.1.2/`. Do not claim publication before it is confirmed.

## Safety and recovery

- No trigger on `push`, `pull_request`, or `release`. This workflow is manually invoked.
- Job-level permissions are `contents: read` and `id-token: write`; OIDC access is scoped through the `pypi` environment.
- The action will publish only GitHub release assets matching these fixed hashes:
  - `dist_parity-0.1.2-py3-none-any.whl`: `f7404baf015ebea9a188764713839b5a0244d6237dfe46b12c5d2ff576f75aa1`
  - `dist_parity-0.1.2.tar.gz`: `40e61f0b8fdc9cb5a5e66fd3a561b7b314c744a9c431ecfc15cce89008d851da`
- PyPI packages cannot be silently overwritten. If the workflow fails after a partial upload, inspect [PyPI project files](https://pypi.org/manage/projects/) before retrying; do **not** edit hashes or force an upload.
- No account password, API token, personal email, or private project data should be posted to GitHub issues or shared in this repository.
- PyPI visibility and download counts **do not automatically establish third-party adoption**. Treat only verifiable independent installs, issues, or downstream integrations as independent evidence.

Official references: [PyPI pending trusted publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/) and [publishing with trusted publishers](https://docs.pypi.org/trusted-publishers/using-a-publisher/).
