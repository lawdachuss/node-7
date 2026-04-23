# GoFile Keeper Deployment Checklist

Use this checklist to ensure proper deployment of the GoFile Keeper system.

## Pre-Deployment

- [ ] **Understand the problem**
  - [ ] GoFile deletes files after 10 days of inactivity
  - [ ] Keeper prevents this by downloading 1KB every 5-7 days
  - [ ] This registers as activity and resets the deletion timer

- [ ] **Review architecture**
  - [ ] Keeper fetches links from Supabase
  - [ ] Downloads first 1KB of each file
  - [ ] Updates `last_kept` timestamp in database
  - [ ] Runs automatically via GitHub Actions

- [ ] **Verify prerequisites**
  - [ ] Supabase project exists
  - [ ] `gofile_uploads` table exists
  - [ ] GitHub account available
  - [ ] Repository created (or existing repo ready)

## Database Setup

- [ ] **Run database migration**
  - [ ] Connect to Supabase SQL Editor
  - [ ] Run `database_migration.sql`
  - [ ] Verify columns added: `last_kept`, `keep_alive_count`, `status`
  - [ ] Verify indexes created
  - [ ] Check existing records updated with `status='active'`

- [ ] **Test database queries**
  ```sql
  -- Should return links needing keep-alive
  SELECT * FROM gofile_uploads 
  WHERE (status = 'active' OR status IS NULL)
    AND (last_kept IS NULL OR last_kept < NOW() - INTERVAL '5 days')
  LIMIT 5;
  ```

- [ ] **Optional: Set up RLS policies**
  - [ ] Enable Row Level Security
  - [ ] Create read policy for keeper
  - [ ] Create update policy for keeper
  - [ ] Test with anon key

## Repository Setup

### Option A: New Separate Repository (Recommended)

- [ ] **Create new repository**
  - [ ] Go to GitHub → New Repository
  - [ ] Name: `gofile-keeper` (or your choice)
  - [ ] Visibility: Private (recommended) or Public
  - [ ] Initialize with README: No (we'll add our own)
  - [ ] Click "Create repository"

- [ ] **Clone and setup**
  ```bash
  git clone https://github.com/yourusername/gofile-keeper.git
  cd gofile-keeper
  ```

- [ ] **Copy keeper files**
  - [ ] Run `deploy.sh` (Linux/Mac) or `deploy.bat` (Windows)
  - [ ] Or manually copy all files from `keeper/` folder

### Option B: Use Existing Repository

- [ ] **Copy keeper files to existing repo**
  ```bash
  # Copy all keeper files
  cp -r keeper/* /path/to/your/repo/
  ```

- [ ] **Ensure workflow is in correct location**
  - [ ] `.github/workflows/gofile-keeper.yml` exists

## GitHub Configuration

- [ ] **Set up GitHub Secrets**
  - [ ] Go to repo Settings → Secrets and variables → Actions
  - [ ] Click "New repository secret"
  - [ ] Add `SUPABASE_URL`:
    - Name: `SUPABASE_URL`
    - Value: `https://your-project.supabase.co`
  - [ ] Add `SUPABASE_API_KEY`:
    - Name: `SUPABASE_API_KEY`
    - Value: Your Supabase anon or service key
  - [ ] Verify both secrets are saved

- [ ] **Enable GitHub Actions**
  - [ ] Go to Actions tab
  - [ ] If prompted, click "I understand my workflows, go ahead and enable them"
  - [ ] Verify "GoFile Link Keeper" workflow appears

- [ ] **Review workflow configuration**
  - [ ] Open `.github/workflows/gofile-keeper.yml`
  - [ ] Check schedule: `cron: '0 3 */7 * *'` (every 7 days)
  - [ ] Adjust if needed (every 5 days: `*/5`, every 3 days: `*/3`)
  - [ ] Check batch size: default 100
  - [ ] Check delay: default 2 seconds

## Local Testing (Optional but Recommended)

- [ ] **Install Python dependencies**
  ```bash
  cd keeper  # or your repo root
  pip install -r requirements.txt
  ```

- [ ] **Create .env file**
  ```bash
  cp .env.example .env
  # Edit .env with your credentials
  ```

- [ ] **Run keeper locally**
  ```bash
  export $(cat .env | grep -v '^#' | xargs)  # Linux/Mac
  # Or set variables manually on Windows
  python keeper.py
  ```

- [ ] **Verify output**
  - [ ] "Fetching links from Supabase..." appears
  - [ ] Links are processed
  - [ ] Success/failure counts shown
  - [ ] No critical errors

- [ ] **Check database updates**
  ```sql
  SELECT * FROM gofile_uploads 
  WHERE last_kept IS NOT NULL 
  ORDER BY last_kept DESC 
  LIMIT 5;
  ```

## First Production Run

- [ ] **Trigger manual workflow run**
  - [ ] Go to Actions tab
  - [ ] Click "GoFile Link Keeper"
  - [ ] Click "Run workflow" button
  - [ ] Select branch (usually `main`)
  - [ ] Click "Run workflow"

- [ ] **Monitor execution**
  - [ ] Click on the running workflow
  - [ ] Expand "Run GoFile Keeper" step
  - [ ] Watch logs in real-time
  - [ ] Look for success indicators

- [ ] **Verify success**
  - [ ] Workflow completes with green checkmark
  - [ ] Logs show: "✅ Kept alive successfully" for links
  - [ ] Summary shows success count
  - [ ] No critical errors

- [ ] **Check database**
  ```sql
  -- Should show recently updated timestamps
  SELECT 
    streamer_name,
    gofile_link,
    last_kept,
    keep_alive_count,
    status
  FROM gofile_uploads
  WHERE last_kept > NOW() - INTERVAL '1 hour'
  ORDER BY last_kept DESC;
  ```

## Monitoring Setup

- [ ] **Configure notifications**
  - [ ] GitHub sends email on workflow failure (default)
  - [ ] Optional: Add Discord/Slack webhook
  - [ ] Optional: Set up monitoring dashboard

- [ ] **Set up regular checks**
  - [ ] Add calendar reminder to check Actions tab weekly
  - [ ] Monitor success rate
  - [ ] Watch for increasing failures

- [ ] **Create monitoring queries**
  ```sql
  -- View keeper statistics
  SELECT * FROM gofile_keeper_stats;
  
  -- Links never kept
  SELECT COUNT(*) FROM gofile_uploads WHERE last_kept IS NULL;
  
  -- Failed links
  SELECT * FROM gofile_uploads WHERE status = 'failed';
  ```

## Validation

- [ ] **Wait for automatic run**
  - [ ] First automatic run happens based on cron schedule
  - [ ] Check Actions tab after scheduled time
  - [ ] Verify it ran automatically

- [ ] **Verify link longevity**
  - [ ] Wait 2-3 weeks
  - [ ] Test some GoFile links manually
  - [ ] Confirm they're still accessible
  - [ ] Check `last_kept` timestamps are updating

- [ ] **Check resource usage**
  - [ ] Go to Settings → Actions → General
  - [ ] View "Actions usage this month"
  - [ ] Should be ~20 minutes/month (well within free tier)

## Troubleshooting

If something goes wrong, check:

- [ ] **Workflow fails immediately**
  - [ ] Verify GitHub Secrets are set correctly
  - [ ] Check secret names match exactly
  - [ ] Ensure no extra spaces in secret values

- [ ] **"No links found"**
  - [ ] Verify `gofile_uploads` table has data
  - [ ] Check RLS policies aren't blocking access
  - [ ] Verify links haven't been kept recently (within 5 days)

- [ ] **"Failed to fetch links from Supabase"**
  - [ ] Test Supabase URL in browser
  - [ ] Verify API key is valid
  - [ ] Check Supabase project is active

- [ ] **"Link not found (404)"**
  - [ ] File was already deleted by GoFile
  - [ ] Mark as deleted: `UPDATE gofile_uploads SET status='deleted' WHERE id=X`
  - [ ] This is normal for old links

- [ ] **High failure rate**
  - [ ] Check if GoFile is having issues
  - [ ] Verify network connectivity
  - [ ] Increase `DELAY_BETWEEN_REQUESTS` to avoid rate limiting

## Maintenance

- [ ] **Weekly checks** (first month)
  - [ ] Review Actions tab for failures
  - [ ] Check database for updated timestamps
  - [ ] Monitor success rate

- [ ] **Monthly checks** (ongoing)
  - [ ] Review overall success rate
  - [ ] Clean up deleted links
  - [ ] Update keeper if needed

- [ ] **Quarterly tasks**
  - [ ] Review and optimize batch size
  - [ ] Consider adjusting schedule frequency
  - [ ] Update dependencies: `pip install -r requirements.txt --upgrade`

## Documentation

- [ ] **Team knowledge sharing**
  - [ ] Share README.md with team
  - [ ] Document where secrets are stored
  - [ ] Add keeper to team runbook

- [ ] **Update project docs**
  - [ ] Add keeper to main project README
  - [ ] Document the 10-day expiration issue
  - [ ] Link to keeper repository

## Success Criteria

You're done when:

- [x] Database migration completed successfully
- [x] Keeper files deployed to repository
- [x] GitHub Secrets configured
- [x] First manual run succeeded
- [x] Database shows updated `last_kept` timestamps
- [x] Automatic schedule is working
- [x] Monitoring is in place

## Post-Deployment

- [ ] **Mark deployment date**
  - Date deployed: _______________

- [ ] **Set review date**
  - Review in 2 weeks: _______________
  - Review in 1 month: _______________

- [ ] **Document any issues**
  - Issues encountered: _______________
  - Solutions applied: _______________

## Notes

Use this space for deployment-specific notes:

```
_______________________________________________
_______________________________________________
_______________________________________________
_______________________________________________
```

---

## Quick Reference

**Workflow file**: `.github/workflows/gofile-keeper.yml`
**Main script**: `keeper.py`
**Database migration**: `database_migration.sql`

**GitHub Secrets needed**:
- `SUPABASE_URL`
- `SUPABASE_API_KEY`

**Default schedule**: Every 7 days at 3 AM UTC

**Cost**: $0 (within GitHub free tier)

**Maintenance**: Minimal (check monthly)

---

✅ **Checklist complete!** Your GoFile links are now protected from expiration.
