from django.core.management.base import BaseCommand, CommandError, CommandParser
from banner.management.create_classes import create_terms
from django.db import transaction
from django.conf import settings
import os

class Command(BaseCommand):
    help = "Adds non-existing class information to the database"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("terms", nargs="+", type=str, help="The terms used for the data SeasonYear or 'all'")

        parser.add_argument("--force", action="store_true", help="Continues the loading process even if some sections fail to be added to the database")
    
    @transaction.atomic
    def handle(self, *args, **options) -> None:
        BANNER_DUMP_PATH = f"{settings.BASE_DIR}/banner/data/classes"
        valid_terms = [term for term in os.listdir(BANNER_DUMP_PATH) if os.path.isdir(os.path.join(BANNER_DUMP_PATH, term))]
        
        if any(map(lambda term: term.upper() == 'ALL', options["terms"])):
            course_errs, section_errs = create_terms(terms=valid_terms, force=options["force"])
        else:
            invalid_terms: filter = filter(lambda term: term not in valid_terms, options['terms'])
            if len(invalid_terms) != 0:
                raise CommandError(f"{', '.join(invalid_terms)} term(s) are invalid or not stored. These are the stored terms: {','.join(valid_terms)}")
            course_errs, section_errs = create_terms(terms=options["terms"], force=options["force"]) 
        
        self.stdout.write(self.style.SUCCESS('Successfully added class information to the database'))
        if course_errs or section_errs:
            tab = "----"
            unique_course_errs = set(course_errs)
            unique_section_errs = set(section_errs)
            self.stdout.write(self.style.ERROR(f'However {len(course_errs)} course(s) and {len(section_errs)} section(s) were silenced: '))
            self.stdout.write(self.style.ERROR(f'\nCourse Errors'))
            for unique_course_err in unique_course_errs:
                self.stdout.write(self.style.ERROR(f'{tab}{unique_course_err} X {course_errs.count(unique_course_err)}'))

            self.stdout.write(self.style.ERROR(f'\n\nSection Errors'))
            for unique_section_err in unique_section_errs:
                self.stdout.write(self.style.ERROR(f'{tab}{unique_section_err} X {section_errs.count(unique_section_err)}'))

