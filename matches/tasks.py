# matches/tasks.py
import csv
import traceback
from datetime import datetime
from io import StringIO
from celery import shared_task
from django.utils import timezone
from django.core.files.storage import default_storage

from .models import CSVUpload, Match, Team, Fixture, Player, Gameweek, League, Competition, Country
from django.utils.dateparse import parse_datetime


@shared_task(bind=True)
def process_csv_upload(self, upload_id):
    """
    Background task to process CSV uploads efficiently using bulk_create
    """
    try:
        upload = CSVUpload.objects.get(id=upload_id)
        upload.status = 'processing'
        upload.celery_task_id = self.request.id
        upload.save()
        
        # Read file from S3 or local storage
        file_content = upload.file.read().decode('utf-8')
        csvfile = StringIO(file_content)
        reader = csv.DictReader(csvfile)
        
        # Count total rows first
        rows = list(reader)
        upload.total_rows = len(rows)
        upload.save()
        
        # Process based on model type
        if upload.model_type == 'match':
            process_match_csv(upload, rows)
        elif upload.model_type == 'fixture':
            process_fixture_csv(upload, rows)
        elif upload.model_type == 'team':
            process_team_csv(upload, rows)
        elif upload.model_type == 'player':
            process_player_csv(upload, rows)
        elif upload.model_type == 'gameweek':
            process_gameweek_csv(upload, rows)
        else:
            raise ValueError(f"Unknown model type: {upload.model_type}")
        
        # Mark as completed
        upload.status = 'completed'
        upload.completed_at = timezone.now()
        upload.save()
        
        return {
            'status': 'completed',
            'total_rows': upload.total_rows,
            'successful_rows': upload.successful_rows,
            'failed_rows': upload.failed_rows
        }
        
    except Exception as e:
        # Handle errors
        if upload_id:
            try:
                upload = CSVUpload.objects.get(id=upload_id)
                upload.status = 'failed'
                upload.error_message = f"{str(e)}\n\n{traceback.format_exc()}"
                upload.completed_at = timezone.now()
                upload.save()
            except:
                pass
        raise


def process_match_csv(upload, rows):
    """Process Match CSV with bulk operations"""
    BATCH_SIZE = 500
    league = upload.league
    competition = upload.competition
    season = upload.season or "unknown"
    
    # Default league
    if not league:
        league = League.get_or_create_league("Premier League")
    
    matches_to_create = []
    matches_to_update = {}
    processed = 0
    successful = 0
    failed = 0
    
    for row in rows:
        try:
            # Parse fields
            comp_name = row.get("Competition") or row.get("competition")
            if comp_name:
                comp_obj, _ = Competition.objects.get_or_create(name=comp_name)
            else:
                comp_obj = competition
            
            season_val = row.get("Season") or row.get("season") or season
            
            league_name = row.get("League") or row.get("league")
            if league_name:
                league_obj = League.get_or_create_league(league_name)
            else:
                league_obj = league
            
            # Country logic
            country_name = row.get("Country") or row.get("country")
            country_obj = None
            
            if country_name:
                country_obj = Country.objects.filter(name__iexact=country_name).first()
            else:
                # Infer from league or competition
                if league_obj and league_obj.country_link:
                    country_obj = league_obj.country_link
                    country_name = country_obj.name
                elif league_obj and league_obj.country:
                    country_name = league_obj.country
                elif comp_obj and comp_obj.country:
                    country_obj = comp_obj.country
                    country_name = country_obj.name
            
            if not country_name:
                country_name = "England"
            
            # Teams
            home_team = Team.get_or_create_canonical(
                name=row.get("HomeTeam") or row.get("Home Team"),
                api_id=row.get("home_team_api_id"),
                country=country_name,
                country_link=country_obj
            )
            away_team = Team.get_or_create_canonical(
                name=row.get("AwayTeam") or row.get("Away Team"),
                api_id=row.get("away_team_api_id"),
                country=country_name,
                country_link=country_obj
            )
            
            # Date parsing
            date_str = row.get("Date") or row.get("date")
            date = parse_datetime(date_str)
            if not date:
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
                    try:
                        date = datetime.strptime(date_str, fmt)
                        break
                    except:
                        continue
            
            if not date:
                failed += 1
                continue
            
            # Scores and result
            home_score_str = row.get("FTHG") or row.get("home_score") or row.get("HomeScore")
            away_score_str = row.get("FTAG") or row.get("away_score") or row.get("AwayScore")
            home_score = int(home_score_str) if home_score_str else None
            away_score = int(away_score_str) if away_score_str else None
            
            result_str = row.get("FTR") or row.get("result") or row.get("Result")
            result = None
            if result_str:
                from .models import RESULT_MAP
                result = RESULT_MAP.get(result_str)
            
            # Create fixture_id
            fixture_id = Match.canonical_fixture_id(home_team, away_team, league_obj, season_val, date)
            
            # Check if exists
            existing = Match.objects.filter(fixture_id=fixture_id).first()
            if existing:
                # Update existing
                existing.home_team = home_team
                existing.away_team = away_team
                existing.league = league_obj
                existing.competition = comp_obj
                existing.season = season_val
                existing.date = date
                existing.home_score = home_score
                existing.away_score = away_score
                existing.result = result
                matches_to_update[existing.id] = existing
            else:
                # Prepare for bulk create
                matches_to_create.append(Match(
                    fixture_id=fixture_id,
                    home_team=home_team,
                    away_team=away_team,
                    league=league_obj,
                    competition=comp_obj,
                    season=season_val,
                    date=date,
                    home_score=home_score,
                    away_score=away_score,
                    result=result
                ))
            
            successful += 1
            processed += 1
            
            # Batch create
            if len(matches_to_create) >= BATCH_SIZE:
                Match.objects.bulk_create(matches_to_create, ignore_conflicts=True)
                matches_to_create = []
                
                # Update progress
                upload.processed_rows = processed
                upload.successful_rows = successful
                upload.failed_rows = failed
                upload.save()
        
        except Exception as e:
            failed += 1
            processed += 1
            print(f"Error processing row: {e}")
            continue
    
    # Final batch create
    if matches_to_create:
        Match.objects.bulk_create(matches_to_create, ignore_conflicts=True)
    
    # Bulk update existing
    if matches_to_update:
        Match.objects.bulk_update(
            matches_to_update.values(),
            ['home_team', 'away_team', 'league', 'competition', 'season', 'date', 
             'home_score', 'away_score', 'result'],
            batch_size=BATCH_SIZE
        )
    
    # Final update
    upload.processed_rows = processed
    upload.successful_rows = successful
    upload.failed_rows = failed
    upload.save()


def process_fixture_csv(upload, rows):
    """Process Fixture CSV with bulk operations"""
    BATCH_SIZE = 500
    league = upload.league
    season = upload.season or "unknown"
    
    if not league:
        league = League.get_or_create_league("Premier League")
    
    fixtures_to_create = []
    processed = 0
    successful = 0
    failed = 0
    
    for row in rows:
        try:
            home_team = Team.get_or_create_canonical(
                name=row.get("home_team_name") or row.get("HomeTeam"),
                api_id=row.get("home_team_api_id"),
            )
            away_team = Team.get_or_create_canonical(
                name=row.get("away_team_name") or row.get("AwayTeam"),
                api_id=row.get("away_team_api_id"),
            )
            
            date_str = row.get("date") or row.get("Date")
            date = parse_datetime(date_str)
            if not date:
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
                    try:
                        date = datetime.strptime(date_str, fmt)
                        break
                    except:
                        continue
            
            if not date:
                failed += 1
                continue
            
            fixture_id_val = row.get("id") or Fixture.canonical_fixture_id(
                home_team, away_team, league, season, date
            ).replace("-", "")[:10]
            
            # Check if exists
            if not Fixture.objects.filter(id=int(fixture_id_val)).exists():
                fixtures_to_create.append(Fixture(
                    id=int(fixture_id_val),
                    date=date,
                    status=row.get("status", "scheduled"),
                    league=league,
                    season=season,
                    home_team=home_team,
                    away_team=away_team,
                ))
            
            successful += 1
            processed += 1
            
            if len(fixtures_to_create) >= BATCH_SIZE:
                Fixture.objects.bulk_create(fixtures_to_create, ignore_conflicts=True)
                fixtures_to_create = []
                
                upload.processed_rows = processed
                upload.successful_rows = successful
                upload.failed_rows = failed
                upload.save()
        
        except Exception as e:
            failed += 1
            processed += 1
            continue
    
    if fixtures_to_create:
        Fixture.objects.bulk_create(fixtures_to_create, ignore_conflicts=True)
    
    upload.processed_rows = processed
    upload.successful_rows = successful
    upload.failed_rows = failed
    upload.save()


def process_team_csv(upload, rows):
    """Process Team CSV with bulk operations"""
    processed = 0
    successful = 0
    failed = 0
    
    for row in rows:
        try:
            Team.get_or_create_canonical(row["name"], api_id=row.get("api_id"))
            successful += 1
        except Exception as e:
            failed += 1
        processed += 1
        
        if processed % 100 == 0:
            upload.processed_rows = processed
            upload.successful_rows = successful
            upload.failed_rows = failed
            upload.save()
    
    upload.processed_rows = processed
    upload.successful_rows = successful
    upload.failed_rows = failed
    upload.save()


def process_player_csv(upload, rows):
    """Process Player CSV"""
    # Delegate to existing player import logic
    from utils.player_import import import_players_from_csv
    
    # Save file temporarily
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='utf-8') as tmp:
        fieldnames = rows[0].keys() if rows else []
        writer = csv.DictWriter(tmp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        tmp_path = tmp.name
    
    try:
        imported, updated = import_players_from_csv(tmp_path, upload.season or "2023-2024")
        upload.processed_rows = len(rows)
        upload.successful_rows = imported + updated
        upload.failed_rows = len(rows) - (imported + updated)
        upload.save()
    finally:
        os.unlink(tmp_path)


def process_gameweek_csv(upload, rows):
    """Process Gameweek CSV with bulk operations"""
    BATCH_SIZE = 100
    gameweeks_to_create = []
    processed = 0
    successful = 0
    failed = 0
    
    for row in rows:
        try:
            number = int(row.get("number") or row.get("Number"))
            
            start_date_str = row.get("start_date") or row.get("Start Date")
            start_date = parse_datetime(start_date_str)
            if not start_date:
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
                    try:
                        start_date = datetime.strptime(start_date_str, fmt)
                        break
                    except:
                        continue
            
            end_date_str = row.get("end_date") or row.get("End Date")
            end_date = parse_datetime(end_date_str)
            if not end_date:
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y"):
                    try:
                        end_date = datetime.strptime(end_date_str, fmt)
                        break
                    except:
                        continue
            
            if not Gameweek.objects.filter(number=number).exists():
                gameweeks_to_create.append(Gameweek(
                    number=number,
                    start_date=start_date,
                    end_date=end_date
                ))
            
            successful += 1
            processed += 1
            
            if len(gameweeks_to_create) >= BATCH_SIZE:
                Gameweek.objects.bulk_create(gameweeks_to_create, ignore_conflicts=True)
                gameweeks_to_create = []
                
                upload.processed_rows = processed
                upload.successful_rows = successful
                upload.failed_rows = failed
                upload.save()
        
        except Exception as e:
            failed += 1
            processed += 1
            continue
    
    if gameweeks_to_create:
        Gameweek.objects.bulk_create(gameweeks_to_create, ignore_conflicts=True)
    
    upload.processed_rows = processed
    upload.successful_rows = successful
    upload.failed_rows = failed
    upload.save()
