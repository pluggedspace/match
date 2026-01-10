import os
import tempfile
from django import forms
from django.shortcuts import render, redirect
from django.urls import path
from django.contrib import admin, messages
from django.core.management import call_command
from django.utils.safestring import mark_safe

from .models import Team, Player, Match, Prediction, Fixture, UserPrediction, Bet, Gameweek, TelegramProfile, League, Country, Competition, ModelConfig, CSVUpload
from matches.logic.train_and_predict import train_and_predict
from matches.management.commands.sync_teams import Command as SyncTeamsCommand

# -------------------------------
# CSV Import Form
# -------------------------------
class CsvImportForm(forms.Form):
    csv_file = forms.FileField(label="Select CSV file")
    league = forms.ModelChoiceField(
        queryset=League.objects.all(),
        required=False, 
        label="League",
        empty_label="Select League"
    )
    competition = forms.ModelChoiceField(
        queryset=Competition.objects.all(),
        required=False,
        label="Competition",
        empty_label="Select Competition"
    )
    season = forms.CharField(required=False, label="Season", initial="unknown")

class GameweekImportForm(forms.Form):
    csv_file = forms.FileField(label="Select CSV file")

# -------------------------------
# Country Admin
# -------------------------------
@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'flag_preview']
    search_fields = ['name', 'code']

    def flag_preview(self, obj):
        if obj.flag_url:
            return mark_safe(f'<img src="{obj.flag_url}" width="30" />')
        return "-"
    flag_preview.short_description = 'Flag'

# -------------------------------
# Competition Admin
# -------------------------------
@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'type', 'country']
    list_filter = ['type', 'country']
    search_fields = ['name', 'code']

# -------------------------------
# ModelConfig Admin
# -------------------------------
@admin.register(ModelConfig)
class ModelConfigAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'model_type', 'active', 'updated_at']
    list_filter = ['active', 'model_type', 'league', 'competition', 'country']
    search_fields = ['league__name', 'competition__name', 'country__name']
    fieldsets = (
        ('Context (Select one)', {
            'fields': ('league', 'competition', 'country')
        }),
        ('Hyperparameters', {
            'fields': ('model_type', 'n_estimators', 'max_depth', 'min_samples_split', 'active')
        }),
        ('Feature Weights', {
            'fields': (
                'weight_home_form', 'weight_away_form',
                'weight_home_strength', 'weight_away_strength',
                'weight_home_injuries', 'weight_away_injuries',
                'weight_home_goal_avg', 'weight_away_goal_avg',
                'weight_form_diff', 'weight_strength_diff',
                'weight_home_win_rate', 'weight_home_draw_rate',
                'weight_away_win_rate', 'weight_away_draw_rate',
                'weight_home_advantage'
            ),
            'classes': ('collapse',),
        }),
    )

# -------------------------------
# League Admin
# -------------------------------
@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'code', 'country', 'country_link', 'logo_preview']
    search_fields = ['name', 'code', 'country']
    list_filter = ['country', 'country_link']
    fields = ['name', 'code', 'country', 'country_link', 'logo_url']

    def logo_preview(self, obj):
        if obj.logo_url:
            return mark_safe(f'<a href="{obj.logo_url}" target="_blank">'
                             f'<img src="{obj.logo_url}" width="50" height="50" style="object-fit: contain;" />'
                             f'</a>')
        return "No logo"
    logo_preview.short_description = 'Logo Preview'

    actions = ['update_country']

    def update_country(self, request, queryset):
        self.message_user(request, f"Selected {queryset.count()} leagues for country update")
    update_country.short_description = "Update country for selected leagues"

# -------------------------------
# Gameweek Admin
# -------------------------------
@admin.register(Gameweek)
class GameweekAdmin(admin.ModelAdmin):
    list_display = ('number', 'start_date', 'end_date')
    list_filter = ('start_date', 'end_date')
    ordering = ('number',)
    change_list_template = "admin/gameweek_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.admin_site.admin_view(self.import_csv_view), name='gameweek_import_csv'),
        ]
        return custom_urls + urls

    def import_csv_view(self, request):
        form = GameweekImportForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            
            # Create CSVUpload record
            upload = CSVUpload.objects.create(
                file=csv_file,
                model_type='gameweek',
                uploaded_by=request.user,
                status='pending'
            )
            
            # Trigger background processing
            from matches.tasks import process_csv_upload
            task = process_csv_upload.delay(upload.id)
            upload.celery_task_id = task.id
            upload.save()
            
            messages.success(
                request,
                f"✅ CSV uploaded successfully! Processing in background. "
                f"<a href='/match/admin/matches/csvupload/{upload.id}/change/'>Track progress here</a>",
                extra_tags='safe'
            )
            return redirect("admin:matches_csvupload_changelist")
            
        context = dict(
            self.admin_site.each_context(request),
            form=form,
            title="Import Gameweeks from CSV",
        )
        return render(request, "admin/import_csv_form.html", context)

# -------------------------------
# Team Admin
# -------------------------------
@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "country", "country_link", "api_id")
    search_fields = ("name", "country")
    list_filter = ("country", "country_link")
    ordering = ("name", "country")
    actions = ["merge_teams_action"]
    change_list_template = "admin/team_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("sync_teams_form/", self.admin_site.admin_view(self.sync_teams_form), name="sync_teams_form"),
            path('import-csv/', self.admin_site.admin_view(self.import_csv_view), name='team_import_csv'),
            path('merge-teams/', self.admin_site.admin_view(self.merge_teams_view), name='team_merge_teams'),
        ]
        return custom_urls + urls

    def sync_teams_form(self, request):
        temp_cmd = SyncTeamsCommand()
        from argparse import ArgumentParser
        parser = ArgumentParser()
        temp_cmd.add_arguments(parser)
        country_options = sorted(temp_cmd.country_map.keys())

        if request.method == "POST":
            league_slug = request.POST.get("league")
            season = request.POST.get("season")
            if not league_slug or not season:
                messages.error(request, "Please select both country and season.")
            else:
                call_command("sync_teams", f"--{league_slug}", "--season", season)
                messages.success(
                    request,
                    f"✅ Teams synced successfully for {league_slug.replace('-', ' ').title()} ({season})"
                )
                return redirect("..")

        return render(request, "admin/sync_teams_form.html", {
            "title": "Sync Teams from API",
            "country_options": country_options,
        })

    def import_csv_view(self, request):
        form = CsvImportForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            league_instance = form.cleaned_data.get('league')
            
            # Create CSVUpload record
            upload = CSVUpload.objects.create(
                file=csv_file,
                model_type='team',
                league=league_instance,
                uploaded_by=request.user,
                status='pending'
            )
            
            # Trigger background processing
            from matches.tasks import process_csv_upload
            task = process_csv_upload.delay(upload.id)
            upload.celery_task_id = task.id
            upload.save()
            
            messages.success(
                request,
                f"✅ CSV uploaded successfully! Processing in background. "
                f"<a href='/match/admin/matches/csvupload/{upload.id}/change/'>Track progress here</a>",
                extra_tags='safe'
            )
            return redirect("admin:matches_csvupload_changelist")
            
        context = dict(
            self.admin_site.each_context(request),
            form=form,
            title="Import Teams from CSV",
        )
        return render(request, "admin/import_csv_form.html", context)

    def merge_teams_action(self, request, queryset):
        """Admin action to initiate team merge"""
        if queryset.count() < 2:
            self.message_user(request, "Please select at least 2 teams to merge.", level=messages.WARNING)
            return
        
        # Store selected team IDs in session
        request.session['teams_to_merge'] = list(queryset.values_list('id', flat=True))
        return redirect('admin:team_merge_teams')
    merge_teams_action.short_description = "Merge selected teams"

    def merge_teams_view(self, request):
        """View to handle team merging"""
        team_ids = request.session.get('teams_to_merge', [])
        
        if not team_ids:
            messages.error(request, "No teams selected for merging.")
            return redirect('admin:matches_team_changelist')
        
        teams = Team.objects.filter(id__in=team_ids)
        
        if request.method == "POST":
            keep_team_id = request.POST.get('keep_team')
            if not keep_team_id:
                messages.error(request, "Please select a team to keep.")
            else:
                keep_team = Team.objects.get(id=keep_team_id)
                merge_teams = teams.exclude(id=keep_team_id)
                
                # Update all related records
                from django.db.models import Q
                
                # Count affected records
                home_matches = Match.objects.filter(home_team__in=merge_teams).count()
                away_matches = Match.objects.filter(away_team__in=merge_teams).count()
                home_fixtures = Fixture.objects.filter(home_team__in=merge_teams).count()
                away_fixtures = Fixture.objects.filter(away_team__in=merge_teams).count()
                players = Player.objects.filter(team__in=merge_teams).count()
                
                # Perform merge
                Match.objects.filter(home_team__in=merge_teams).update(home_team=keep_team)
                Match.objects.filter(away_team__in=merge_teams).update(away_team=keep_team)
                Fixture.objects.filter(home_team__in=merge_teams).update(home_team=keep_team)
                Fixture.objects.filter(away_team__in=merge_teams).update(away_team=keep_team)
                Player.objects.filter(team__in=merge_teams).update(team=keep_team)
                
                # Delete merged teams
                merged_names = ', '.join(merge_teams.values_list('name', flat=True))
                merge_teams.delete()
                
                # Clear session
                del request.session['teams_to_merge']
                
                messages.success(
                    request,
                    f"✅ Successfully merged {merged_names} into {keep_team.name}. "
                    f"Updated: {home_matches + away_matches} matches, "
                    f"{home_fixtures + away_fixtures} fixtures, {players} players."
                )
                return redirect('admin:matches_team_changelist')
        
        context = dict(
            self.admin_site.each_context(request),
            teams=teams,
            title="Merge Teams",
        )
        return render(request, "admin/merge_teams.html", context)

# -------------------------------
# Player Admin
# -------------------------------
@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "team", "position", "injured")
    list_filter = ("position", "injured", "team")
    search_fields = ("name",)
    actions = ["sync_players_action"]
    change_list_template = "admin/player_changelist.html"

    def sync_players_action(self, request, queryset):
        call_command("sync_players")
        self.message_user(request, "✅ Players synced for all teams.")
    sync_players_action.short_description = "Sync Players for All Teams"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.admin_site.admin_view(self.import_csv_view), name='matches_player_import_csv'),
            path('import-api/', self.admin_site.admin_view(self.import_api_view), name='matches_player_import_api'),
        ]
        return custom_urls + urls

    def import_csv_view(self, request):
        import os
        form = CsvImportForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            season = form.cleaned_data.get("season") or "2023-2024"
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
                for chunk in csv_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            try:
                from utils.player_import import import_players_from_csv
                imported, updated = import_players_from_csv(tmp_path, season)
                messages.success(
                    request,
                    f"✅ Players imported successfully! {imported} new, {updated} updated"
                )
            except Exception as e:
                messages.error(request, f"❌ Import failed: {str(e)}")
            finally:
                os.unlink(tmp_path)
            return redirect("..")

        context = dict(
            self.admin_site.each_context(request),
            form=form,
            title="Import Players from CSV",
        )
        return render(request, "admin/import_csv_form.html", context)

    def import_api_view(self, request):
        if request.method == "POST":
            league_name = request.POST.get("league_name")
            season = request.POST.get("season")
            team_id = request.POST.get("team_id")
            try:
                if team_id:
                    from utils.api_import import import_players_from_api
                    team = Team.objects.get(id=team_id)
                    result = import_players_from_api(team.api_id, season)
                    if result:
                        messages.success(request, f"✅ Players imported for {team.name}")
                    else:
                        messages.warning(request, f"⚠️ No players found for {team.name}")
                else:
                    call_command("sync_players", "--league", league_name, "--season", season)
                    messages.success(request, f"✅ Players synced for {league_name}")
            except Exception as e:
                messages.error(request, f"❌ API import failed: {str(e)}")
            return redirect("..")

        leagues = Team.objects.values_list('league', flat=True).distinct()
        teams = Team.objects.all()
        context = dict(
            self.admin_site.each_context(request),
            leagues=leagues,
            teams=teams,
            title="Import Players from API",
        )
        return render(request, "admin/import_api_form.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_import_buttons'] = True
        return super().changelist_view(request, extra_context=extra_context)

# -------------------------------
# Match Admin
# -------------------------------
@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("id", "fixture_id", "home_team", "away_team", "date", "result", "competition")
    list_filter = ("result", "date", "competition", "league")
    #list_editable = ("fixture_id", "home_team", "away_team", "date", "result", "competition")
    search_fields = ("home_team__name", "away_team__name")
    change_list_template = "admin/match_changelist.html"
    ordering = ("-date",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.admin_site.admin_view(self.import_csv_view), name='matches_match_import_csv'),
        ]
        return custom_urls + urls

    def import_csv_view(self, request):
        form = CsvImportForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            league_instance = form.cleaned_data.get("league")
            competition_instance = form.cleaned_data.get("competition")
            season = form.cleaned_data.get("season") or "unknown"
            
            # Create CSVUpload record (file will be saved to S3)
            upload = CSVUpload.objects.create(
                file=csv_file,
                model_type='match',
                league=league_instance,
                competition=competition_instance,
                season=season,
                uploaded_by=request.user,
                status='pending'
            )
            
            # Trigger background processing
            from matches.tasks import process_csv_upload
            task = process_csv_upload.delay(upload.id)
            upload.celery_task_id= task.id
            upload.save()
            
            messages.success(
                request, 
                f"✅ CSV uploaded successfully! Processing in background. "
                f"<a href='/match/admin/matches/csvupload/{upload.id}/change/'>Track progress here</a>",
                extra_tags='safe'
            )
            return redirect("admin:matches_csvupload_changelist")
            
        context = dict(
            self.admin_site.each_context(request),
            form=form,
            title="Import Matches from CSV",
        )
        return render(request, "admin/import_csv_form.html", context)

# -------------------------------
# Fixture Admin
# -------------------------------
@admin.register(Fixture)
class FixtureAdmin(admin.ModelAdmin):
    list_display = ("id", "date", "status", "league", "competition", "season", "home_team", "away_team")
    list_filter = ("status", "date", "league", "competition", "season")
    list_editable = ("date", "status", "league", "competition", "season", "home_team", "away_team")
    search_fields = ("home_team__name", "away_team__name")
    change_list_template = "admin/fixtures_changelist.html"
    ordering = ("-date",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("sync-fixtures/", self.admin_site.admin_view(self.sync_fixtures_view), name="matches_fixture_sync_fixtures"),
            path('import-csv/', self.admin_site.admin_view(self.import_csv_view), name='matches_fixture_import_csv'),
        ]
        return custom_urls + urls

    def sync_fixtures_view(self, request):
        if request.method == "POST":
            league_name = request.POST.get("league_name")
            country = request.POST.get("country")
            season = request.POST.get("season")
            next_n = request.POST.get("next")
            
            # Get or create the League instance
            league_instance, created = League.objects.get_or_create(
                name=league_name,
                defaults={
                    'country': country, 
                    'code': league_name.upper().replace(' ', '_')
                }
            )
            
            call_command(
                "sync_fixtures",
                league_name=league_name,  # Pass as string for command compatibility
                country=country,
                season=int(season),
                next=int(next_n)
            )
            messages.success(request, "✅ Fixtures synced successfully.")
            return redirect("..")
        return render(request, "admin/sync_fixtures_form.html")

    def import_csv_view(self, request):
        form = CsvImportForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            league_instance = form.cleaned_data.get("league")
            season = form.cleaned_data.get("season") or "unknown"
            
            # Create CSVUpload record
            upload = CSVUpload.objects.create(
                file=csv_file,
                model_type='fixture',
                league=league_instance,
                season=season,
                uploaded_by=request.user,
                status='pending'
            )
            
            # Trigger background processing
            from matches.tasks import process_csv_upload
            task = process_csv_upload.delay(upload.id)
            upload.celery_task_id = task.id
            upload.save()
            
            messages.success(
                request,
                f"✅ CSV uploaded successfully! Processing in background. "
                f"<a href='/match/admin/matches/csvupload/{upload.id}/change/'>Track progress here</a>",
                extra_tags='safe'
            )
            return redirect("admin:matches_csvupload_changelist")
            
        context = dict(
            self.admin_site.each_context(request),
            form=form,
            title="Import Fixtures from CSV",
        )
        return render(request, "admin/import_csv_form.html", context)

# -------------------------------
# Prediction Admin
# -------------------------------
@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = (
        "fixture", "fixture_date", "result_pred", "confidence", "goal_diff",
        "fair_odds_home", "fair_odds_draw", "fair_odds_away", "model_version"
    )
    list_filter = ("result_pred", "model_version", "fixture__date")
    search_fields = ("fixture__home_team__name", "fixture__away_team__name")
    ordering = ("-fixture__date",)
    actions = ["train_matches_action"]

    def fixture_date(self, obj):
        return obj.fixture.date if obj.fixture and obj.fixture.date else "-"
    fixture_date.admin_order_field = "fixture__date"
    fixture_date.short_description = "Date"

    def train_matches_action(self, request, queryset):
        try:
            call_command("train_matches")
            self.message_user(request, "✅ Match model trained successfully.")
        except Exception as e:
            self.message_user(request, f"❌ Training failed: {e}", level=messages.ERROR)
    train_matches_action.short_description = "Train Match Prediction Model"

# -------------------------------
# UserPrediction Admin
# -------------------------------
@admin.register(UserPrediction)
class UserPredictionAdmin(admin.ModelAdmin):
    list_display = ("user", "fixture", "predicted_result", "timestamp")
    list_filter = ("predicted_result", "timestamp")
    search_fields = (
        "user__username",
        "fixture__home_team__name",
        "fixture__away_team__name"
    )
    ordering = ("-timestamp",)

# -------------------------------
# Bet Admin
# -------------------------------
@admin.register(Bet)
class BetAdmin(admin.ModelAdmin):
    list_display = (
        "user", "match", "predicted_result", "amount", "odds",
        "is_settled", "win", "payout", "placed_at"
    )
    list_filter = ("is_settled", "win", "placed_at")
    search_fields = ("user__username", "match__home_team__name", "match__away_team__name")

# -------------------------------
# CSV Upload Admin
# -------------------------------
@admin.register(CSVUpload)
class CSVUploadAdmin(admin.ModelAdmin):
    list_display = (
        "id", "model_type", "status", "progress_display", 
        "uploaded_by", "created_at", "completed_at"
    )
    list_filter = ("status", "model_type", "created_at")
    search_fields = ("uploaded_by__username", "error_message")
    readonly_fields = (
        "celery_task_id", "total_rows", "processed_rows", 
        "successful_rows", "failed_rows", "created_at", "updated_at", "completed_at"
    )
    actions = ["retry_failed_uploads"]
    ordering = ("-created_at",)
    
    fieldsets = (
        ("File Info", {
            "fields": ("file", "model_type", "uploaded_by")
        }),
        ("Import Context", {
            "fields": ("league", "competition", "season")
        }),
        ("Processing Status", {
            "fields": ("status", "celery_task_id", "error_message")
        }),
        ("Progress", {
            "fields": (
                "total_rows", "processed_rows", 
                "successful_rows", "failed_rows"
            )
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at", "completed_at")
        }),
    )
    
    def progress_display(self, obj):
        """Display progress bar"""
        if obj.total_rows == 0:
            return "N/A"
        
        percentage = obj.progress_percentage
        color = "green" if obj.status == "completed" else "blue"
        
        if obj.status == "failed":
            color = "red"
        
        return mark_safe(
            f'<div style="width: 200px; background: #f0f0f0; border-radius: 4px; overflow: hidden;">'
            f'<div style="width: {percentage}%; background: {color}; color: white; '
            f'padding: 2px 5px; text-align: center; min-width: 30px;">'
            f'{obj.processed_rows}/{obj.total_rows} ({percentage:.1f}%)'
            f'</div></div>'
        )
    progress_display.short_description = "Progress"
    
    def retry_failed_uploads(self, request, queryset):
        """Retry failed uploads"""
        from matches.tasks import process_csv_upload
        
        count = 0
        for upload in queryset.filter(status="failed"):
            upload.status = "pending"
            upload.error_message = None
            upload.save()
            
            # Trigger Celery task
            task = process_csv_upload.delay(upload.id)
            upload.celery_task_id = task.id
            upload.save()
            count += 1
        
        self.message_user(request, f"✅ Retrying {count} failed uploads")
    retry_failed_uploads.short_description = "Retry failed uploads"

# -------------------------------
# TelegramProfile Admin
# -------------------------------
@admin.register(TelegramProfile)
class TelegramProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "telegram_id", "username", "first_name", "last_name")
    search_fields = ("user__username", "telegram_id", "username", "first_name", "last_name")
    list_filter = ("user__is_active",)
    ordering = ("user__username",)