# Contributing to ShadowClaude

Thank you for your interest in contributing to ShadowClaude! This document provides guidelines for contributing.

## How to Contribute

### Reporting Bugs

Before creating a bug report, please:

1. Check if the issue already exists
2. Use the latest version
3. Provide a minimal reproducible example

Use the bug report template when creating issues.

### Suggesting Features

Feature requests are welcome! Please:

1. Check if the feature has already been requested
2. Explain the use case clearly
3. Describe expected behavior

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`cargo test`, `pytest`)
5. Commit your changes (`git commit -m 'feat: add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Development Setup

See [Development Setup](./setup/environment.md) for detailed instructions.

Quick start:

```bash
git clone https://github.com/shadowclaude/shadowclaude.git
cd shadowclaude
cargo build
```

## Code Standards

- Follow [Code Style Guidelines](./guidelines/code-style.md)
- Write tests for new features
- Update documentation
- Keep commits atomic and well-described

## Commit Message Format

We follow [Conventional Commits](https://conventionalcommits.org/):

```
<type>(<scope>): <description>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code refactoring
- `test`: Tests
- `chore`: Maintenance

## Code Review Process

1. All PRs require at least one review
2. CI checks must pass
3. Documentation must be updated
4. Tests must be included

## Community

- Be respectful and inclusive
- Help others learn
- Give constructive feedback

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

*Thank you for contributing to ShadowClaude!*
