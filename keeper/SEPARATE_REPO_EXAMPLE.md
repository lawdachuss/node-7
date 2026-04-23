# Using Keeper in a Separate Repository

This guide shows how to use the GoFile Keeper in a completely separate repository from your main application.

## Why Use a Separate Repository?

- **Separation of concerns**: Keep monitoring separate from your main app
- **Independent deployment**: Update keeper without touching main app
- **Reusability**: Use the same keeper for multiple applications
- **Security**: Limit access to production credentials
- **Cleaner history**: Keep keeper logs separate from app commits

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Your Main App Repo                    │
│  (goondvr - records streams, uploads to GoFile)         │
│                                                          │
│  ┌────────────┐         ┌──────────────┐               │
│  │  Recorder  │────────▶│   Supabase   │               │
│  │            │         │   Database   │               │
│  └────────────┘         └──────┬───────┘               │
│                                 │                        │
└─────────────────────────────────┼────────────────────────┘
                                  │
                                  │ Reads links
                                  │
┌─────────────────────────────────┼────────────────────────┐
│              Separate Keeper Repo                        │
│  (gofile-keeper - keeps links alive)                     │
│                                 │                        │
│  ┌──────────────────┐          │                        │
│  │  GitHub Actions  │          │                        │
│  │  (Every 7 days)  │          │                        │
│  └────────┬─────────┘          │                        │
│           │                     │                        │
│           ▼                     ▼                        │
│  ┌─────────────────────────────────────┐                │
│  │         keeper.py                   │                │
│  │  1. Fetch links from Supabase       │                │
│  │  2. Download 1KB from each file     │                │
│  │  3. Update last_kept timestamp      │                │
│  └─────────────────────────────────────┘                │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## Step-by-Step Setup

### 1. Create New Repository

```bash
# On GitHub, create a new repository named "gofile-keeper"
# Then clone it:

git clone https://github.com/yourusername/gofile-keeper.git
cd gofile-keeper
```

### 2. Copy Keeper Files

Copy only the necessary files from your main repo:

```bash
# From your main repo directory:
cd /path/to/goondvr

# Copy keeper files to the new repo
cp -r keeper/* /path/to/gofile-keeper/

# Or if you want to be selective:
cp keeper/keeper.py /path/to/gofile-keeper/
cp keeper/requirements.txt /path/to/gofile-keeper/
cp keeper/README.md /path/to/gofile-keeper/
cp keeper/.env.example /path/to/gofile-keeper/
cp keeper/.gitignore /path/to/gofile-keeper/
mkdir -p /path/to/gofile-keeper/.github/workflows
cp keeper/.github/workflows/gofile-keeper.yml /path/to/gofile-keeper/.github/workflows/
```

### 3. Initialize the Repository

```bash
cd /path/to/gofile-keeper

# Create a README
cat > README.md << 'EOF'
# GoFile Link Keeper

Automated system to keep GoFile links alive by preventing 10-day inactivity deletion.

## What This Does

- Runs every 7 days via GitHub Actions
- Fetches GoFile links from Supabase database
- Downloads first 1KB of each file to register activity
- Prevents GoFile's automatic deletion after 10 days of inactivity

## Setup

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed instructions.

## Quick Start

1. Add GitHub Secrets: `SUPABASE_URL` and `SUPABASE_API_KEY`
2. Enable GitHub Actions
3. Workflow runs automatically every 7 days

## Configuration

Edit `.github/workflows/gofile-keeper.yml` to customize:
- Schedule frequency
- Batch size
- Delay between requests

## Monitoring

Check the Actions tab for execution logs and status.
EOF

# Commit and push
git add .
git commit -m "Initial commit: GoFile Link Keeper"
git push origin main
```

### 4. Configure GitHub Secrets

In your **new repository** (gofile-keeper):

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add secrets:
   - `SUPABASE_URL`: Same as your main app
   - `SUPABASE_API_KEY`: Same as your main app (or create a read-only key)

### 5. Enable GitHub Actions

1. Go to **Actions** tab
2. Enable workflows if prompted
3. You should see "GoFile Link Keeper" workflow

### 6. Test It

Trigger a manual run:

1. **Actions** → **GoFile Link Keeper** → **Run workflow**
2. Check the logs to ensure it works

## Repository Structure

Your separate keeper repo should look like this:

```
gofile-keeper/
├── .github/
│   └── workflows/
│       └── gofile-keeper.yml    # GitHub Actions workflow
├── .gitignore                    # Ignore .env and Python cache
├── .env.example                  # Example environment variables
├── keeper.py                     # Main keeper script
├── requirements.txt              # Python dependencies
├── test_keeper.py               # Unit tests
├── README.md                     # Main documentation
├── SETUP_GUIDE.md               # Setup instructions
└── SEPARATE_REPO_EXAMPLE.md     # This file
```

## Sharing Supabase Access

### Option 1: Use Same Credentials (Simple)

Use the same `SUPABASE_API_KEY` from your main app.

**Pros:**
- Simple setup
- No additional configuration

**Cons:**
- Keeper has full database access
- Less secure

### Option 2: Create Read-Only Key (Recommended)

Create a separate Supabase key with limited permissions:

1. Go to Supabase Dashboard → **Settings** → **API**
2. Create a new service role key (or use anon key with RLS)
3. Set up Row Level Security (RLS) policies:

```sql
-- Allow reading gofile_uploads
CREATE POLICY "Allow keeper to read uploads"
ON gofile_uploads
FOR SELECT
TO authenticated
USING (true);

-- Allow keeper to update keep status
CREATE POLICY "Allow keeper to update keep status"
ON gofile_uploads
FOR UPDATE
TO authenticated
USING (true)
WITH CHECK (true);
```

4. Use this key in the keeper repo secrets

### Option 3: Create Dedicated Database View

Create a view that exposes only what the keeper needs:

```sql
-- Create a view with only necessary columns
CREATE VIEW gofile_keeper_view AS
SELECT 
  id,
  streamer_name,
  gofile_link,
  upload_date,
  last_kept,
  keep_alive_count,
  status
FROM gofile_uploads
WHERE status != 'deleted';

-- Grant access to the view
GRANT SELECT, UPDATE ON gofile_keeper_view TO anon;
```

Then modify `keeper.py` to use the view instead of the table.

## Multiple Applications

You can use one keeper repo for multiple applications:

### Modify keeper.py to support multiple tables:

```python
# In keeper.py, add configuration for multiple sources

SOURCES = [
    {
        'name': 'goondvr',
        'url': os.getenv('SUPABASE_URL_1'),
        'key': os.getenv('SUPABASE_API_KEY_1'),
        'table': 'gofile_uploads'
    },
    {
        'name': 'other_app',
        'url': os.getenv('SUPABASE_URL_2'),
        'key': os.getenv('SUPABASE_API_KEY_2'),
        'table': 'uploads'
    }
]

def main():
    for source in SOURCES:
        logger.info(f"Processing source: {source['name']}")
        supabase = SupabaseClient(source['url'], source['key'])
        # ... rest of the logic
```

### Add secrets for each source:

- `SUPABASE_URL_1`, `SUPABASE_API_KEY_1`
- `SUPABASE_URL_2`, `SUPABASE_API_KEY_2`

## Monitoring Multiple Repos

If you have multiple apps using GoFile, you can:

1. **Centralize in one keeper repo** (recommended)
   - One workflow, multiple data sources
   - Easier to maintain

2. **Separate keeper per app**
   - More isolated
   - Can have different schedules

3. **Hybrid approach**
   - Production apps: Dedicated keeper
   - Dev/test apps: Shared keeper

## Advanced: Webhook Notifications

Add Discord/Slack notifications to your keeper:

```yaml
# In .github/workflows/gofile-keeper.yml

- name: Notify on completion
  if: always()
  run: |
    STATUS="${{ job.status }}"
    if [ "$STATUS" = "success" ]; then
      MESSAGE="✅ GoFile Keeper completed successfully"
    else
      MESSAGE="❌ GoFile Keeper failed"
    fi
    
    curl -X POST ${{ secrets.DISCORD_WEBHOOK }} \
      -H "Content-Type: application/json" \
      -d "{\"content\": \"$MESSAGE\"}"
```

Add `DISCORD_WEBHOOK` secret to your repo.

## Cost Analysis

### GitHub Actions (Free Tier)
- **Free minutes**: 2,000/month
- **Keeper usage**: ~5 minutes per run
- **Runs per month**: ~4 (every 7 days)
- **Total usage**: ~20 minutes/month
- **Cost**: $0 (well within free tier)

### Bandwidth
- **Per file**: 1KB download
- **1,000 files**: 1MB total
- **Per month**: ~4MB
- **Cost**: Negligible

### Supabase
- **Read operations**: ~100 per run
- **Write operations**: ~100 per run
- **Per month**: ~800 operations
- **Cost**: $0 (within free tier)

**Total monthly cost**: $0 ✅

## Maintenance

### Update the Keeper

```bash
cd gofile-keeper
git pull origin main

# Make changes to keeper.py
vim keeper.py

# Test locally
python keeper.py

# Commit and push
git add .
git commit -m "Update keeper logic"
git push origin main
```

Changes take effect on the next scheduled run.

### View Execution History

1. Go to **Actions** tab
2. See all past runs with timestamps
3. Click any run to see detailed logs

### Debugging

If something goes wrong:

1. Check GitHub Actions logs
2. Test locally:
   ```bash
   export SUPABASE_URL="..."
   export SUPABASE_API_KEY="..."
   python keeper.py
   ```
3. Check Supabase logs
4. Verify GoFile links manually

## Security Best Practices

1. **Never commit credentials**
   - Use GitHub Secrets
   - Add `.env` to `.gitignore`

2. **Use read-only keys when possible**
   - Keeper only needs SELECT and UPDATE on one table

3. **Enable RLS policies**
   - Restrict what the keeper can access

4. **Rotate keys periodically**
   - Update secrets every 6-12 months

5. **Monitor access logs**
   - Check Supabase logs for unusual activity

## Conclusion

Using a separate repository for the keeper provides:
- ✅ Clean separation of concerns
- ✅ Independent deployment and updates
- ✅ Reusability across projects
- ✅ Better security isolation
- ✅ Cleaner git history

The keeper runs autonomously, requires zero maintenance, and costs nothing on GitHub's free tier.
