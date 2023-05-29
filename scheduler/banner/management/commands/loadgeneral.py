from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from banner.management.create_static import create_all

class Command(BaseCommand):
    help = "Adds relatively static, term independent data to the database"

    def add_arguments(self, parser: CommandParser) -> None:
        return super().add_arguments(parser)
    
    @transaction.atomic
    def handle(self, *args, **options) -> None:
        create_all()
        self.stdout.write(self.style.SUCCESS('Successfully added general information to database'))