# Migration Guide

This document describes how to handle breaking changes between versions of SnipContext.

## Backup Before Upgrade

**Always backup your snippets before upgrading.** The storage directory contains all your data. Simply copy it to a safe location.

```bash
cp -r ~/.snipcontext ~/.snipcontext.backup.$(date +%Y%m%d)
```

## Versioning Policy

- **v0.x**: Breaking changes may occur on any minor version bump (e.g., v0.2 → v0.3). We will document them in the CHANGELOG.
- **v1.0+**: Breaking changes only on major version bumps.

## Checking if a Migration is Needed

Run the following command to check the current storage version and compare it to the expected version:

```bash
snipcontext migrate --dry-run
```

If it prints that a migration is required, follow the steps below.

## How to Migrate

1. **Read the CHANGELOG** for the new version to understand what changed.
2. **Backup your snippets** (see above).
3. **Run the migration command** (if available). Currently, automatic migration is a work in progress – if the command says it’s not implemented, you may need to:
   - Export all snippets using an older version,
   - Upgrade SnipContext,
   - Re‑import them using the new version’s import tools.
4. **Verify** your snippets are intact after the upgrade.

## Future Automatic Migration

We plan to add a `snipcontext migrate` command that will automatically convert storage formats, config files, and search indices. Watch the CHANGELOG for announcements.
