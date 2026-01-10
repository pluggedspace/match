# matches/storage.py
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorage(S3Boto3Storage):
    """Custom S3 storage for media files (CSV uploads, etc.)"""
    location = 'media'
    default_acl = 'private'
    file_overwrite = False


class CSVUploadStorage(S3Boto3Storage):
    """Custom S3 storage specifically for CSV uploads"""
    location = 'csv-uploads'
    default_acl = 'private'
    file_overwrite = False
