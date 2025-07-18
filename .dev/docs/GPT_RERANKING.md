# GPT-Enhanced Reranking (Phase 4 Step 2)

## Overview

The GPT-Enhanced Reranking system provides intelligent task prioritization using OpenAI's GPT models to analyze and rerank tasks with human-readable explanations, cost controls, and confidence-based filtering.

## Features

### Core Capabilities
- **JSON-based GPT prompting** for structured, reliable responses
- **Cost-limited API usage** with configurable spending limits
- **Confidence-based filtering** to ensure quality recommendations
- **Enhanced logging** with detailed GPT insights and cost tracking
- **Fallback mechanisms** for robustness and reliability
- **Rich CLI output** with visual indicators and detailed explanations

### GPT Analysis Provides
- **Human-readable explanations** of task priority decisions
- **Urgency indicators** detected from task content
- **Mode alignment** assessment (work, personal, weekend, evening)
- **Recommendation levels** (prioritize, defer, standard)
- **Confidence scores** for reliability assessment

## Configuration

### Enabling GPT Reranking

Add the following configuration to your `ranking_config.json`:

```json
{
  "gpt_reranking": {
    "enabled": true,
    "model": "gpt-3.5-turbo",
    "candidate_limit": 10,
    "max_tokens": 1000,
    "temperature": 0.3,
    "timeout": 30,
    "cost_limit_per_run_usd": 0.10,
    "confidence_threshold": 0.7,
    "fallback_on_error": true
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable/disable GPT reranking |
| `model` | string | `"gpt-3.5-turbo"` | OpenAI model to use |
| `candidate_limit` | integer | `10` | Max tasks to analyze with GPT |
| `max_tokens` | integer | `1000` | Maximum tokens per GPT request |
| `temperature` | float | `0.3` | GPT creativity level (0.0-1.0) |
| `timeout` | integer | `30` | Request timeout in seconds |
| `cost_limit_per_run_usd` | float | `0.10` | Maximum cost per run in USD |
| `confidence_threshold` | float | `0.7` | Minimum confidence to accept GPT reranking |
| `fallback_on_error` | boolean | `true` | Fall back to base ranking on errors |

## Usage

### CLI Commands

```bash
# Enable GPT reranking with cost controls (respects config)
python main.py --generate-today --gpt-rerank --limit 5

# Use legacy GPT-enhanced ranking (always enabled)
python main.py --generate-today --gpt-enhanced-ranking --limit 3

# Dry run to preview results
python main.py --generate-today --gpt-rerank --dry --limit 5
```

### Example Output

```
🎯 Generating today's task list (mode: work, limit: 3)
🤖 Using GPT-powered reranking with cost controls

🎯 Today's prioritized tasks:
  1. [0.85 (↑0.15)] 🔥 Fix critical authentication bug affecting all users...
      🤖 This task contains critical system impact requiring immediate prioritization
      📊 urgency: urgent, critical, authentication | alignment: high priority security issue | confidence: 0.95 | source: gpt_reranked | Cost: $0.0023

  2. [0.75] 📋 Schedule quarterly planning meeting with team...
      🤖 Meeting tasks require coordination but standard priority for work mode
      📊 urgency: meeting | alignment: routine coordination task | confidence: 0.80 | source: gpt_enhanced | Cost: $0.0018

  3. [0.65] ⏳ Update project documentation when time permits...
      🤖 Documentation updates are important but can be deferred
      📊 urgency: | alignment: low priority maintenance | confidence: 0.75 | source: gpt_enhanced | Cost: $0.0015
```

## Architecture

### GPT Reranking Flow

1. **Base Ranking**: Generate initial ranking using existing algorithm
2. **Candidate Selection**: Select top N candidates based on `candidate_limit`
3. **Cost Estimation**: Estimate API costs and check against limits
4. **GPT Analysis**: Send structured JSON prompts to OpenAI API
5. **Response Parsing**: Parse JSON responses with fallback to regex
6. **Confidence Filtering**: Apply confidence thresholds
7. **Final Ranking**: Sort by final scores and apply limits

### JSON Prompt Structure

```json
{
  "task": {
    "content": "URGENT: Fix critical bug",
    "priority": 1,
    "due_date": "today",
    "labels": ["work", "urgent", "bug"],
    "id": "12345"
  },
  "context": {
    "mode": "work",
    "user_profile": "Developer focused on quality and deadlines",
    "base_score": 0.75,
    "base_explanation": "High priority task with due date"
  },
  "request": {
    "analyze_task_priority": true,
    "provide_explanation": true,
    "suggest_rerank_score": true,
    "confidence_assessment": true
  }
}
```

### JSON Response Structure

```json
{
  "explanation": "This task contains urgent indicators and critical system impact",
  "confidence": 0.95,
  "rerank_score": 0.85,
  "reasoning": "Authentication bugs affect all users",
  "urgency_indicators": ["urgent", "critical", "authentication"],
  "mode_alignment": "high priority security issue",
  "recommendation": "prioritize"
}
```

## Cost Management

### Cost Estimation
- Estimates tokens based on task content and prompt structure
- Uses model-specific pricing (GPT-3.5-turbo, GPT-4, GPT-4-turbo)
- Tracks actual costs and stops processing when limits are reached

### Cost Monitoring
```
GPT_RANK_CONFIG: Model=gpt-3.5-turbo, Max tokens=1000, Cost limit=$0.100
GPT_RANK_CANDIDATE: Task 123 → Base: 0.750 | GPT: 0.850 | Confidence: 0.95 | Model: gpt-3.5-turbo | Source: gpt_reranked | Cost: $0.0023
GPT_RANK_SUMMARY: Selected 3 tasks from 8 candidates | GPT enhanced: 2, reranked: 1 | Total cost: $0.0156
```

## Error Handling & Fallbacks

### Fallback Scenarios
1. **GPT Reranking Disabled**: Falls back to base ranking algorithm
2. **Cost Limit Reached**: Stops GPT processing, uses base scores for remaining tasks
3. **Low Confidence**: Uses base score instead of GPT rerank score
4. **API Errors**: Graceful fallback to base ranking with error logging
5. **JSON Parse Errors**: Falls back to regex parsing for legacy responses

### Mock Mode
For testing and development without API costs:
```bash
export GPT_MOCK_MODE=1
python main.py --generate-today --gpt-rerank
```

## Testing

### Running Tests
```bash
# Run all GPT reranking tests
python run_tests.py

# Run only unit tests
python run_tests.py unit

# Run only integration tests  
python run_tests.py integration

# Verbose output
python run_tests.py --verbose
```

### Test Coverage
- **Unit Tests**: JSON parsing, cost estimation, confidence filtering, mock responses
- **Integration Tests**: Full pipeline, configuration loading, error handling, multi-mode ranking
- **Test Fixtures**: Sample GPT responses, cost scenarios, confidence thresholds

## Monitoring & Debugging

### Log Levels
- **INFO**: Normal operation, ranking results, cost summaries
- **DEBUG**: Detailed JSON parsing, API interactions
- **WARNING**: Cost limits, low confidence, fallbacks
- **ERROR**: API failures, parsing errors

### Key Log Patterns
```
GPT_RANK_START: Processing 8 candidates for GPT-enhanced ranking (mode: work)
GPT_RANK_CANDIDATE: Task 123 → Base: 0.750 | GPT: 0.850 | Confidence: 0.95
GPT_RANK_EXPLANATION: Task 123 | Base: high priority task | GPT: Critical system impact
GPT_RANK_URGENCY: Task 123 | Indicators: urgent, critical, authentication
GPT_RANK_RECOMMENDATION: Task 123 | PRIORITIZE: Authentication bugs affect all users
GPT_RANK_SUMMARY: Selected 3 tasks from 8 candidates | Total cost: $0.0156
```

## Performance Considerations

### Optimization Strategies
1. **Candidate Limiting**: Process only top N tasks to control costs
2. **Cost Estimation**: Stop processing before hitting limits
3. **Confidence Thresholds**: Filter low-quality recommendations
4. **Timeout Controls**: Prevent hanging on slow API responses
5. **Mock Mode**: Test without API costs during development

### Typical Performance
- **Processing Time**: 2-5 seconds for 5 tasks
- **API Costs**: $0.01-0.05 per run (gpt-3.5-turbo)
- **Accuracy**: 85-95% confidence on priority tasks

## Troubleshooting

### Common Issues

**Q: GPT reranking not working**
A: Check that `gpt_reranking.enabled = true` in `ranking_config.json` and `OPENAI_API_KEY` is set

**Q: High API costs**
A: Lower `candidate_limit` or `cost_limit_per_run_usd` in configuration

**Q: Poor recommendations** 
A: Increase `confidence_threshold` or update user profile in `task_sense_config.json`

**Q: Timeout errors**
A: Increase `timeout` value or check network connectivity

**Q: JSON parsing errors**
A: System automatically falls back to regex parsing - check logs for details

### Debug Mode
```bash
python main.py --generate-today --gpt-rerank --debug --dry
```

## Future Enhancements

### Planned Features
- **Custom prompts** for different domains (engineering, marketing, etc.)
- **Learning from feedback** to improve recommendations over time
- **Batch processing** for large task sets
- **Alternative AI models** (Claude, local models)
- **Advanced cost analytics** and optimization

## Security & Privacy

### Data Handling
- Task content is sent to OpenAI API for analysis
- No persistent storage of task data by AI models
- Cost tracking logs may contain task IDs (not content)
- API keys should be stored securely in environment variables

### Best Practices
- Review sensitive tasks before enabling GPT reranking
- Use appropriate cost limits for your budget
- Monitor API usage through OpenAI dashboard
- Consider mock mode for development with sensitive data