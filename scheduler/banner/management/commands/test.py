from django.core.management.base import BaseCommand
from request.models import *
from claim.models import *

class Command(BaseCommand):

    def handle(self, *args, **options) -> None:
        term = Term.objects.get(pk=10)
        building = Building.objects.get(pk=6)
        start = time(hour=18, minute=30)
        end =  time(hour=20, minute=45)
        day = "MO"


        rooms = building.get_available_rooms(
            start,
            end,
            day,
            term,
            True
        )
        filters = Q(
            meetings__section__term = term,
            meetings__time_block__day=day,
            meetings__time_block__start_end_time__start__lte=end,
            meetings__time_block__start_end_time__end__gte=start,
        )
        r_0 = building.rooms.all()
        r_1 = building.rooms.filter(filters)
        r_2 = building.rooms.exclude(filters)
        r_3 = building.rooms.exclude(pk__in=r_1)
        r_4 = building.rooms.filter(~filters)
        for r in r_1.all():
            print(r.meetings.filter(
                section__term = term,
                time_block__day=day,
                time_block__start_end_time__start__lte=end,
                time_block__start_end_time__end__gte=start,
            ).first())
        print(list(map(str, r_0)))
        print(list(map(str, r_1.all())))
        print(list(map(str, r_2.all())))
        print(list(map(str, r_3.all())))
        print(list(map(str, r_4.all())))
        print(list(map(str, rooms.all())))



