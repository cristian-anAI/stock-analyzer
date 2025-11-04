# 🔒 Security - Environment Variables

## ⚠️ IMPORTANT: Never Commit Credentials!

The following files contain **sensitive credentials** and must **NEVER** be committed to Git:

- ❌ `.env`
- ❌ `.env.local`
- ❌ `.env.prod`
- ❌ Any `.env.*` file with real credentials

## ✅ Setup Instructions

### 1. Copy the example file:
```bash
cp .env.example .env
```

### 2. Fill in your actual credentials:
```bash
# Edit .env with your real values
TELEGRAM_BOT_TOKEN=8449587269:AAF...  # Your actual bot token
TELEGRAM_CHAT_ID=-1003106978167        # Your actual chat ID
```

### 3. Verify .env is ignored:
```bash
git status
# Should NOT show .env file
```

## 🔑 Getting Telegram Credentials

### Bot Token:
1. Talk to [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy the token (format: `123456:ABC-DEF...`)

### Chat ID:
1. Add your bot to a group
2. Send a message in the group
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Look for `"chat":{"id":-1234567890}` in the JSON
5. Copy the negative number (group chat ID)

## 📝 Files Explanation

- **`.env.example`** ✅ - Template (safe to commit)
- **`.env`** ❌ - Development credentials (NEVER commit)
- **`.env.local`** ❌ - Local credentials (NEVER commit)
- **`.env.prod`** ❌ - Production credentials (NEVER commit)

## 🚨 If You Accidentally Committed Credentials

1. **Immediately revoke the credentials** (regenerate bot token)
2. Remove from git history (see instructions below)
3. Update `.gitignore`
4. **Never use the old credentials again**

### Remove from Git History:
```bash
# Remove file from tracking
git rm --cached .env.prod

# Commit the removal
git commit -m "security: Remove credentials from tracking"

# Force push (if already pushed to remote)
git push origin feature/ca/caja --force
```

## ⚡ After Credentials Leak

If credentials were pushed to GitHub/remote:

1. **🔴 URGENT: Revoke the Telegram bot token**
   - Go to @BotFather
   - Send `/revoke` and select your bot
   - Create a new token

2. **Update your local .env with new token**

3. **Clean git history** (already done in commit b0832f7)

4. **Force push** to overwrite remote history

---

**Remember**: Credentials in git history can be found even after deletion. Always assume leaked credentials are compromised and regenerate them immediately.
