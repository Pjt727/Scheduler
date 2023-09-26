from django.http import QueryDict
from django.db import models, IntegrityError, transaction
from authentication.models import Professor
from claim.models import *
from authentication.models import Professor
from typing import TypedDict

class TimeSlot(TypedDict):
    start: time
    end: time
    day: str
    allocation_max: int
    allocation: int
    numbers: list[str]

class Problem:
    DANGER = 'danger'
    WARNING = 'warning'

    def __init__(self, type: str, text: str) -> None:
        self.type = type
        self.text = text

@dataclass
class EditMeeting:
    start_time: time
    end_time: time
    day: str
    building: Building
    room: Room | None
    meeting: Meeting
    section: Section
    counter: int | None
    professor: Professor = None
    is_deleted: bool = False

    def create_all(data: QueryDict) -> list['EditMeeting']:
        are_deleted = data.getlist('isDeleted')
        sections = data.getlist('section')
        start_times = data.getlist('startTime')
        end_times = data.getlist('endTime')
        days = data.getlist('day')
        buildings = data.getlist('building')
        rooms = data.getlist('room')
        professors = data.getlist('professor')
        counters = data.getlist('counter')

        originals = data.getlist('original')

        edit_meetings: list[EditMeeting] = []
        for i in range(len(are_deleted)):
            section = Section.objects.get(pk=sections[i])
            counter = int(counters[i])

            start_time = start_times[i]
            end_time = end_times[i]
            start_time = time.fromisoformat(start_time)
            end_time = time.fromisoformat(end_time)
            day = days[i]

            building = buildings[i]
            if building == "any":
                building = None
            else:
                building = Building.objects.get(pk=building)
            
            room = rooms[i]
            if room == "any":
                room = None
            else:
                room = Room.objects.get(pk=room)

            meeting = originals[i]
            if meeting == "None":
                meeting = None
            else:
                meeting = Meeting.objects.get(pk=meeting)

            professor = professors[i]
            if professor == "None":
                professor = None
            else:

                professor = Professor.objects.get(pk=professor)
        
            is_deleted = are_deleted[i] == "true"
            edit_meetings.append(EditMeeting(
                start_time=start_time,
                counter=counter,
                end_time=end_time,
                day=day,
                building=building,
                section=section,
                room=room,
                meeting=meeting,
                professor=professor,
                is_deleted=is_deleted
            ))
        return edit_meetings
    
    def room_problems(self, sections_to_exclude: list[Section] = None, check_allocation=True) -> list[Problem]:
        if sections_to_exclude is None:
            sections_to_exclude = [self.section]

        overlaps_time = Q(
            time_block__start_end_time__start__lte = self.end_time,
            time_block__start_end_time__end__gte = self.start_time,
            time_block__day = self.day,
        )

        meetings = Meeting.objects \
            .filter(section__term=self.section.term) \
            .exclude(section__in=sections_to_exclude) \
            .filter(overlaps_time)

        problems = []
        if self.room is None: return problems

        sections = list(map(lambda s: str(Section.objects.get(pk=s['section'])),
            meetings.filter(room=self.room).values('section').distinct()))
        if sections:
            sections_text = ", ".join(sections)
            text = f"Meeting {self.counter} overlaps {self.room} with {sections_text}."
            problems.append(Problem(Problem.DANGER, text))
        
        if not (self.room.is_general_purpose and check_allocation): return problems

        time_blocks = TimeBlock.get_official_time_blocks(self.start_time, self.end_time, day=self.day)
        department_allocations = DepartmentAllocation.objects.filter(
            department = self.section.course.subject.department,
            allocation_group__in = time_blocks.values('allocation_groups')
        )

        if any(map(lambda d_a: d_a.exceeds_allocation(self.section.term), department_allocations.all())):
            text = f"Meeting {self.counter} exceeds department constraints for that time slot."
            problems.append(Problem(Problem.WARNING, text))

        return problems

    def professor_problems(self, sections_to_exclude: list[Section] = None) -> list[Problem]:
        if sections_to_exclude is None:
            sections_to_exclude = [self.section]

        overlaps_time = Q(
            time_block__start_end_time__start__lte = self.end_time,
            time_block__start_end_time__end__gte = self.start_time,
            time_block__day = self.day,
        )

        meetings = Meeting.objects \
            .filter(section__term=self.section.term) \
            .exclude(section__in=sections_to_exclude) \
            .filter(overlaps_time)
        
        problems = []
        if self.professor is None: return problems

        sections = list(map(str, meetings.filter(professor=self.professor).values('section').distinct()))
        if sections:
            sections_text = ", ".join(sections)
            text = f"Meeting {self.counter} overlaps with {sections_text} that {self.professor} teaches."
            problems.append(Problem(Problem.DANGER, text))
        
        return problems

    def get_group_problems(edit_meetings: list['EditMeeting']) -> list[Problem]:
        problems: list[Problem] = []
        for i, edit_meeting1 in enumerate(edit_meetings[:-1]):
            for edit_meeting2 in edit_meetings[i+1:]:
                overlapping_time = (edit_meeting1.start_time_d() <= edit_meeting2.end_time_d()) \
                    and (edit_meeting1.end_time_d() >= edit_meeting2.start_time_d()) 
                same_day = (edit_meeting1.day == edit_meeting2.day)
                if not (overlapping_time and same_day): continue
                same_room = (edit_meeting1.room == edit_meeting2.room) \
                    and (edit_meeting1.room is not None)
                if same_room:
                    message = f"Meeting {edit_meeting1.counter} from {edit_meeting1.section} overlaps {edit_meeting1.room} with meeting {edit_meeting2.counter} from {edit_meeting2.section}."
                    problems.append(Problem(Problem.DANGER, message))
                same_professor = (edit_meeting1.professor == edit_meeting2.professor) \
                    and (edit_meeting1.professor is not None)
                if same_professor:
                    message = f"Meeting {edit_meeting1.counter} from {edit_meeting1.section} overlaps with meeting {edit_meeting2.counter} from {edit_meeting2.section} that {edit_meeting1.professor} teaches."
                    problems.append(Problem(Problem.DANGER, message))
        return problems

    def get_section_problems(edit_meetings: list['EditMeeting'], sections_to_exclude: list[Section]) -> list[Problem]:
        sections = set()
        for m in edit_meetings:
            sections.add(m.section)
        assert len(sections) == 1

        problems: list[Section]= []
        section = edit_meetings[0].section

        for edit_meeting in edit_meetings:
            problems.extend(edit_meeting.room_problems(sections_to_exclude, check_allocation=False))
            problems.extend(edit_meeting.professor_problems(sections_to_exclude))

        total_time = sum(map(lambda t: t.end_time_d() - t.start_time_d(), edit_meetings), start=timedelta())

        if total_time not in section.course.get_approximate_times():
            message = f'The total time for this section does not match {section.course.credits} credit hours.'
            problems.append(Problem(Problem.WARNING, message))
        in_meetings = Q()
        for edit_meeting in edit_meetings:
            in_meetings |= Q(
                day=edit_meeting.day,
                start_end_time__start__lte=edit_meeting.end_time,
                start_end_time__end__gte=edit_meeting.start_time,
            )
        official_time_blocks = TimeBlock.objects \
            .filter(number__isnull=False) \
            .filter(in_meetings) \
            .distinct()
        exceeds_allocation = False
        dep_allocations = DepartmentAllocation.objects \
            .filter(allocation_group__in=official_time_blocks.values('allocation_groups'))

        for dep_allocation in dep_allocations:
            # Maybe think about making this not add one for the section
            if dep_allocation.exceeds_allocation(edit_meeting.section.term):
                exceeds_allocation = True
                break
        if exceeds_allocation:
            message = f'The department allocation is exceeded for one or more of these meetings.'
            problems.append(Problem(Problem.WARNING, message))

        
        
        # TODO? implement a warning for giving a professor too many teaching hours

        return problems

    def is_changed(self) -> bool:
        if self.is_deleted:
            return True
        if self.meeting is None:
            return True
        og_time_block = self.meeting.time_block
        if og_time_block.day != self.day:
            return True
        if og_time_block.start_end_time.start != self.start_time:
            return True
        if og_time_block.start_end_time.end != self.end_time:
            return True
        if self.meeting.room != self.room:
            return True
        if self.meeting.professor != self.professor:
            return True

        return False

    def get_open_slots(self, edit_meetings: list['EditMeeting'], sections_to_exclude: list[Section], enforce_allocation: bool) -> tuple[QuerySet[Meeting], list[TimeSlot]]:
        edit_meetings = edit_meetings.copy()
        edit_meetings.remove(self)

        meetings = Meeting.objects.none()
        if self.professor:
            meetings |= self.professor.meetings.filter(section__term=self.section.term)
        if self.room:
            meetings |= Meeting.objects.filter(room=self.room, section__term=self.section.term)
        
        meetings = meetings.exclude(section__in=sections_to_exclude).distinct()

        total_time = self.end_time_d() - self.start_time_d()
        if (total_time == TimeBlock.ONE_BLOCK) or (total_time == TimeBlock.DOUBLE_BLOCK):
            return meetings, self.open_slots(
                room=self.room,
                professor=self.professor,
                building=None,
                section=self.section,
                duration= total_time,
                edit_meetings=edit_meetings,
                meetings = meetings,
                enforce_allocation=enforce_allocation)
        elif total_time == TimeBlock.DOUBLE_BLOCK_NIGHT:
            return meetings, []
        elif total_time == TimeBlock.TRIPLE_NIGHT:
            return meetings, []
    
    # There are still a lot problems with this and probably with forever have a lot of problems but at this points
    # it does not need to be perfect
    def open_slots(*args, room: Room | None, professor: Professor, building: Building | None, section: Section , duration: timedelta, edit_meetings: list['EditMeeting'], meetings: QuerySet[Meeting], enforce_allocation: bool) -> list[TimeSlot]:
        if building is None:
            building = Building.recommend(section.course, term=section.term)
        in_edit_meetings = Q()
        # duration is always greater than or equal to TimeBlock.ONE_BLOCK
        duration_after_time_block = duration - TimeBlock.ONE_BLOCK
        sections_to_exclude: set[Section] = set()
        for edit_meeting in edit_meetings:
            sections_to_exclude.add(edit_meeting.section)
            same_professor = (professor == edit_meeting.professor) \
                and (professor is not None)
            same_room = (room == edit_meeting.room) \
                and (room is not None)
            
            if not (same_professor or same_room): continue
            new_start_d = edit_meeting.start_time_d() - duration_after_time_block
            new_start_t = time(hour=new_start_d.seconds // 3600, minute=(new_start_d.seconds % 3600) // 60)
            in_edit_meetings |= Q(
                day=edit_meeting.day,
                start_end_time__start__lte=edit_meeting.end_time,
                start_end_time__end__gte=new_start_t
            )
        
        in_meetings = Q()
        for meeting in meetings.all():
            new_start_d = meeting.time_block.start_end_time.start_d() - duration_after_time_block
            new_start_t = time(hour=new_start_d.seconds // 3600, minute=(new_start_d.seconds % 3600) // 60)
            in_meetings |= Q(
                day= meeting.time_block.day,
                start_end_time__start__lte=meeting.time_block.start_end_time.end,
                start_end_time__end__gte=new_start_t
            )
        time_blocks = TimeBlock.objects \
            .filter(number__isnull=False) \
            .exclude(number__in=TimeBlock.LONG_NIGHT_NUMBERS) \
            .exclude(in_edit_meetings) \
            .exclude(in_meetings)
        open_slots = []
        for time_block in time_blocks.all():
            new_end_d = time_block.start_end_time.start_d() + duration
            new_end_t = time(hour=new_end_d.seconds // 3600, minute=(new_end_d.seconds % 3600) // 60)
            tbs = TimeBlock.objects.filter(
                number__isnull=False,
                day=time_block.day,
                start_end_time__end=new_end_t)
            if not tbs.exists(): continue
            department_allocation = DepartmentAllocation.objects.get(
                department=section.course.subject.department,
                allocation_group=time_block.allocation_groups.first()
            )

            allocation_max = department_allocation.number_of_classrooms
            # STILL COUNTS WITHOUT CHANGES WHEN EDITING
            allocation = department_allocation.count_rooms(section.term)
            slot: TimeSlot = {
                'start': time_block.start_end_time.start,
                'end': new_end_t,
                'day': time_block.day,
                'allocation_max': allocation_max,
                'allocation': allocation,
                'numbers': [time_block.number]
            }
            if room is None:
                # DOES NOT INCLUDE ONES FROM EDIT MEETINGS
                available_rooms = building.get_available_rooms(
                    start_time=slot['start'],
                    end_time=slot['end'],
                    day=slot['day'],
                    term=section.term,
                    include_general= (slot['allocation_max'] > slot['allocation']) or (not enforce_allocation),
                    sections_to_exclude=sections_to_exclude
                )
                if not available_rooms.exists(): continue
                open_slots.append(slot)
                continue

            if not enforce_allocation:
                open_slots.append(slot)
                continue
            if slot['allocation_max'] > slot['allocation']:
                open_slots.append(slot)
                continue
            if not room.is_general_purpose:
                open_slots.append(slot)
                continue

            
        return open_slots

    # Recommending meeting is painfully complex and pretty slow doing it this way.
    # To remove some of the complexity open_slots is used which probably is not the best way
    # There should be A LOT better of way to recommend bulk subjects without requesting 

    def recommend_meetings(edit_meetings: list['EditMeeting'], professor: Professor, section: Section) -> list['EditMeeting']:
        total_duration = timedelta()
        sections_to_exclude = set()
        number_room_complement: list[tuple[int, Room]] = []
        last_counter = 1
        for edit_meeting in edit_meetings:
            sections_to_exclude.add(edit_meeting.section)
            if edit_meeting.section != section: continue
            last_counter = max(last_counter, edit_meeting.counter)
            if edit_meeting.is_deleted: continue
            tms = TimeBlock.get_official_time_blocks(edit_meeting.start_time, edit_meeting.end_time, edit_meeting.day)
            for tm in tms.all():
                in_complements_flag = False
                for i, (num, _) in enumerate(number_room_complement):
                    if num != tm.number: continue
                    del number_room_complement[i]
                    in_complements_flag = True
                if in_complements_flag: continue
                number_room_complement.append((tm.number, edit_meeting.room))
            total_duration += edit_meeting.end_time_d() - edit_meeting.start_time_d()
        edit_meetings = list(filter(lambda m: not m.is_deleted, edit_meetings))
        no_recommendation = EditMeeting(
            start_time=time(0),
            end_time=time(hour=1, minute=15),
            day="MO",
            building=None,
            room=None,
            meeting=None,
            section=section,
            counter=last_counter + 1
        )

        valid_times = section.course.get_approximate_times()
        valid_added_times = list(map(lambda t: t-total_duration, valid_times))
        base_meetings = Meeting.objects.none()
        if professor:
            base_meetings |= professor.meetings \
                .filter(section__term=section.term) \
                .exclude(section__in=sections_to_exclude)
        
        # purposefully slow to ensure that the same logic as open_slots is used
        # I also hate this code
        if timedelta(0) in valid_added_times:
            return [no_recommendation]
        elif TimeBlock.ONE_BLOCK in valid_added_times:
            return EditMeeting.recommend_one_block(edit_meetings=edit_meetings, professor=professor,
                base_meetings=base_meetings, section=section, number_room_complements=number_room_complement,
                sections_to_exclude=sections_to_exclude, last_counter=last_counter)
        elif (TimeBlock.ONE_BLOCK * 2) in valid_added_times:
            return EditMeeting.recommend_two_block(edit_meetings=edit_meetings, professor=professor,
                base_meetings=base_meetings, section=section, number_room_complements=number_room_complement,
                sections_to_exclude=sections_to_exclude, last_counter=last_counter)
        elif any(map(lambda t: t==TimeBlock.ONE_BLOCK * 3, valid_added_times)):
            recommended_edit_meetings = EditMeeting.recommend_two_block(
                edit_meetings=edit_meetings, professor=professor, base_meetings=base_meetings,
                section=section, number_room_complements=number_room_complement,
                sections_to_exclude=sections_to_exclude, last_counter=last_counter)
            edit_meetings.extend(recommended_edit_meetings)
            recommended_edit_meetings.extend(EditMeeting.recommend_one_block(
                edit_meetings=edit_meetings, professor=professor,
                base_meetings=base_meetings, section=section, number_room_complements=number_room_complement,
                sections_to_exclude=sections_to_exclude, last_counter=last_counter + len(recommended_edit_meetings)
            ))
            return recommended_edit_meetings

        return [no_recommendation]

    def no_recommendation(section: Section, counter: int, building: Building = None):
        return EditMeeting(
            start_time=time(0), end_time=time(hour=1, minute=15), day="MO",
            building=building, room=None, meeting=None,
            section=section, counter=counter,
        )

    def recommend_one_block(*args, edit_meetings: list['EditMeeting'], professor: Professor, base_meetings: QuerySet[Meeting], section: Section,
        number_room_complements: list[tuple[int, Room]], sections_to_exclude: set[Section], last_counter: int) -> list['EditMeeting']:

        for num, room in number_room_complements:
            if room:
                meetings = base_meetings | Meeting.objects \
                    .filter(room=room, section__term=section.term) \
                    .exclude(section__in=sections_to_exclude)
            else:
                meetings = base_meetings
            open_slots: list[TimeSlot] = EditMeeting.open_slots( room=room, professor=professor,
                building=None, duration=TimeBlock.ONE_BLOCK, section=section,
                edit_meetings=edit_meetings, meetings=meetings, enforce_allocation=False)
            for open_slot in open_slots:
                if num not in open_slot['numbers']: continue
                building = None if room is None else room.building
                return [EditMeeting(
                    start_time=open_slot['start'], end_time=open_slot['end'], day=open_slot['day'],
                    building=building, room=room, meeting=None,
                    section=section, counter=last_counter + 1, professor=professor,
                )]
        building = Building.recommend(section.course, term=section.term)
        open_slots: list[TimeSlot] = EditMeeting.open_slots(
            room=None, professor=professor, building=building,
            duration=TimeBlock.ONE_BLOCK, edit_meetings=edit_meetings, section=section,
            meetings=base_meetings, enforce_allocation=False)
        open_slots.sort(key=lambda s: s['allocation'] / s['allocation_max'])
        best_open_slot = open_slots[0]
        return [EditMeeting(
            start_time=best_open_slot['start'], end_time=best_open_slot['end'], day=best_open_slot['day'],
            building=building, room=None, meeting=None,
            section=section, counter=last_counter + 1, professor=professor,
        )]
    
    def recommend_two_block(*args, edit_meetings: list['EditMeeting'], professor: Professor, base_meetings: QuerySet[Meeting], section: Section,
        number_room_complements: list[tuple[int, Room]], sections_to_exclude: set[Section], last_counter: int) -> list['EditMeeting']:
        recommended = []
        building = Building.recommend(section.course, term=section.term)
        # There should at most only be one complement 
        if number_room_complements:
            num, room = number_room_complements[0]
            if room:
                meetings = base_meetings | Meeting.objects \
                    .filter(room=room, section__term=section.term) \
                    .exclude(section__in=sections_to_exclude)
            else:
                meetings = base_meetings
                
            building = building if room is None else room.building
            open_slots: list[TimeSlot] = EditMeeting.open_slots(room=room, professor=professor,
                building=building, duration=TimeBlock.ONE_BLOCK, edit_meetings=edit_meetings,
                meetings=meetings, enforce_allocation=False, section=section)
            for open_slot in open_slots:
                if num not in open_slot['numbers']: continue
                building = building if room is None else room.building
                last_counter += 1
                recommended.append(EditMeeting(
                    start_time=open_slot['start'], end_time=open_slot['end'], day=open_slot['day'],
                    building=building, room=room, meeting=None,
                    section=section, counter=last_counter, professor=professor,
                ))
                recommended.extend(EditMeeting.recommend_one_block(
                    edit_meetings=edit_meetings, professor=professor, base_meetings=base_meetings,
                    section=section, number_room_complements=[], sections_to_exclude=sections_to_exclude, 
                    last_counter=last_counter
                ))
                return recommended
        open_slots = EditMeeting.open_slots(room=None, professor=professor,
            building=building, duration=TimeBlock.ONE_BLOCK, edit_meetings=edit_meetings,
            meetings=base_meetings, enforce_allocation=False, section=section)
        
        # yeah... i know
        seen_numbers: list[str] = []
        for i, slot1 in enumerate(open_slots):
            if any(number in seen_numbers for number in slot1['numbers']):
                continue
            available_rooms_slot1 = building.get_available_rooms(
                start_time=slot1['start'],
                end_time=slot1['end'],
                day=slot1['day'],
                term=section.term,
                include_general= False,
                sections_to_exclude=sections_to_exclude
            )
            slot2 = None
            if i + 1 == len(open_slots): continue
            for s in open_slots[i+1:]:
                if s['numbers'] == slot1['numbers']:
                    slot2=s
            if slot2 is None: continue
            available_rooms_slot2 = building.get_available_rooms(
                start_time=slot2['start'],
                end_time=slot2['end'],
                day=slot2['day'],
                term=section.term,
                include_general= False,
                sections_to_exclude=sections_to_exclude
            )
            intersecting_rooms = available_rooms_slot1 & available_rooms_slot2
            if not intersecting_rooms.exists(): continue

            room = intersecting_rooms.first()
            m1 = EditMeeting(start_time=slot1['start'], end_time=slot2['end'],
                day=slot1['day'], building=room.building, room=room,
                meeting=None, section=section, counter=last_counter+1,
                professor=professor)
            m2 = EditMeeting(start_time=slot2['start'], end_time=slot2['end'],
                day=slot2['day'], building=room.building, room=room,
                meeting=None, section=section, counter=last_counter+2,
                professor=professor)
            return [m1, m2]

        return [EditMeeting.no_recommendation(section=section, counter=last_counter+1, building=building)]
    
    def save_as_request(self, edit_section: 'EditSectionRequest') -> 'EditMeetingRequest':
        request = EditMeetingRequest(
            start_time=self.start_time,
            end_time=self.end_time,
            day=self.day,
            building=self.building,
            room=self.room,
            professor=self.professor,
            original=self.meeting,
            edit_section=edit_section,
            is_deleted=self.is_deleted
        )
        request.save()
        return request
    def get_meeting_pk(self) -> None | str:
        return None if self.meeting is None else self.meeting.pk

    def start_time_d(self):
        return timedelta(hours=self.start_time.hour, minutes=self.start_time.minute)

    def end_time_d(self):
        return timedelta(hours=self.end_time.hour, minutes=self.end_time.minute)


class EditRequestBundle(models.Model):
    verbose_name = "Edit Meeting Bundle"

    requester = models.ForeignKey(Professor, related_name="edit_request_bundles", on_delete=models.CASCADE)
    edit_sections: QuerySet['EditSectionRequest']
    message_bundles: QuerySet['EditMeetingMessageBundle']

    def realize(self):
        for edit_section in self.edit_sections.all():
            edit_section.realize()



class EditSectionRequest(models.Model):
    verbose_name = "Edit Section"

    section = models.ForeignKey(Section, related_name="edit_sections", on_delete=models.CASCADE)
    bundle = models.ForeignKey(EditRequestBundle, related_name="edit_sections", on_delete=models.CASCADE)
    edit_meetings: QuerySet['EditMeetingRequest']
    
    def save(self, *args, **kwargs):
        if EditSectionRequest.objects.filter(section=self.section, bundle__requester=self.bundle.requester).exists():
            raise IntegrityError("This professor has already requested a change with this section.")
        super().save(*args, **kwargs)
    
    def realize(self):
        for edit_meeting in self.edit_meetings.all():
            edit_meeting.realize()


class EditMeetingRequest(models.Model):
    verbose_name = "Edit Meeting"

    start_time = models.TimeField()
    end_time = models.TimeField()
    day = models.CharField(max_length=2, choices=Day.DAY_CHOICES)
    is_deleted = models.BooleanField()

    building = models.ForeignKey(Building, related_name="edit_requests", blank=True, null=True, on_delete=models.SET_NULL)
    # If the room is None then the new meeting can be any room in the building 
    room = models.ForeignKey(Room, related_name="edit_requests", blank=True, null=True, on_delete=models.SET_NULL)
    professor = models.ForeignKey(Professor, related_name="edit_requests_involving", blank=True, null=True, default=None, on_delete=models.CASCADE)
    # If there is no original then it is a created meeting
    original = models.ForeignKey(Meeting, related_name="edit_meetings", blank=True, null=True, default=None, on_delete=models.CASCADE)

    edit_section = models.ForeignKey(EditSectionRequest, related_name="edit_meetings", on_delete=models.CASCADE)

    def is_changed(self) -> bool:
        if self.original is None: return True
        old_new = [
            (self.original.time_block.start_end_time.start, self.start_time,),
            (self.original.time_block.start_end_time.end, self.end_time,),
            (self.original.time_block.day, self.day,),
            (self.original.room, self.room,),
            (self.original.professor, self.professor,),
        ]

        return any(map(lambda old_new: old_new[0] != old_new[1], old_new))

    def freeze(self, bundle: 'EditMeetingMessageBundle') -> 'EditMeetingMessage':
        '''Freezes the current state of the request into a message'''
        if self.original is not None:
            old_start_time = self.original.time_block.start_end_time.start
            old_end_time = self.original.time_block.start_end_time.end
            old_day = self.original.time_block.day
            old_room = self.original.room
            old_professor = self.original.professor
            if old_room is not None:
                old_building = old_room.building
            else:
                old_building = None
        else:
            old_professor = None
            old_start_time = None
            old_end_time = None
            old_day = None
            old_room = None
            old_building = None



        message = EditMeetingMessage(
            is_changed=self.is_changed(),

            old_start_time=old_start_time,
            old_end_time=old_end_time,
            old_day=old_day,
            old_building=old_building,
            old_room=old_room,
            old_professor=old_professor,

            new_start_time=self.start_time,
            new_end_time=self.end_time,
            new_day=self.day,
            new_building=self.building,
            new_room=self.room,
            new_professor=self.professor,

            section=self.edit_section.section,
            bundle=bundle,
        )
        message.save()
        return message

    def reformat(self, counter: int) -> EditMeeting:
        return EditMeeting(
                start_time=self.start_time,
                end_time=self.end_time,
                day=self.day,
                building=self.building,
                room=self.room,
                meeting=self.original,
                section=self.edit_section.section,
                counter=counter,
                professor=self.professor,
                is_deleted=self.is_deleted
            )

    def realize(self) -> None:
        start_end_time, _ = StartEndTime.objects.get_or_create(
            start=self.start_time,
            end=self.end_time,)
        time_block, _ = TimeBlock.objects.get_or_create(
            start_end_time=start_end_time,
            day=self.day)

        if self.original:
            self.original.room = self.room
            self.original.professor = self.professor
            self.original.time_block = time_block
            self.original.save()
            return
        
        meeting = Meeting(
            room=self.room,
            professor=self.professor,
            time_block=time_block,
            section=self.edit_section.section)
        meeting.save()


class EditMeetingMessageBundle(models.Model):
    verbose_name = "Update meeting message bundle"

    REQUESTED = 'requested'
    ACCEPTED = 'accepted'
    REVISED_ACCEPTED = 'revised_accepted'
    DENIED = 'denied'

    choices = [
        (REQUESTED, 'Requested'),
        (ACCEPTED, 'Accepted'),
        (REVISED_ACCEPTED, 'Revised and Accepted'),
        (DENIED, 'Denied')
    ]
    date_sent = models.DateTimeField(auto_now_add=True, blank=True)
    is_read = models.BooleanField(default=False, blank=True)
    

    status = models.CharField(max_length=20, choices=choices)
    sender = models.ForeignKey(Professor, related_name="sent_bundles", on_delete=models.CASCADE)
        
    recipient = models.ForeignKey(Professor, related_name="receive_bundles", blank=True, null=True, default=None, on_delete=models.SET_NULL)
    # If none the request is no longer active and has been resolved
    # may not be in sync with the message information instead points to the most recent edit of it
    request = models.ForeignKey(EditRequestBundle, related_name="message_bundles", null=True, on_delete=models.SET_NULL)

    messages: QuerySet['EditMeetingMessage']

    class Meta:
        ordering = ["-date_sent"]
    
    def __str__(self) -> str:
        return f"{self.status.capitalize()} changes from {self.sender} on {self.date_sent.date()}"
    
    def messages_sorted(self) -> QuerySet['EditMeetingMessage']:

        return self.messages.order_by(models.Case(
            models.When(new_day=Day.MONDAY, then=1),
            models.When(new_day=Day.TUESDAY, then=2),
            models.When(new_day=Day.WEDNESDAY, then=3),
            models.When(new_day=Day.THURSDAY, then=4),
            models.When(new_day=Day.FRIDAY, then=5),
            models.When(new_day=Day.SATURDAY, then=6),
            models.When(new_day=Day.SUNDAY, then=7),),
            'new_start_time'
        )
    

class EditMeetingMessage(models.Model):
    verbose_name = "Change Meeting Message"

    is_changed = models.BooleanField()

    old_start_time = models.TimeField(blank=True, null=True)
    old_end_time = models.TimeField(blank=True, null=True)
    old_day = models.CharField(max_length=2, choices=Day.DAY_CHOICES, blank=True, null=True)
    old_building = models.ForeignKey(Building, related_name="messages_of_old", blank=True, null=True, on_delete=models.SET_NULL)
    old_room = models.ForeignKey(Room, related_name="messages_of_old", blank=True, null=True, on_delete=models.SET_NULL)
    old_professor = models.ForeignKey(Professor, related_name="messages_of_old", blank=True, null=True, on_delete=models.SET_NULL)

    new_start_time = models.TimeField()
    new_end_time = models.TimeField()
    new_day = models.CharField(max_length=2, choices=Day.DAY_CHOICES)
    new_building = models.ForeignKey(Building, related_name="messages_of_new", null=True, on_delete=models.SET_NULL)
    new_room = models.ForeignKey(Room, related_name="messages_of_new", null=True, on_delete=models.SET_NULL)
    new_professor = models.ForeignKey(Professor, related_name="messages_of_new", blank=True, null=True, on_delete=models.SET_NULL)

    section = models.ForeignKey(Section, related_name="messages", null=True, on_delete=models.SET_NULL)

    bundle = models.ForeignKey(EditMeetingMessageBundle, related_name="messages", null=True, on_delete=models.CASCADE)

    def get_old_start_time(self):
        return self.old_start_time.strftime('%I:%M %p')
    
    def get_old_end_time(self):
        return self.old_end_time.strftime('%I:%M %p')

    def get_new_start_time(self):
        return self.new_start_time.strftime('%I:%M %p')

    def get_new_end_time(self):
        return self.new_end_time.strftime('%I:%M %p')

