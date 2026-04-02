# Release Process

This document describes the ShadowClaude release process.

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH

Example: 1.2.3
```

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

## Release Checklist

### Pre-Release

- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped in:
  - [ ] `Cargo.toml`
  - [ ] `python/pyproject.toml`
  - [ ] `docs/README.md`
- [ ] Release notes drafted

### Release Steps

1. **Create Release Branch**
   ```bash
   git checkout -b release/v1.2.0
   ```

2. **Update Version**
   ```bash
   # Update version in all files
   ./scripts/bump-version.sh 1.2.0
   ```

3. **Update CHANGELOG**
   ```bash
   # Add release notes to CHANGELOG.md
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "chore(release): prepare v1.2.0"
   ```

5. **Create Tag**
   ```bash
   git tag -a v1.2.0 -m "Release v1.2.0"
   ```

6. **Push to Remote**
   ```bash
   git push origin release/v1.2.0
   git push origin v1.2.0
   ```

7. **Create Release PR**
   - Merge `release/v1.2.0` into `main`
   - Wait for CI
   - Merge

8. **Create GitHub Release**
   - Go to GitHub releases
   - Create new release from tag
   - Add release notes
   - Publish

### Post-Release

- [ ] Verify release on crates.io
- [ ] Verify release on PyPI
- [ ] Update documentation site
- [ ] Announce on social media
- [ ] Close milestone

## Release Automation

### CI/CD Pipeline

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Rust
        run: cargo build --release
      
      - name: Build Python
        run: |
          cd python
          maturin build --release
      
      - name: Publish to crates.io
        run: cargo publish
        env:
          CARGO_REGISTRY_TOKEN: ${{ secrets.CRATES_IO_TOKEN }}
      
      - name: Publish to PyPI
        run: |
          cd python
          maturin publish
        env:
          MATURIN_PYPI_TOKEN: ${{ secrets.PYPI_TOKEN }}
```

## Hotfix Process

For critical bugs in released versions:

1. Create hotfix branch from tag:
   ```bash
   git checkout -b hotfix/v1.2.1 v1.2.0
   ```

2. Fix the bug
3. Update version and CHANGELOG
4. Create PR to `main`
5. Tag and release

## Version Support

| Version | Support Status | End of Life |
|---------|---------------|-------------|
| 1.x | Active | TBD |
| 0.x | End of Life | 2025-01-01 |

---

*Last Updated: 2026-04-02*
