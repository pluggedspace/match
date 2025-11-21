import os
import glob
from django.core.management.base import BaseCommand
from backup import drive_utils

class Command(BaseCommand):
    help = "Uploads the latest backup file to Google Drive"

    def handle(self, *args, **kwargs):
        backup_dir = "/app/backups"
        pattern = os.path.join(backup_dir, "full_backup_*.zip")

        # Find all matching backup files
        backup_files = glob.glob(pattern)
        if not backup_files:
            self.stdout.write(self.style.ERROR("❌ No backup files found in /app/backups"))
            return

        # Pick the newest file
        latest_file = max(backup_files, key=os.path.getctime)
        self.stdout.write(f"📂 Found latest backup: {os.path.basename(latest_file)}")

        try:
            result = drive_utils.upload_to_drive(latest_file)
            self.stdout.write(self.style.SUCCESS(f"✅ Uploaded to Drive: {result['webViewLink']}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Upload failed: {e}"))