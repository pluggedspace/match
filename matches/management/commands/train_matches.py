from django.core.management.base import BaseCommand
from matches.logic.train_and_predict import train_and_predict

class Command(BaseCommand):
    help = "Train the match prediction model and generate predictions for upcoming matches."

    def add_arguments(self, parser):
        parser.add_argument('--league', type=int, help='League ID to train for')
        parser.add_argument('--competition', type=int, help='Competition ID to train for')
        parser.add_argument('--country', type=int, help='Country ID to train for')

    def handle(self, *args, **options):
        league_id = options.get('league')
        competition_id = options.get('competition')
        country_id = options.get('country')

        self.stdout.write(self.style.NOTICE("Starting training and prediction..."))

        result = train_and_predict(
            league_id=league_id,
            competition_id=competition_id,
            country_id=country_id
        )

        if result.get("status") == "success":
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Training complete.\n"
                    f"Accuracy: {result['accuracy']}\n"
                    f"CV Score: {result.get('cv_score', 'N/A')}\n"
                    f"Matches predicted: {result['matches_predicted']}"
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"❌ Failed: {result.get('reason', 'Unknown error')}")
            )