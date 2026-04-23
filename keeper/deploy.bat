@echo off
REM Deploy script for GoFile Keeper to a new repository (Windows)

echo.
echo ========================================
echo   GoFile Keeper Deployment Script
echo ========================================
echo.

REM Check if git is installed
where git >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: git is not installed
    exit /b 1
)

REM Get target directory
set /p TARGET_DIR="Enter target directory (or press Enter for current directory): "
if "%TARGET_DIR%"=="" set TARGET_DIR=.

REM Create directory if it doesn't exist
if not exist "%TARGET_DIR%" (
    echo Creating directory: %TARGET_DIR%
    mkdir "%TARGET_DIR%"
)

cd /d "%TARGET_DIR%"

REM Check if it's already a git repo
if exist ".git" (
    echo Git repository detected
) else (
    set /p INIT_GIT="Initialize git repository? (y/n): "
    if /i "%INIT_GIT%"=="y" (
        git init
        echo Git repository initialized
    )
)

echo.
echo Copying keeper files...

REM Get script directory
set SCRIPT_DIR=%~dp0

REM Copy main files
copy "%SCRIPT_DIR%keeper.py" .
copy "%SCRIPT_DIR%requirements.txt" .
copy "%SCRIPT_DIR%.env.example" .
copy "%SCRIPT_DIR%.gitignore" .
copy "%SCRIPT_DIR%README.md" .
copy "%SCRIPT_DIR%SETUP_GUIDE.md" .
copy "%SCRIPT_DIR%SEPARATE_REPO_EXAMPLE.md" .
copy "%SCRIPT_DIR%test_keeper.py" .

REM Copy workflow
if not exist ".github\workflows" mkdir ".github\workflows"
copy "%SCRIPT_DIR%.github\workflows\gofile-keeper.yml" ".github\workflows\"

echo Files copied successfully
echo.

REM Create .env file
set /p CREATE_ENV="Create .env file with your credentials? (y/n): "
if /i "%CREATE_ENV%"=="y" (
    set /p SUPABASE_URL="   Supabase URL: "
    set /p SUPABASE_API_KEY="   Supabase API Key: "
    
    (
        echo # Supabase Configuration
        echo SUPABASE_URL=!SUPABASE_URL!
        echo SUPABASE_API_KEY=!SUPABASE_API_KEY!
        echo.
        echo # Keeper Configuration
        echo BATCH_SIZE=100
        echo DELAY_BETWEEN_REQUESTS=2
        echo MIN_KEEP_INTERVAL_DAYS=5
    ) > .env
    
    echo .env file created
    echo Remember: .env is gitignored and won't be committed
)

echo.
echo ========================================
echo   Deployment Complete!
echo ========================================
echo.
echo Next Steps:
echo.
echo 1. Set up GitHub Secrets (if using GitHub Actions):
echo    - Go to repo Settings -^> Secrets -^> Actions
echo    - Add: SUPABASE_URL
echo    - Add: SUPABASE_API_KEY
echo.
echo 2. Enable GitHub Actions:
echo    - Go to Actions tab
echo    - Enable workflows
echo.
echo 3. Test the workflow:
echo    - Actions -^> GoFile Link Keeper -^> Run workflow
echo.
echo 4. Monitor execution:
echo    - Check Actions tab for logs
echo.
echo Documentation:
echo    - README.md - Overview
echo    - SETUP_GUIDE.md - Detailed setup
echo    - SEPARATE_REPO_EXAMPLE.md - Using in separate repo
echo.
echo Happy keeping!
echo.

pause
