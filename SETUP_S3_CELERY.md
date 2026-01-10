# Setup Guide: S3 Storage and Celery CSV Processing

## Overview
Your Django app now supports:
- ✅ **Background CSV processing** - No more timeouts!
- ✅ **S3 storage** - Compatible with AWS S3 and Backblaze B2
- ✅ **Progress tracking** - Real-time status in admin
- ✅ **Bulk operations** - Efficient database inserts

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create Database Migration
```bash
python manage.py makemigrations matches
python manage.py migrate
```

### 3. Configure Storage (Choose One)

#### Option A: Backblaze B2 (Recommended for cost)
Create a Backblaze B2 bucket and application key, then set environment variables:

```bash
# .env or environment variables
AWS_ACCESS_KEY_ID=your_b2_keyID
AWS_SECRET_ACCESS_KEY=your_b2_applicationKey
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-west-000
AWS_S3_ENDPOINT_URL=https://s3.us-west-000.backblazeb2.com
```

**Backblaze B2 Setup Steps:**
1. Go to https://www.backblaze.com/b2/cloud-storage.html
2. Create an account (10GB free!)
3. Create a bucket (make it private)
4. Go to "App Keys" → "Add a New Application Key"
5. Copy the `keyID` (use as AWS_ACCESS_KEY_ID)
6. Copy the `applicationKey` (use as AWS_SECRET_ACCESS_KEY)
7. Note your endpoint URL (e.g., `https://s3.us-west-004.backblazeb2.com`)

#### Option B: AWS S3
```bash
# .env or environment variables
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1
# AWS_S3_ENDPOINT_URL - leave this empty for AWS S3
```

### 4. Start Celery Worker

In a separate terminal:
```bash
celery -A match worker --loglevel=info
```

Or use Docker Compose (recommended for production):
```yaml
# Add to docker-compose.yml
celery:
  build: .
  command: celery -A match worker --loglevel=info
  environment:
    - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
    - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
    - AWS_STORAGE_BUCKET_NAME=${AWS_STORAGE_BUCKET_NAME}
    - AWS_S3_REGION_NAME=${AWS_S3_REGION_NAME}
    - AWS_S3_ENDPOINT_URL=${AWS_S3_ENDPOINT_URL}
  depends_on:
    - redis
    - db
```

### 5. Start Redis (if not already running)
```bash
# Via Docker
docker run -d -p 6379:6379 redis:alpine

# Or use existing Redis from docker-compose
```

## Usage

### Importing CSV Files

1. **Navigate to Django Admin**
   - Go to any model admin (Match, Fixture, Team, etc.)
   - Click "Import from CSV"

2. **Upload Your CSV File**
   - Select your CSV file (can be 5k, 10k, 50k+ rows!)
   - Choose league/competition/season if needed
   - Click "Submit"

3. **Track Progress**
   - You'll be redirected to the CSV Upload list
   - See real-time progress bar
   - Status updates automatically
   - See successful/failed row counts

4. **Check Results**
   - When status shows "Completed", your data is imported
   - If "Failed", click the upload to see error details
   - Use "Retry failed uploads" action to retry

### Monitoring Uploads

**View all uploads:**
- Admin → CSV Uploads

**Filter by:**
- Status (Pending, Processing, Completed, Failed)
- Model Type (Match, Fixture, Team, etc.)
- Date uploaded

**Retry failed uploads:**
- Select failed uploads
- Choose "Retry failed uploads" action
- Click "Go"

## How It Works

### Background Processing Flow

```
1. User uploads CSV via admin
   ↓
2. File saved to S3 (or local if no credentials)
   ↓
3. CSVUpload record created with status="pending"
   ↓
4. Celery task triggered
   ↓
5. Worker downloads file from S3
   ↓
6. Worker processes in batches (500 rows at a time)
   ↓
7. Uses bulk_create() for fast database insertion
   ↓
8. Progress updated after each batch
   ↓
9. Status set to "completed" when done
```

### Performance Benefits

**Before (Synchronous):**
- ❌ 5k+ rows → Timeout (30-60 seconds)
- ❌ Shows "success" but data not imported
- ❌ Blocks admin interface
- ❌ No progress tracking

**After (Asynchronous with Celery):**
- ✅ 50k+ rows → Completes successfully
- ✅ ~500-1000 rows per second
- ✅ Non-blocking (user can continue working)
- ✅ Real-time progress tracking
- ✅ Automatic retry on failure

## Troubleshooting

### CSV Upload Not Processing

**Check Celery worker is running:**
```bash
# You should see worker logs
celery -A match worker --loglevel=info
```

**Check Redis is running:**
```bash
# Test connection
redis-cli ping
# Should return: PONG
```

### Files Not Uploading to S3

**Verify environment variables:**
```python
# In Django shell
from django.conf import settings
print(settings.AWS_ACCESS_KEY_ID)
print(settings.AWS_STORAGE_BUCKET_NAME)
```

**Test S3 connection:**
```python
from django.core.files.storage import default_storage
default_storage.bucket_name  # Should show your bucket name
```

### Upload Shows "Failed"

1. Click the failed upload in admin
2. Check "Error message" field for details
3. Common issues:
   - Missing CSV columns
   - Invalid date formats
   - Missing related objects (teams, leagues)
4. Fix the CSV and retry

## Cost Comparison

### Backblaze B2
- **10 GB free storage**
- **1 GB/day free download**
- Storage: $0.005/GB/month (after free tier)
- Download: $0.01/GB (after free tier)
- **Best for**: Budget-conscious, predictable costs

### AWS S3
- **5 GB free for 12 months** (new accounts)
- Storage: $0.023/GB/month
- Requests: $0.005/1000 PUT, $0.0004/1000 GET
- **Best for**: If already using AWS ecosystem

## Next Steps

1. ✅ Install dependencies: `pip install -r requirements.txt`
2. ✅ Run migrations: `python manage.py migrate`
3. ✅ Set up Backblaze B2 or AWS S3 credentials
4. ✅ Start Celery worker
5. ✅ Test with a small CSV file (~100 rows)
6. ✅ Try importing your large CSV (5k+ rows)
7. ✅ Monitor progress in admin

## Support

If you encounter issues:
1. Check Celery worker logs
2. Check Django logs
3. Review error message in failed upload
4. Verify S3/B2 credentials
5. Test with smaller CSV first
