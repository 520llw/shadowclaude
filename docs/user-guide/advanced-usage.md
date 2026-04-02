# ShadowClaude Advanced Usage

This guide covers advanced features and usage patterns.

## Multi-Agent Coordination

### Creating Custom Agents

```python
from shadowclaude.agents import Agent, Task, TaskResult

class CodeReviewAgent(Agent):
    """Agent specialized in code review."""
    
    def handle(self, task: Task) -> TaskResult:
        code = task.data['code']
        
        # Perform analysis
        issues = self.analyze_code(code)
        suggestions = self.generate_suggestions(code)
        
        return TaskResult(
            success=True,
            output={
                'issues': issues,
                'suggestions': suggestions
            }
        )
```

### Task Orchestration

```python
from shadowclaude import Coordinator

coordinator = Coordinator()

# Register agents
coordinator.register_agent('reviewer', CodeReviewAgent())
coordinator.register_agent('tester', TestAgent())
coordinator.register_agent('documenter', DocAgent())

# Create complex workflow
workflow = coordinator.create_workflow()
workflow.add_step('review', depends_on=[])
workflow.add_step('test', depends_on=['review'])
workflow.add_step('document', depends_on=['review'])

result = workflow.execute(code=my_code)
```

## Advanced Memory Management

### Custom Embeddings

```python
from shadowclaude.memory import SemanticMemory, Embedder

class CustomEmbedder(Embedder):
    def embed(self, text: str) -> list[float]:
        # Your custom embedding logic
        return self.model.encode(text)

memory = SemanticMemory(
    embedder=CustomEmbedder()
)
```

### Memory Import/Export

```python
# Export memories
memory.export_to_file('memories.json')

# Import memories
memory.import_from_file('memories.json')
```

## Tool Development

### Advanced Tool Definition

```python
from shadowclaude.tools import Tool, ToolResult
from pydantic import BaseModel

class SearchArgs(BaseModel):
    pattern: str
    path: str = '.'
    recursive: bool = True

class AdvancedSearchTool(Tool):
    name = 'advanced_search'
    description = 'Advanced file search with regex'
    args_schema = SearchArgs
    
    async def execute(self, args: SearchArgs) -> ToolResult:
        import re
        from pathlib import Path
        
        results = []
        pattern = re.compile(args.pattern)
        
        base_path = Path(args.path)
        files = base_path.rglob('*') if args.recursive else base_path.iterdir()
        
        for file in files:
            if file.is_file():
                content = file.read_text()
                matches = pattern.findall(content)
                if matches:
                    results.append({
                        'file': str(file),
                        'matches': len(matches)
                    })
        
        return ToolResult(output=results)
```

## KAIROS Daemon Deep Dive

### Custom Schedulers

```python
from shadowclaude.kairos import Scheduler, Trigger

scheduler = Scheduler()

# Complex schedule
scheduler.add_job(
    name='backup',
    trigger=Trigger.composite([
        Trigger.cron('0 2 * * *'),  # Daily at 2am
        Trigger.interval(hours=6),   # Every 6 hours
    ]),
    action=backup_task
)

# Conditional trigger
scheduler.add_job(
    name='cleanup',
    trigger=Trigger.when(
        condition=lambda: disk_usage() > 0.9,
        then=Trigger.interval(minutes=5)
    ),
    action=cleanup_task
)
```

### File Watching

```python
from shadowclaude.kairos import FileWatcher, EventType

watcher = FileWatcher()

watcher.watch(
    path='/project/src',
    events=[EventType.MODIFY, EventType.CREATE],
    patterns=['*.rs', '*.py'],
    handler=lambda event: {
        print(f"File changed: {event.path}")
        run_tests()
    }
)
```

## Undercover Mode

### Silent Monitoring

```python
from shadowclaude.undercover import UndercoverMode

undercover = UndercoverMode(
    trigger_words=['bug', 'error', 'issue'],
    auto_suggest=True,
    notification_level='subtle'
)

undercover.start()
```

### Context-Aware Assistance

```python
undercover.configure(
    context_detection=True,
    detect_patterns={
        'code_review': r'review|PR|pull request',
        'debugging': r'bug|debug|fix',
        'refactoring': r'refactor|clean up|improve'
    },
    suggestions_by_context={
        'code_review': ['check_style', 'run_tests'],
        'debugging': ['search_logs', 'check_stackoverflow']
    }
)
```

## WebSocket Integration

### Real-time Collaboration

```javascript
// Frontend integration
class ShadowClaudeClient {
    constructor(url, token) {
        this.ws = new WebSocket(url);
        this.token = token;
        this.sessionId = null;
    }
    
    async connect() {
        this.ws.onopen = () => {
            this.authenticate();
        };
        
        this.ws.onmessage = (event) => {
            this.handleMessage(JSON.parse(event.data));
        };
    }
    
    async streamQuery(query, onChunk) {
        const id = `req_${Date.now()}`;
        
        this.send({
            type: 'query',
            id,
            payload: {
                message: query,
                stream: true,
                session_id: this.sessionId
            }
        });
        
        return new Promise((resolve) => {
            const chunks = [];
            
            this.pending[id] = {
                onChunk: (chunk) => {
                    chunks.push(chunk);
                    onChunk?.(chunk);
                },
                onComplete: () => resolve(chunks.join(''))
            };
        });
    }
}
```

## Performance Tuning

### Query Optimization

```python
from shadowclaude import QueryEngine

engine = QueryEngine(
    cache_config={
        'enabled': True,
        'ttl': 3600,
        'max_size': '100MB'
    },
    batch_config={
        'enabled': True,
        'max_batch_size': 10,
        'max_latency_ms': 100
    }
)
```

### Parallel Execution

```python
import asyncio

async def parallel_queries(queries):
    tasks = [
        engine.process(q)
        for q in queries
    ]
    results = await asyncio.gather(*tasks)
    return results
```

---

*Last Updated: 2026-04-02*
