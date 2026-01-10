# Quick Reference: Backblaze B2 Setup

## Create Backblaze B2 Account & Get Credentials

### 1. Sign Up (FREE!)
- Go to: https://www.backblaze.com/b2/sign-up.html
- **Free tier:** 10 GB storage + 1 GB/day downloads
- No credit card required for trial

### 2. Create a Bucket
1. Login to Backblaze dashboard
2. Click "Buckets" → "Create a Bucket"
3. **Bucket name:** `match-uploads` (or your choice)
4. **Files in bucket:** **Private** (recommended)
5. **Encryption:** Enable (recommended)
6. Click "Create a Bucket"

### 3. Get Application Key
1. Click "App Keys" in left sidebar
2. Click "Add a New Application Key"
3. **Name:** `match-app-key`
4. **Allow access to:** Select your bucket
5. **Type of access:** Read and Write
6. Click "Create New Key"

### 4. Save Credentials
**IMPORTANT:** Copy these immediately (you can't see the key again!)

```
keyID: 001234567890abcd1234567
applicationKey: K001abcdefghijklmnopqrstuvwxyz1234567890
```

### 5. Find Your Endpoint URL
Look at the bucket details, you'll see something like:
```
Endpoint: s3.us-west-004.backblazeb2.com
```

Your full endpoint URL is:
```
https://s3.us-west-004.backblazeb2.com
```

## Environment Variables

Add these to your `.env` file or environment:

```bash
# Backblaze B2 Configuration
AWS_ACCESS_KEY_ID=001234567890abcd1234567
AWS_SECRET_ACCESS_KEY=K001abcdefghijklmnopqrstuvwxyz1234567890
AWS_STORAGE_BUCKET_NAME=match-uploads
AWS_S3_REGION_NAME=us-west-004
AWS_S3_ENDPOINT_URL=https://s3.us-west-004.backblazeb2.com
```

## Docker Compose Example

```yaml
services:
  web:
    build: .
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_STORAGE_BUCKET_NAME=${AWS_STORAGE_BUCKET_NAME}
      - AWS_S3_REGION_NAME=${AWS_S3_REGION_NAME}
      - AWS_S3_ENDPOINT_URL=${AWS_S3_ENDPOINT_URL}

  celery:
    build: .
    command: celery -A match worker --loglevel=info
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_STORAGE_BUCKET_NAME=${AWS_STORAGE_BUCKET_NAME}
      - AWS_S3_REGION_NAME=${AWS_S3_REGION_NAME}
      - AWS_S3_ENDPOINT_URL=${AWS_S3_ENDPOINT_URL}
```

## Test Connection

```python
# Django shell
python manage.py shell

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

# Test upload
default_storage.save('test.txt', ContentFile(b'Hello Backblaze!'))

# Should print: test.txt (or similar)
```

## Cost Calculator

### Backblaze B2 Pricing
- Storage: $0.005/GB/month
- Download: $0.01/GB
- Free tier: First 10 GB storage + 1 GB/day downloads

### Example: 50 GB storage, 10 GB downloads/month
```
Storage: (50 - 10) × $0.005 = $0.20
Downloads: (10 × 30 - 30) × $0.01 = $2.70
Total: ~$2.90/month
```

Compare to AWS S3: ~$15/month for same usage! 💰

## Troubleshooting

### Error: "Access Denied"
- Check bucket permissions (should be Private with your key having access)
- Verify application key has Read/Write access
- Confirm bucket name is correct

### Error: "Invalid Endpoint"
- Verify endpoint URL matches your bucket region
- Format: `https://s3.{region}.backblazeb2.com`
- Check region in bucket details

### Files not appearing in bucket
- Check Celery worker logs
- Verify environment variables are set
- Test with Django shell (see above)

## Quick Start Commands

```bash
# 1. Install dependencies
pip install boto3 django-storages[s3]

# 2. Set environment variables (see above)

# 3. Create migrations
python manage.py makemigrations matches
python manage.py migrate

# 4. Start Celery worker
celery -A match worker --loglevel=info

# 5. Upload CSV in admin!
```

## Support Resources

- Backblaze B2 Docs: https://www.backblaze.com/b2/docs/
- S3-Compatible API: https://www.backblaze.com/b2/docs/s3_compatible_api.html
- django-storages Docs: https://django-storages.readthedocs.io/

---

**Ready to go!** 🚀 Now you can upload unlimited CSV rows without timeout issues!
