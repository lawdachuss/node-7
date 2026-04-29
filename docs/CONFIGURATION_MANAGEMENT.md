# Configuration Management Guide

## 📋 Overview

Your application uses configuration files in the `conf/` directory that are **NOT** automatically deployed by CI/CD (they're in `.gitignore` for security). This guide shows you how to manage them.

---

## 📁 Configuration Files

### `conf/settings.json`
Contains application settings including:
- Supabase credentials
- Upload service API keys (GoFile, Streamtape, etc.)
- Discord webhook URL
- Recording settings (quality, format, etc.)
- Disk usage thresholds

### `conf/channels.json`
Contains the list of channels to monitor and record.

---

## 🚀 Quick Upload

### Upload Configuration to EC2

**Windows (PowerShell):**
```powershell
.\scripts\upload-config.ps1
```

**Manual Upload:**
```powershell
# Upload settings
scp -i aws-secrets/aws-key.pem conf/settings.json ubuntu@54.210.37.19:/tmp/
ssh -i aws-secrets/aws-key.pem ubuntu@54.210.37.19 "sudo mv /tmp/settings.json /home/ubuntu/goondvr/conf/ && sudo chown ubuntu:ubuntu /home/ubuntu/goondvr/conf/settings.json"

# Upload channels
scp -i aws-secrets/aws-key.pem conf/channels.json ubuntu@54.210.37.19:/tmp/
ssh -i aws-secrets/aws-key.pem ubuntu@54.210.37.19 "sudo mv /tmp/channels.json /home/ubuntu/goondvr/conf/ && sudo chown ubuntu:ubuntu /home/ubuntu/goondvr/conf/channels.json"

# Restart application
ssh -i aws-secrets/aws-key.pem ubuntu@54.210.37.19 "cd /home/ubuntu/goondvr && sudo docker compose restart recorder"
```

---

## 🔄 Workflow

### Initial Setup (First Time)

1. **Configure locally** - Edit `conf/settings.json` and `conf/channels.json`
2. **Upload to EC2** - Run `.\scripts\upload-config.ps1`
3. **Verify** - Check http://54.210.37.19:8080

### Updating Configuration

1. **Edit locally** - Modify `conf/settings.json` or `conf/channels.json`
2. **Upload changes** - Run `.\scripts\upload-config.ps1`
3. **Application restarts automatically** - Changes take effect immediately

### After Code Deployment

The CI/CD pipeline **preserves** your configuration:
- Backs up `conf/` before deployment
- Restores `conf/` after deployment
- Your settings remain intact

---

## 🔐 Security Best Practices

### ✅ DO:
- Keep `conf/` in `.gitignore` (already configured)
- Store sensitive credentials only in `conf/settings.json`
- Use the upload script to deploy configuration
- Keep a local backup of your configuration

### ❌ DON'T:
- Commit `conf/settings.json` to Git (contains secrets!)
- Share your configuration files publicly
- Hardcode credentials in the application code

---

## 📊 Verify Configuration

### Check if Configuration Exists on EC2

```bash
ssh -i aws-secrets/aws-key.pem ubuntu@54.210.37.19 "ls -la /home/ubuntu/goondvr/conf/"
```

### View Current Settings

```bash
ssh -i aws-secrets/aws-key.pem ubuntu@54.210.37.19 "cat /home/ubuntu/goondvr/conf/settings.json"
```

### Check Application Logs

```bash
ssh -i aws-secrets/aws-key.pem ubuntu@54.210.37.19 "cd /home/ubuntu/goondvr && sudo docker compose logs recorder --tail=50"
```

---

## 🛠️ Troubleshooting

### "Supabase is disabled" Error

**Cause:** Configuration file missing or not loaded

**Solution:**
```powershell
.\scripts\upload-config.ps1
```

### Configuration Not Taking Effect

**Solution:** Restart the application
```bash
ssh -i aws-secrets/aws-key.pem ubuntu@54.210.37.19 "cd /home/ubuntu/goondvr && sudo docker compose restart recorder"
```

### Lost Configuration After Deployment

**Cause:** Backup/restore failed during deployment

**Solution:** Re-upload configuration
```powershell
.\scripts\upload-config.ps1
```

---

## 📝 Configuration Reference

### Supabase Settings

```json
{
  "enable_supabase": true,
  "supabase_url": "https://your-project.supabase.co",
  "supabase_api_key": "your-anon-key"
}
```

### Upload Services

```json
{
  "enable_gofile_upload": true,
  "turboviplay_api_key": "your-key",
  "voesx_api_key": "your-key",
  "streamtape_login": "your-login",
  "streamtape_api_key": "your-key"
}
```

### Recording Settings

```json
{
  "finalize_mode": "remux",
  "ffmpeg_container": "mp4",
  "ffmpeg_encoder": "libx264",
  "ffmpeg_quality": 18,
  "ffmpeg_preset": "slow"
}
```

### Disk Management

```json
{
  "disk_warning_percent": 80,
  "disk_critical_percent": 90
}
```

---

## 🔄 Backup and Restore

### Backup Configuration from EC2

```bash
# Download from EC2 to local
scp -i aws-secrets/aws-key.pem ubuntu@54.210.37.19:/home/ubuntu/goondvr/conf/settings.json conf/settings-backup.json
scp -i aws-secrets/aws-key.pem ubuntu@54.210.37.19:/home/ubuntu/goondvr/conf/channels.json conf/channels-backup.json
```

### Restore Configuration

```powershell
# Restore from backup
Copy-Item conf/settings-backup.json conf/settings.json
Copy-Item conf/channels-backup.json conf/channels.json

# Upload to EC2
.\scripts\upload-config.ps1
```

---

## 🎯 Common Tasks

### Add a New Channel

1. Edit `conf/channels.json` locally
2. Add the channel to the array
3. Upload: `.\scripts\upload-config.ps1`
4. Check Web UI to verify

### Update Supabase Credentials

1. Edit `conf/settings.json` locally
2. Update `supabase_url` and `supabase_api_key`
3. Upload: `.\scripts\upload-config.ps1`
4. Verify in Web UI

### Change Recording Quality

1. Edit `conf/settings.json` locally
2. Modify `ffmpeg_quality` (lower = better quality, 18 is recommended)
3. Upload: `.\scripts\upload-config.ps1`
4. New recordings will use the new quality

### Update Discord Webhook

1. Edit `conf/settings.json` locally
2. Update `discord_webhook_url`
3. Upload: `.\scripts\upload-config.ps1`
4. Test by triggering a notification

---

## 📚 Related Documentation

- [CI/CD Setup Guide](CI_CD_SETUP.md)
- [Deployment Guide](../DEPLOYMENT_GUIDE.md)
- [Upload Feature Documentation](UPLOAD_FEATURE.md)

---

## ✅ Checklist

After uploading configuration, verify:

- [ ] Configuration files exist on EC2
- [ ] Application restarted successfully
- [ ] Web UI is accessible
- [ ] Supabase is enabled (check Web UI)
- [ ] Channels are being monitored
- [ ] Recordings are working

---

**Last Updated:** 2026-04-29  
**Status:** Configuration management active
