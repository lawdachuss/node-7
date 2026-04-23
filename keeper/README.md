# GoFile Link Keeper

A smart, autonomous system to keep GoFile links active and prevent automatic deletion due to inactivity.

## Problem

GoFile free accounts delete files after **10 days of inactivity** (no downloads). This keeper system automatically "touches" your links by downloading a small portion of each file periodically.

## How It Works

The **Smart Keeper** uses one intelligent workflow that automatically adjusts its behavior:

1. **Multiple Schedules**: Runs at different frequencies for different priorities
   - **Every 2 hours**: Critical files (uploaded in last 24 hours)
   - **Every 6 hours**: Important files (uploaded in last week)  
   - **Every 12 hours**: Normal files (uploaded in last month)
   - **Daily**: Maintenance mode (all files)

2. **Smart Processing**: Downloads only the first 1KB of each file to register activity

3. **Adaptive Behavior**: 
   - Adjusts delays based on rate limiting
   - Handles errors intelligently
   - Prioritizes never-kept files
   - Filters by file age automatically

4. **Comprehensive Logging**: Tracks success rates, errors, and provides recommendations

## Setup

### Prerequisites

- Supabase project with `gofile_uploads` table
- GitHub repository 
- Supabase credentials (URL and API key)

### Quick Setup

1. **Copy the keeper folder to your repository**

2. **Set up GitHub Secrets**:
   - Go to repo → Settings → Secrets and variables → Actions
   - Add `SUPABASE_URL`: Your Supabase project URL
   - Add `SUPABASE_API_KEY`: Your Supabase anon/service key

3. **Copy the workflow file**:
   ```bash
   cp keeper/.github/workflows/gofile-keeper.yml .github/workflows/
   ```

4. **Run database migration**:
   ```sql
   -- In Supabase SQL Editor
   -- Copy and run the contents of keeper/database_migration.sql
   ```

5. **Enable GitHub Actions** and you're done!

## Smart Modes

The keeper automatically runs in different modes:

### Automatic Modes (Scheduled)
- **High Priority** (every 2 hours): New files that need immediate protection
- **Medium Priority** (every 6 hours): Recent files needing regular attention  
- **Low Priority** (every 12 hours): Older files with established patterns
- **Maintenance** (daily): Comprehensive check of all files

### Manual Modes (Workflow Dispatch)
- **Auto**: Smart defaults based on current conditions
- **Aggressive**: Maximum processing power (emergency situations)
- **Conservative**: Minimal processing (rate limit issues)
- **Emergency**: Process everything immediately
- **Test**: Safe mode for testing (only 5 files)

## Configuration

The smart workflow automatically configures itself, but you can customize:

### Environment Variables
```bash
# All optional - smart defaults are used
BATCH_SIZE=50              # Files per run (0 = auto)
DELAY_BETWEEN_REQUESTS=3   # Seconds between files
MIN_KEEP_INTERVAL_DAYS=0.5 # Hours between keeps (as decimal days)
AGE_FILTER_DAYS=30         # Only process files newer than X days
```

### Manual Triggers
1. Go to Actions tab
2. Select "GoFile Link Keeper"
3. Click "Run workflow"
4. Choose mode and parameters

## Monitoring

### GitHub Actions Dashboard
- View execution history in Actions tab
- Each run shows detailed logs and statistics
- Job summaries show key metrics

### Success Indicators
```
🤖 Smart Keeper Configuration:
   Mode: high_priority
   Priority: critical
   Batch Size: 25
   Status: success

📊 RESULTS:
✅ Successfully kept alive: 23/25
❌ Failed: 2/25 (already deleted)
📊 Success rate: 92.0%
🎉 Excellent performance!
```

### Database Queries
```sql
-- View recent activity
SELECT 
  streamer_name,
  gofile_link,
  last_kept,
  keep_alive_count,
  status
FROM gofile_uploads
WHERE last_kept > NOW() - INTERVAL '24 hours'
ORDER BY last_kept DESC;

-- Check statistics
SELECT 
  COUNT(*) as total_files,
  COUNT(*) FILTER (WHERE status = 'active') as active,
  COUNT(*) FILTER (WHERE last_kept IS NOT NULL) as ever_kept,
  AVG(keep_alive_count) as avg_keeps
FROM gofile_uploads;
```

## Error Handling

The smart keeper handles all common issues automatically:

### Rate Limiting
- Detects 429 responses
- Automatically increases delays
- Adds random jitter to prevent synchronization

### Network Issues  
- Retries failed requests with backoff
- Continues processing other files if some fail
- Reports network errors separately

### Deleted Files
- Detects 404 responses
- Marks files as deleted in database
- Excludes them from future processing

### Database Issues
- Continues processing even if database updates fail
- Logs database errors for investigation
- Doesn't stop the entire run for DB issues

## Cost & Performance

### GitHub Actions Usage
- **Free tier**: 2,000 minutes/month
- **Typical usage**: 50-100 minutes/month
- **Cost**: $0 (well within free tier)

### Bandwidth
- **Per file**: 1KB download
- **1,000 files**: 1MB total per run
- **Monthly**: ~10-20MB (negligible)

### Database Operations
- **Reads**: ~100 per run
- **Writes**: ~100 per run  
- **Monthly**: ~2,000 operations (within free tier)

## Advanced Features

### Adaptive Delays
- Increases delays when rate limited
- Reduces delays when everything works smoothly
- Weekend mode (less aggressive on weekends)

### Smart Filtering
- Prioritizes never-kept files
- Focuses on recently uploaded files during high-priority runs
- Processes older files during maintenance runs

### Comprehensive Reporting
- Success rates and performance metrics
- Failed link analysis with recommendations
- Execution summaries with insights

### Error Recovery
- Automatic retry with conservative settings on failure
- Continues processing even with partial failures
- Detailed error categorization

## Troubleshooting

The smart keeper provides detailed diagnostics:

### "No links found"
- Check database has records
- Verify keep intervals aren't too restrictive
- Check age filters

### High failure rate
- Review error messages in logs
- Check if GoFile is experiencing issues
- Verify network connectivity

### Rate limiting
- Keeper automatically handles this
- Will increase delays and retry
- Consider running less frequently if persistent

## Database Schema

Required table structure:
```sql
CREATE TABLE gofile_uploads (
  id SERIAL PRIMARY KEY,
  streamer_name TEXT NOT NULL,
  gofile_link TEXT NOT NULL,
  upload_date TIMESTAMP DEFAULT NOW(),
  last_kept TIMESTAMP,
  keep_alive_count INTEGER DEFAULT 0,
  status TEXT DEFAULT 'active'
);
```

## Security

- Uses GitHub Secrets for credentials
- Read-only database operations where possible
- No sensitive data in logs
- Respects GoFile's rate limits

## Support

The smart keeper is designed to be maintenance-free:

1. **Self-configuring**: Automatically adjusts to your usage patterns
2. **Self-healing**: Handles errors and recovers automatically  
3. **Self-monitoring**: Provides detailed diagnostics and recommendations
4. **Self-optimizing**: Learns from failures and adjusts behavior

For issues:
1. Check GitHub Actions logs for detailed diagnostics
2. Review the troubleshooting section
3. Use test mode to safely debug issues

## Migration from Multiple Workflows

If you previously had multiple workflow files:

1. Delete old workflow files:
   ```bash
   rm .github/workflows/gofile-keeper-*.yml
   ```

2. Copy the new smart workflow:
   ```bash
   cp keeper/.github/workflows/gofile-keeper.yml .github/workflows/
   ```

3. The smart workflow handles all previous functionality automatically

## License

MIT - Use freely in any project
