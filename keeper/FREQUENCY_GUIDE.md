# GoFile Keeper Frequency Guide

Choose the right frequency for your needs. Here's a comparison of different approaches:

## Quick Comparison

| Frequency | Safety Level | GitHub Actions Usage | Bandwidth | Best For |
|-----------|--------------|---------------------|-----------|----------|
| **Hourly** | 🟢 Maximum | 🔴 High (240 min/month) | 🟡 Medium | Critical files |
| **Every 6 hours** | 🟢 Very High | 🟡 Medium (80 min/month) | 🟢 Low | Active streamers |
| **Daily** | 🟢 High | 🟢 Low (30 min/month) | 🟢 Low | Regular use |
| **Every 3 days** | 🟡 Good | 🟢 Very Low (10 min/month) | 🟢 Very Low | Casual use |
| **Weekly (default)** | 🟡 Adequate | 🟢 Minimal (4 min/month) | 🟢 Minimal | Set and forget |

## Detailed Options

### 1. Hourly (Maximum Protection)

**Use Case**: Critical files that must never be lost

```yaml
# .github/workflows/gofile-keeper-hourly.yml
schedule:
  - cron: '0 * * * *'  # Every hour
```

**Pros:**
- ✅ Maximum protection (9-day safety buffer)
- ✅ Immediate processing of new uploads
- ✅ Quick detection of failed links

**Cons:**
- ❌ Uses 240 minutes/month (may exceed free tier)
- ❌ Higher bandwidth usage
- ❌ May trigger rate limits

**Cost**: May require paid GitHub plan ($4/month)

### 2. Every 6 Hours (Recommended for Active Use)

**Use Case**: Active streamers with regular uploads

```yaml
schedule:
  - cron: '0 */6 * * *'  # 4 times per day
```

**Pros:**
- ✅ Excellent protection (4-day safety buffer)
- ✅ Stays within free tier (80 min/month)
- ✅ Good balance of safety and efficiency

**Cons:**
- ⚠️ Moderate resource usage

**Cost**: Free

### 3. Daily (Good Balance)

**Use Case**: Regular streamers, good safety margin

```yaml
schedule:
  - cron: '0 3 * * *'  # Every day at 3 AM
```

**Pros:**
- ✅ Great protection (9-day safety buffer)
- ✅ Low resource usage (30 min/month)
- ✅ Easy to monitor

**Cons:**
- ⚠️ 24-hour delay for new uploads

**Cost**: Free

### 4. Every 3 Days (Conservative)

**Use Case**: Casual use, lower activity

```yaml
schedule:
  - cron: '0 3 */3 * *'  # Every 3 days
```

**Pros:**
- ✅ Good protection (7-day safety buffer)
- ✅ Very low resource usage (10 min/month)
- ✅ Minimal bandwidth

**Cons:**
- ⚠️ Smaller safety margin
- ⚠️ 3-day delay for new uploads

**Cost**: Free

### 5. Weekly (Default - Set and Forget)

**Use Case**: Minimal maintenance, basic protection

```yaml
schedule:
  - cron: '0 3 */7 * *'  # Every 7 days
```

**Pros:**
- ✅ Adequate protection (3-day safety buffer)
- ✅ Minimal resource usage (4 min/month)
- ✅ Set and forget

**Cons:**
- ⚠️ Tight safety margin
- ⚠️ Week delay for new uploads

**Cost**: Free

## Adaptive Approach (Recommended)

The **adaptive workflow** automatically adjusts frequency based on file age:

```yaml
# Different schedules for different priorities
schedule:
  - cron: '0 */2 * * *'   # Every 2 hours for files < 24 hours old
  - cron: '30 */6 * * *'  # Every 6 hours for files < 1 week old
  - cron: '0 */12 * * *'  # Every 12 hours for files < 1 month old
  - cron: '0 4 * * *'     # Daily for older files
```

**Benefits:**
- 🎯 **Smart prioritization**: New files get more attention
- 💰 **Cost efficient**: Older files checked less frequently
- 🔒 **Maximum safety**: Critical period covered intensively
- 📊 **Scalable**: Handles growing file counts efficiently

## How to Choose

### For New Projects (< 100 files)
- Start with **Daily** frequency
- Monitor for 2 weeks
- Adjust based on upload patterns

### For Active Streamers (100-1000 files)
- Use **Adaptive** workflow
- Provides best balance of safety and efficiency
- Automatically scales with your growth

### For Large Archives (1000+ files)
- Use **Adaptive** workflow with larger batch sizes
- Consider multiple workflows for different streamer tiers
- Monitor GitHub Actions usage

### For Critical Business Use
- Use **Hourly** frequency
- Set up monitoring and alerts
- Consider paid GitHub plan for higher limits

## Implementation

### Step 1: Choose Your Frequency

Copy the appropriate workflow file:

```bash
# For daily
cp keeper/.github/workflows/gofile-keeper-daily.yml .github/workflows/

# For continuous (6 hours)
cp keeper/.github/workflows/gofile-keeper-continuous.yml .github/workflows/

# For hourly
cp keeper/.github/workflows/gofile-keeper-hourly.yml .github/workflows/

# For adaptive (recommended)
cp keeper/.github/workflows/gofile-keeper-adaptive.yml .github/workflows/
```

### Step 2: Adjust Parameters

Edit the workflow file to customize:

```yaml
env:
  BATCH_SIZE: '50'              # Smaller batches for frequent runs
  DELAY_BETWEEN_REQUESTS: '5'   # Longer delays to avoid rate limits
  MIN_KEEP_INTERVAL_DAYS: '0.25' # 6 hours in days
```

### Step 3: Monitor Usage

Check your GitHub Actions usage:
1. Go to Settings → Billing → Plans and usage
2. View "Actions" usage
3. Ensure you stay within limits

## Rate Limiting Protection

GoFile may rate limit frequent requests. Protect against this:

### Increase Delays
```yaml
env:
  DELAY_BETWEEN_REQUESTS: '10'  # 10 seconds between files
```

### Reduce Batch Sizes
```yaml
env:
  BATCH_SIZE: '20'  # Process fewer files per run
```

### Add Random Jitter
```yaml
- name: Random delay
  run: |
    DELAY=$((RANDOM % 60 + 30))  # 30-90 seconds
    echo "Waiting $DELAY seconds..."
    sleep $DELAY
```

## Monitoring Multiple Frequencies

If you run multiple workflows, monitor them:

### View All Workflows
```bash
# List all keeper workflows
ls .github/workflows/gofile-keeper*.yml
```

### Check Execution History
1. Go to Actions tab
2. Filter by workflow name
3. Monitor success rates

### Avoid Overlaps
Ensure workflows don't run simultaneously:

```yaml
# Stagger start times
- cron: '0 */6 * * *'    # Continuous: 00:00, 06:00, 12:00, 18:00
- cron: '30 3 * * *'     # Daily: 03:30
- cron: '15 */2 * * *'   # Hourly: XX:15
```

## Cost Analysis

### GitHub Actions Free Tier
- **Limit**: 2,000 minutes/month
- **Typical keeper run**: 2-5 minutes

### Usage by Frequency
| Frequency | Runs/Month | Minutes/Month | Within Free Tier? |
|-----------|------------|---------------|-------------------|
| Hourly | 720 | 1,440-3,600 | ⚠️ May exceed |
| 6 hours | 120 | 240-600 | ✅ Yes |
| Daily | 30 | 60-150 | ✅ Yes |
| 3 days | 10 | 20-50 | ✅ Yes |
| Weekly | 4 | 8-20 | ✅ Yes |

### If You Exceed Free Tier
- **GitHub Pro**: $4/month (3,000 minutes)
- **GitHub Team**: $4/user/month (3,000 minutes)
- **Pay-per-use**: $0.008/minute

## Best Practices

### Start Conservative
1. Begin with **Daily** frequency
2. Monitor for issues
3. Increase frequency if needed

### Monitor Success Rates
- Aim for >95% success rate
- Investigate if rate drops below 90%
- Failed links may indicate deleted files

### Adjust Based on Patterns
- **High upload frequency**: Use adaptive workflow
- **Batch uploads**: Increase frequency temporarily
- **Stable archive**: Reduce to weekly

### Set Up Alerts
```yaml
- name: Notify on high failure rate
  if: failure()
  run: |
    # Send notification if too many failures
    curl -X POST ${{ secrets.WEBHOOK_URL }} \
      -d "GoFile Keeper failure rate too high"
```

## Troubleshooting

### "Too many requests" errors
- Increase `DELAY_BETWEEN_REQUESTS`
- Reduce `BATCH_SIZE`
- Switch to less frequent schedule

### GitHub Actions limit exceeded
- Reduce frequency
- Optimize batch sizes
- Consider paid plan

### Links still expiring
- Check workflow is running
- Verify success rates
- Ensure 10-day rule understanding

## Migration Between Frequencies

### From Weekly to Daily
1. Copy daily workflow file
2. Disable weekly workflow (comment out schedule)
3. Test daily workflow
4. Delete weekly workflow after confirmation

### From Daily to Adaptive
1. Copy adaptive workflow file
2. Test with manual trigger
3. Disable daily workflow
4. Monitor adaptive performance

### Rollback Plan
Always keep a backup workflow:
```yaml
# Emergency backup - runs weekly
name: GoFile Keeper (Backup)
on:
  schedule:
    - cron: '0 5 */7 * *'  # Different time than main
```

---

## Recommendation

For most users, I recommend the **Adaptive workflow**:
- Provides maximum protection for new files
- Efficient resource usage
- Scales automatically
- Handles varying upload patterns
- Stays within free tier

Start with adaptive, monitor for 2 weeks, then adjust based on your specific needs.