# Machine-readable JSON output contract (current source)

The CLI supports `dist-parity --json` and the composite Action on current
`main` supports `format: json` with optional `json-file` output. The
**versioned JSON Schema v1** is in
[`schemas/report-v1.schema.json`](../schemas/report-v1.schema.json).

**Release boundary:** This is a reviewed contract for the current repository
source, NOT a declaration that the published `swiast/dist-parity@v0.1.2`
Action has all current-source options or that this schema ships inside its
historical wheel. A future tagged release needs separate owner approval.

## The two valid report shapes

When a pair can be compared, exit 0 means checked fields agree; exit 1 means
at least one error-severity finding was recorded. Both exit codes produce a
comparison object containing `sdist`, `wheel`, `project`, `version`,
`ok`, and `findings`. Each finding has a nonempty `code`, `severity`
(`info`, `warning` or `error`), a human-facing `message`, and a nullable
`field`. Informational and warning findings do not make `ok` false by themselves.

```json
{
  "sdist": "dist/example-1.0.tar.gz",
  "wheel": "dist/example-1.0-py3-none-any.whl",
  "project": "example",
  "version": "1.0",
  "ok": true,
  "findings": [
    {
      "code": "PARITY_OK",
      "severity": "info",
      "message": "All checked metadata fields are consistent",
      "field": null
    }
  ]
}
```

Invalid arguments, missing or malformed distributions return exit 2 and a
different error object without the comparison-specific identity fields:

```json
{
  "ok": false,
  "error": "--sdist and --wheel must be provided together",
  "findings": []
}
```

Do not infer the exit code solely from `ok`: both exit 1 (a completed
comparison with findings) and exit 2 (an input error) have `ok: false`.
This schema validates structure, not file provenance, content safety, or the
relationship between `ok` and the severities in `findings`.

## CI consumers

```yaml
# On an authorized future release that includes this feature:
- uses: swiast/dist-parity@YOUR_APPROVED_NEW_RELEASE_TAG
  with:
    dist-dir: dist
    format: json
    json-file: ${{ runner.temp }}/dist-parity.json
```

The placeholder is **not an existing release**. On published `v0.1.2`,
call the released CLI with `--json` for its existing JSON behavior instead.
The current-source Action preserves checker status 0/1/2 even when a report
file is written, so use an explicitly conditional or `continue-on-error`
step only when your workflow intentionally needs to inspect a failing report.

Schema version v1 is stored as a **separate file** and is not a new key in
existing CLI output. The schema intentionally rejects unexpected fields to
catch accidental contract drift. `message` is diagnostic prose, not a
stable machine identifier; use `code`, `field`, `severity`, and the
process exit status. Do not place private distribution names or credentials
in public CI output.

## Test the contract from this source checkout

```bash
python -m pip install 'jsonschema==4.26.0'
python scripts/validate_json_contract.py
```

`jsonschema` is installed **only for this optional developer/CI check**;
it is not a runtime dependency of `dist-parity`. The test validates actual
CLI parity, mismatch and input-error responses against Draft 2020-12, plus
negative controls that the schema must reject. The dedicated
[`JSON report contract` workflow](../.github/workflows/json-contract.yml)
executes it on two Python versions. Maintainer CI passing is not independent
adoption and does not attest to released artifact functionality.
