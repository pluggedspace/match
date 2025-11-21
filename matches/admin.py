import os
import tempfile
from django import forms
from django.shortcuts import render, redirect
from django.urls import path
from django.contrib import admin, messages
from django.core.management import call_command
from django.utils.safestring import mark_safe

from .models import Team, Player, Match, Prediction, Fixture, UserPrediction, Bet, Gameweek, TelegramProfile, League
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
    season = forms.CharField(required=False, label="Season", initial="unknown")

# -------------------------------
# League Admin
# -------------------------------
@admin.register(League)
class LeagueAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'country', 'logo_preview']
    search_fields = ['name', 'code', 'country']
    list_filter = ['country']
    fields = ['name', 'code', 'country', 'logo_url']

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
        form = CsvImportForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                for chunk in csv_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            try:
                Team.import_from_csv(tmp_path)
                messages.success(request, "Teams imported successfully!")
            except Exception as e:
                messages.error(request, f"Import failed: {e}")
            finally:
                os.unlink(tmp_path)
            return redirect("..")
        context = dict(
            self.admin_site.each_context(request),
            form=form,
            title="Import Teams from CSV",
        )
        return render(request, "admin/import_csv_form.html", context)

# -------------------------------
# Team Admin
# -------------------------------
@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "country", "api_id")
    search_fields = ("name", "country")
    ordering = ("name", "country")
    change_list_template = "admin/team_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("sync_teams_form/", self.admin_site.admin_view(self.sync_teams_form), name="sync_teams_form"),
            path('import-csv/', self.admin_site.admin_view(self.import_csv_view), name='team_import_csv'),
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
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
                for chunk in csv_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            try:
                Team.import_from_csv(tmp_path, league=league_instance)
                messages.success(request, "Teams imported successfully!")
            except Exception as e:
                messages.error(request, f"Import failed: {e}")
            finally:
                os.unlink(tmp_path)
            return redirect("..")
        context = dict(
            self.admin_site.each_context(request),
            form=form,
            title="Import Teams from CSV",
        )
        return render(request, "admin/import_csv_form.html", context)

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
    list_display = ("id", "fixture_id", "home_team", "away_team", "date", "result")
    list_filter = ("result", "date")
    search_fields = ("home_team__name", "away_team__name")
    actions = ["sync_past_matches_action"]
    change_list_template = "admin/match_changelist.html"
    ordering = ("-date",)

    def sync_past_matches_action(self, request, queryset):
        call_command("sync_past_matches")
        self.message_user(request, "✅ Past matches synced successfully.")
    sync_past_matches_action.short_description = "Sync Past Matches from API"

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
            season = form.cleaned_data.get("season") or "unknown"
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                for chunk in csv_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            try:
                Match.import_from_csv(tmp_path, league=league_instance, season=season)
                messages.success(request, "Matches imported successfully!")
            except Exception as e:
                messages.error(request, f"Import failed: {e}")
            finally:
                os.unlink(tmp_path)
            return redirect("..")
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
    list_display = ("id", "date", "status", "league", "season", "home_team", "away_team")
    list_filter = ("status", "date", "league", "season")
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
            
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                for chunk in csv_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            try:
                Fixture.import_from_csv(tmp_path, league=league_instance, season=season)
                messages.success(request, "Fixtures imported successfully!")
            except Exception as e:
                messages.error(request, f"Import failed: {e}")
            finally:
                os.unlink(tmp_path)
            return redirect("..")
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
# TelegramProfile Admin
# -------------------------------
@admin.register(TelegramProfile)
class TelegramProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "telegram_id", "username", "first_name", "last_name")
    search_fields = ("user__username", "telegram_id", "username", "first_name", "last_name")
    list_filter = ("user__is_active",)
    ordering = ("user__username",)