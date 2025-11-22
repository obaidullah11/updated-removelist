# Google AI API Key Setup Guide

## Problem: API Key Reported as Leaked

If you're seeing this error:
```
403 Your API key was reported as leaked. Please use another API key.
```

This means your Google AI API key has been compromised and Google has disabled it. You need to generate a new API key.

## Solution: Get a New API Key

### Step 1: Generate a New API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Select your Google Cloud project (or create a new one)
5. Copy the new API key

### Step 2: Set Up Your API Key Securely

**Option A: Using .env file (Recommended)**

1. Create a `.env` file in the `backend/` directory (if it doesn't exist)
2. Add your API key:
   ```
   GOOGLE_AI_API_KEY=your-new-api-key-here
   ```
3. **IMPORTANT**: Make sure `.env` is in your `.gitignore` file to prevent committing it to version control

**Option B: Using Environment Variables**

Set the environment variable directly:
- **Windows (PowerShell):**
  ```powershell
  $env:GOOGLE_AI_API_KEY="your-new-api-key-here"
  ```
- **Windows (Command Prompt):**
  ```cmd
  set GOOGLE_AI_API_KEY=your-new-api-key-here
  ```
- **Linux/Mac:**
  ```bash
  export GOOGLE_AI_API_KEY="your-new-api-key-here"
  ```

### Step 3: Restart Your Server

After setting the API key, restart your Django development server:
```bash
python manage.py runserver
```

### Step 4: Verify It Works

1. Create a new move in your application
2. Check the logs - you should see:
   ```
   INFO Google AI (Gemini) initialized successfully with model: gemini-2.5-flash
   ```
3. The AI checklist and floor plan analysis should now work

## Security Best Practices

1. **Never commit API keys to version control**
   - Always use `.env` files or environment variables
   - Add `.env` to your `.gitignore` file
   - Never hardcode API keys in your code

2. **Rotate keys regularly**
   - If a key is leaked, generate a new one immediately
   - Consider rotating keys periodically for security

3. **Restrict API key permissions**
   - In Google Cloud Console, restrict your API key to only the services you need
   - Set up API key restrictions to limit usage

## Troubleshooting

### "GOOGLE_AI_API_KEY not configured"
- Make sure your `.env` file is in the `backend/` directory
- Verify the variable name is exactly `GOOGLE_AI_API_KEY`
- Restart your server after adding the key

### "API key authentication failed"
- Verify your API key is correct (no extra spaces)
- Check that the API key has access to Gemini models
- Ensure you're using a valid Google Cloud project

### "Model not available"
- Some models may not be available in all regions
- Try using a different model name in the service initialization
- Check Google AI Studio for available models in your region

## Need Help?

If you continue to experience issues:
1. Check the Django logs for detailed error messages
2. Verify your API key at [Google AI Studio](https://aistudio.google.com/apikey)
3. Ensure your Google Cloud project has billing enabled (required for API access)



