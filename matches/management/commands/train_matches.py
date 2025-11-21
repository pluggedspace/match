from django.core.management.base import BaseCommand
from matches.logic.train_and_predict import train_and_predict

class Command(BaseCommand):
    help = "Train the match prediction model and generate predictions for upcoming matches."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting training and prediction..."))

        result = train_and_predict()

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