# utils/player_import.py
import csv
from datetime import datetime
from matches.models import Player, Team

def import_players_from_csv(csv_file_path, season=None):
    """
    Import players from CSV file
    Expected CSV format:
    name,team,position,injured,injury_type,expected_return,appearances,goals,assists
    """
    if not season:
        current_year = datetime.now().year
        season = f"{current_year}-{current_year + 1}"
    
    imported_count = 0
    updated_count = 0
    
    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            try:
                # Find team
                team_name = row['team'].strip()
                team = Team.objects.get(name=team_name)
                
                # Parse boolean field
                injured = row['injured'].lower() in ['true', 'yes', '1', 'y'] if row['injured'] else False
                
                # Create or update player
                player, created = Player.objects.update_or_create(
                    name=row['name'].strip(),
                    team=team,
                    season=season,
                    defaults={
                        'position': row.get('position', 'UNK').strip().upper(),
                        'injured': injured,
                        'injury_type': row.get('injury_type', '').strip() or None,
                        'expected_return': row.get('expected_return') or None,
                        'appearances': int(row.get('appearances', 0)),
                        'goals': int(row.get('goals', 0)),
                        'assists': int(row.get('assists', 0)),
                    }
                )
                
                if created:
                    imported_count += 1
                else:
                    updated_count += 1
                    
            except Team.DoesNotExist:
                print(f"Team not found: {row['team']}")
            except Exception as e:
                print(f"Error importing player {row.get('name', 'unknown')}: {e}")
    
    return imported_count, updated_count