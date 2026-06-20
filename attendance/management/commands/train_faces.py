from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from ...face_engine import train_recognizer


class Command(BaseCommand):
    help = "Train the LBPH face recognizer model from stored face samples."

    def handle(self, *args, **options) -> None:
        self.stdout.write(self.style.MIGRATE_HEADING("Training face recognizer..."))
        try:
            train_recognizer()
        except Exception as exc:  # noqa: BLE001
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS("Face recognizer trained successfully."))

