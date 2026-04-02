# Troubleshooting Guide

This guide helps you resolve common issues with ShadowClaude.

## Common Issues

### Installation Issues

#### Command not found

**Problem**: `shadowclaude: command not found`

**Solutions**:

1. Check if installed:
   ```bash
   which shadowclaude
   ```

2. Add to PATH:
   ```bash
   export PATH="$PATH:/usr/local/bin"
   ```

3. Reinstall:
   ```bash
   pip uninstall shadowclaude
   pip install shadowclaude
   ```

#### Permission denied

**Problem**: `Permission denied` when running ShadowClaude

**Solution**:

```bash
# Fix permissions
chmod +x /usr/local/bin/shadowclaude

# Or reinstall with proper permissions
sudo install -m 755 shadowclaude /usr/local/bin/
```

### Configuration Issues

#### API key not found

**Problem**: `Error: LLM API key not configured`

**Solutions**:

1. Set environment variable:
   ```bash
   export ANTHROPIC_API_KEY=sk-xxx
   ```

2. Or configure in file:
   ```yaml
   # ~/.config/shadowclaude/config.yaml
   llm:
     api_key: sk-xxx
   ```

3. Verify:
   ```bash
   shadowclaude doctor
   ```

#### Invalid configuration

**Problem**: `Error: Invalid configuration file`

**Solution**:

```bash
# Validate config
shadowclaude config validate

# Reset to default
shadowclaude init --force
```

### Runtime Issues

#### Connection timeout

**Problem**: `Error: Connection timeout` when calling LLM

**Solutions**:

1. Check internet connection
2. Verify API key is valid
3. Increase timeout:
   ```yaml
   llm:
     timeout: 300  # seconds
   ```

#### Memory connection failed

**Problem**: `Error: Cannot connect to vector database`

**Solutions**:

1. Start required services:
   ```bash
   docker-compose up -d
   ```

2. Check connection:
   ```bash
   curl http://localhost:6333/health
   ```

3. Disable memory (fallback):
   ```yaml
   memory:
     enabled: false
   ```

### Performance Issues

#### Slow response

**Problem**: ShadowClaude is responding slowly

**Solutions**:

1. Enable prompt cache:
   ```yaml
   cache:
     enabled: true
   ```

2. Use faster model:
   ```yaml
   llm:
     model: claude-3-sonnet  # faster than opus
   ```

3. Check system resources:
   ```bash
   htop
   ```

#### High memory usage

**Problem**: ShadowClaude using too much memory

**Solutions**:

1. Limit working memory:
   ```yaml
   memory:
     working:
       max_tokens: 2000
   ```

2. Clear cache:
   ```bash
   shadowclaude cache clear
   ```

### Tool Execution Issues

#### Tool not found

**Problem**: `Error: Tool 'xxx' not found`

**Solution**:

```bash
# List available tools
shadowclaude tools list

# Check if enabled in config
cat ~/.config/shadowclaude/config.yaml
```

#### Permission denied for file access

**Problem**: `Error: Permission denied` when accessing files

**Solutions**:

1. Check allowed paths:
   ```yaml
   tools:
     file:
       allowed_paths:
         - "${HOME}/projects"
   ```

2. Add current directory:
   ```yaml
   tools:
     file:
       allowed_paths:
         - "${PWD}"
   ```

### Build Issues

#### Rust compilation errors

**Problem**: Compilation fails

**Solutions**:

```bash
# Clean and rebuild
cargo clean
cargo build

# Update dependencies
cargo update

# Check Rust version
rustc --version  # Should be >= 1.75.0
```

#### Python binding errors

**Problem**: `ImportError: cannot import name 'shadowclaude'`

**Solutions**:

```bash
# Rebuild Python bindings
cd python
pip install -e .

# Or use maturin
maturin develop
```

## Getting Help

### Diagnostic Command

```bash
shadowclaude doctor
```

This will check:
- Binary installation
- Configuration
- LLM API connectivity
- Memory system
- Tool availability

### Enable Debug Logging

```bash
# Set log level
export RUST_LOG=debug

# Or use flag
shadowclaude --verbose query "test"
```

### Submit Bug Report

```bash
shadowclaude bug-report
```

This will generate a report with:
- System information
- Configuration
- Recent logs
- Stack traces (if any)

## FAQ

### Q: Can I use my own LLM?

Yes! Configure a local LLM:

```yaml
llm:
  provider: local
  url: http://localhost:8000/v1
```

### Q: How do I disable the memory system?

```yaml
memory:
  enabled: false
```

### Q: Can I use ShadowClaude offline?

Partially. You need LLM API connectivity, but you can disable web tools:

```yaml
tools:
  disabled:
    - web_fetch
    - web_search
```

### Q: How do I update ShadowClaude?

```bash
# pip
pip install -U shadowclaude

# cargo
cargo install shadowclaude --force

# Homebrew
brew upgrade shadowclaude
```

## Contact Support

- GitHub Issues: https://github.com/shadowclaude/shadowclaude/issues
- Discord: https://discord.gg/shadowclaude
- Email: support@shadowclaude.dev

---

*Last Updated: 2026-04-02*
