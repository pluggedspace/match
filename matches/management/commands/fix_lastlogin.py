from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = "Fix auth_user.last_login column to allow NULL values (drop NOT NULL)."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Check the current column definition
            cursor.execute("""
                SELECT is_nullable
                FROM information_schema.columns
                WHERE table_name = 'auth_user'
                AND column_name = 'last_login';
            """)
            result = cursor.fetchone()
            if result and result[0] == "NO":
                self.stdout.write(self.style.WARNING("Fixing last_login column..."))
                cursor.execute("ALTER TABLE auth_user ALTER COLUMN last_login DROP NOT NULL;")
                self.stdout.write(self.style.SUCCESS("✅ last_login column fixed (now nullable)."))
            else:
                self.stdout.write(self.style.SUCCESS("✔ last_login column already nullable."))