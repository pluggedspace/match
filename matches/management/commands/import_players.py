# management/commands/import_players.py
from django.core.management.base import BaseCommand
from utils.player_import import import_players_from_csv

class Command(BaseCommand):
    help = 'Import players from CSV file'
    
    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file')
        parser.add_argument('--season', type=str, help='Season format: 2023-2024')
    
    def handle(self, *args, **options):
        csv_file = options['csv_file']
        season = options['season']
        
        self.stdout.write(f"Importing players from {csv_file}...")
        
        imported, updated = import_players_from_csv(csv_file, season)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Import complete! {imported} new players, {updated} updated"
            )
        )