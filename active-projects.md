# Active Projects

## Complexity Assessment

Complexity assessment is automated through the `Complexity Report` GitHub Actions workflow.
On each push to `master`, the workflow installs SnipContext, runs
`snipcontext complexity --output docs/complexity_report.md`, and commits the updated generated report
back to `master` when the report changes.
