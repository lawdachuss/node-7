#!/bin/bash
# Deploy script for GoFile Keeper to a new repository

set -e

echo "🚀 GoFile Keeper Deployment Script"
echo "===================================="
echo ""

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "❌ Error: git is not installed"
    exit 1
fi

# Get target directory
read -p "📁 Enter target directory (or press Enter for current directory): " TARGET_DIR
TARGET_DIR=${TARGET_DIR:-.}

# Create directory if it doesn't exist
if [ ! -d "$TARGET_DIR" ]; then
    echo "📂 Creating directory: $TARGET_DIR"
    mkdir -p "$TARGET_DIR"
fi

cd "$TARGET_DIR"

# Check if it's already a git repo
if [ -d ".git" ]; then
    echo "✅ Git repository detected"
else
    read -p "🔧 Initialize git repository? (y/n): " INIT_GIT
    if [ "$INIT_GIT" = "y" ]; then
        git init
        echo "✅ Git repository initialized"
    fi
fi

# Copy files
echo ""
echo "📋 Copying keeper files..."

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Copy main files
cp "$SCRIPT_DIR/keeper.py" .
cp "$SCRIPT_DIR/requirements.txt" .
cp "$SCRIPT_DIR/.env.example" .
cp "$SCRIPT_DIR/.gitignore" .
cp "$SCRIPT_DIR/README.md" .
cp "$SCRIPT_DIR/SETUP_GUIDE.md" .
cp "$SCRIPT_DIR/SEPARATE_REPO_EXAMPLE.md" .
cp "$SCRIPT_DIR/test_keeper.py" .

# Copy workflow
mkdir -p .github/workflows
cp "$SCRIPT_DIR/.github/workflows/gofile-keeper.yml" .github/workflows/

echo "✅ Files copied successfully"

# Create .env file
echo ""
read -p "🔐 Create .env file with your credentials? (y/n): " CREATE_ENV
if [ "$CREATE_ENV" = "y" ]; then
    read -p "   Supabase URL: " SUPABASE_URL
    read -p "   Supabase API Key: " SUPABASE_API_KEY
    
    cat > .env << EOF
# Supabase Configuration
SUPABASE_URL=$SUPABASE_URL
SUPABASE_API_KEY=$SUPABASE_API_KEY

# Keeper Configuration
BATCH_SIZE=100
DELAY_BETWEEN_REQUESTS=2
MIN_KEEP_INTERVAL_DAYS=5
EOF
    
    echo "✅ .env file created"
    echo "⚠️  Remember: .env is gitignored and won't be committed"
fi

# Test installation
echo ""
read -p "🧪 Test the keeper locally? (requires Python 3) (y/n): " TEST_LOCAL
if [ "$TEST_LOCAL" = "y" ]; then
    if command -v python3 &> /dev/null; then
        echo "📦 Installing dependencies..."
        python3 -m pip install -r requirements.txt --quiet
        
        if [ -f ".env" ]; then
            echo "🏃 Running keeper (dry run)..."
            export $(cat .env | grep -v '^#' | xargs)
            python3 keeper.py || echo "⚠️  Test run completed with errors (this is normal if no links exist yet)"
        else
            echo "⚠️  No .env file found, skipping test run"
        fi
    else
        echo "⚠️  Python 3 not found, skipping test"
    fi
fi

# Git commit
echo ""
if [ -d ".git" ]; then
    read -p "📝 Commit files to git? (y/n): " COMMIT_GIT
    if [ "$COMMIT_GIT" = "y" ]; then
        git add .
        git commit -m "Add GoFile Link Keeper" || echo "⚠️  Nothing to commit"
        echo "✅ Files committed"
        
        read -p "🚀 Push to remote? (y/n): " PUSH_GIT
        if [ "$PUSH_GIT" = "y" ]; then
            read -p "   Remote URL (e.g., https://github.com/user/repo.git): " REMOTE_URL
            git remote add origin "$REMOTE_URL" 2>/dev/null || git remote set-url origin "$REMOTE_URL"
            git push -u origin main || git push -u origin master
            echo "✅ Pushed to remote"
        fi
    fi
fi

# Final instructions
echo ""
echo "===================================="
echo "✅ Deployment Complete!"
echo "===================================="
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Set up GitHub Secrets (if using GitHub Actions):"
echo "   - Go to repo Settings → Secrets → Actions"
echo "   - Add: SUPABASE_URL"
echo "   - Add: SUPABASE_API_KEY"
echo ""
echo "2. Enable GitHub Actions:"
echo "   - Go to Actions tab"
echo "   - Enable workflows"
echo ""
echo "3. Test the workflow:"
echo "   - Actions → GoFile Link Keeper → Run workflow"
echo ""
echo "4. Monitor execution:"
echo "   - Check Actions tab for logs"
echo ""
echo "📚 Documentation:"
echo "   - README.md - Overview"
echo "   - SETUP_GUIDE.md - Detailed setup"
echo "   - SEPARATE_REPO_EXAMPLE.md - Using in separate repo"
echo ""
echo "🎉 Happy keeping!"
