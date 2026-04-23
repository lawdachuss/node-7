# Quick Setup Guide

Follow these steps to set up the GoFile Link Keeper in a new repository.

## Step 1: Create a New Repository (Optional)

If you want to keep this separate from your main app:

```bash
# Create a new repo on GitHub, then:
git clone https://github.com/yourusername/gofile-keeper.git
cd gofile-keeper
```

Or use it in your existing repository.

## Step 2: Copy the Keeper Files

Copy the entire `keeper` folder to your repository:

```bash
# If using a separate repo:
cp -r /path/to/original/keeper/* .

# If using same repo:
# Files are already in the keeper/ folder
```

## Step 3: Set Up GitHub Secrets

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add these two secrets:

   **Secret 1:**
   - Name: `SUPABASE_URL`
   - Value: `https://your-project.supabase.co`

   **Secret 2:**
   - Name: `SUPABASE_API_KEY`
   - Value: Your Supabase anon key or service role key

## Step 4: Copy the Workflow File

```bash
# Create .github/workflows directory if it doesn't exist
mkdir -p .github/workflows

# Copy the workflow file
cp keeper/.github/workflows/gofile-keeper.yml .github/workflows/
```

## Step 5: Update Database Schema (If Needed)

If your `gofile_uploads` table doesn't have tracking columns, add them:

```sql
-- Connect to your Supabase project and run:

ALTER TABLE gofile_uploads 
ADD COLUMN IF NOT EXISTS last_kept TIMESTAMP,
ADD COLUMN IF NOT EXISTS keep_alive_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active';

-- Create an index for better performance
CREATE INDEX IF NOT EXISTS idx_gofile_uploads_last_kept 
ON gofile_uploads(last_kept);

CREATE INDEX IF NOT EXISTS idx_gofile_uploads_status 
ON gofile_uploads(status);
```

## Step 6: Test Locally (Optional)

Before relying on GitHub Actions, test locally:

```bash
cd keeper

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_API_KEY="your-anon-key"

# Run the keeper
python keeper.py
```

Expected output:
```
🚀 GoFile Link Keeper Started
⚙️  Configuration:
   - Batch size: 100
   - Delay between requests: 2.0s
   - Min keep interval: 5 days

📥 Fetching links from Supabase...
📋 Found 45 links to process

[1/45] Processing: streamer1 - https://gofile.io/d/abc123...
  ✅ Kept alive successfully
...
```

## Step 7: Commit and Push

```bash
git add .github/workflows/gofile-keeper.yml
git commit -m "Add GoFile Link Keeper workflow"
git push
```

## Step 8: Enable GitHub Actions

1. Go to the **Actions** tab in your repository
2. If prompted, click **"I understand my workflows, go ahead and enable them"**
3. You should see "GoFile Link Keeper" in the workflows list

## Step 9: Test the Workflow

Trigger a manual run to test:

1. Go to **Actions** tab
2. Click **GoFile Link Keeper** in the left sidebar
3. Click **Run workflow** button (top right)
4. Select your branch (usually `main`)
5. Click **Run workflow**

Wait for it to complete and check the logs.

## Step 10: Verify It's Working

Check the logs for:
- ✅ Successfully kept alive: X/Y links
- No critical errors
- Database updated with `last_kept` timestamps

Query your database:
```sql
SELECT 
  streamer_name,
  gofile_link,
  last_kept,
  keep_alive_count,
  status
FROM gofile_uploads
WHERE last_kept IS NOT NULL
ORDER BY last_kept DESC
LIMIT 10;
```

## Troubleshooting

### "No links need keeping alive"
- Check your database has records in `gofile_uploads` table
- Verify the `status` column is 'active' or NULL
- Check if links were kept recently (within 5 days)

### "Failed to fetch links from Supabase"
- Verify `SUPABASE_URL` secret is correct
- Verify `SUPABASE_API_KEY` secret is correct
- Check Supabase RLS policies allow reading the table

### "Link not found (404)"
- The file was already deleted by GoFile
- Mark it as deleted: `UPDATE gofile_uploads SET status='deleted' WHERE id=X`

### Workflow doesn't run automatically
- Check the cron schedule in `gofile-keeper.yml`
- GitHub Actions may have a delay of up to 15 minutes
- Ensure Actions are enabled in repository settings

## Customization

### Change Schedule

Edit `.github/workflows/gofile-keeper.yml`:

```yaml
schedule:
  - cron: '0 3 */5 * *'  # Every 5 days instead of 7
```

### Process More Links Per Run

Edit `.github/workflows/gofile-keeper.yml`:

```yaml
env:
  BATCH_SIZE: '200'  # Process 200 links instead of 100
```

### Add Notifications

Add a notification step to the workflow:

```yaml
- name: Notify on failure
  if: failure()
  run: |
    curl -X POST ${{ secrets.DISCORD_WEBHOOK }} \
      -H "Content-Type: application/json" \
      -d '{"content": "⚠️ GoFile Keeper failed!"}'
```

## Monitoring

### View Execution History

1. Go to **Actions** tab
2. Click **GoFile Link Keeper**
3. See all past runs with status and logs

### Set Up Notifications

GitHub sends email notifications for workflow failures by default.

To customize:
1. Go to **Settings** → **Notifications**
2. Configure **Actions** notifications

## Next Steps

- Monitor the first few runs to ensure everything works
- Adjust the schedule if needed (every 5 days is safer than 7)
- Set up monitoring/alerting for failures
- Consider adding a dashboard to visualize kept links

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review GitHub Actions logs
3. Verify Supabase connection and permissions
4. Test locally with `python keeper.py`

---

**That's it!** Your GoFile links will now be kept alive automatically. 🎉
