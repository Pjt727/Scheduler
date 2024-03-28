from django.core.management.base import BaseCommand, CommandError, CommandParser
from banner.management.create_classes import create_terms
from django.db import transaction
from django.conf import settings
import os

class Command(BaseCommand):
    help = "Adds non-existing class information to the database"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("years", nargs="+", type=str, help="The years used for the Year (XXXX) or 'all'")

    
    @transaction.atomic
    def handle(self, *_, **options) -> None:
        BANNER_DUMP_PATH = os.path.join(settings.BASE_DIR, 'banner', 'data', 'classes')
        
        sections: list[str] = []
        years = set()

        for file in os.listdir(BANNER_DUMP_PATH):
            if not os.path.isfile(os.path.join(BANNER_DUMP_PATH, file)): continue
            if file.startswith('sections'):
                sections.append(file)
                years.add(file[-9:-5])
        
        
        if any(map(lambda term: term.upper() == 'ALL', options["years"])):
            section_paths = map(lambda f: os.path.join(BANNER_DUMP_PATH, f), sections)
            create_terms(section_paths=section_paths)
        else:
            invalid_years = []
            for year in options["years"]:
                if year not in years: invalid_years.append(year)
            if len(invalid_years) != 0:
                raise CommandError(f"{', '.join(invalid_years)} year(s) are invalid or not stored. These are the stored years: {','.join(years)}")
            selected_sections = []
            for section in sections:
                if any(year in section for year in options["years"]):
                    selected_sections.append(section) 
            section_paths = map(lambda f: os.path.join(BANNER_DUMP_PATH, f), selected_sections)
            create_terms(section_paths=section_paths) 
        
        self.stdout.write(self.style.SUCCESS('Successfully added class information to the database'))
