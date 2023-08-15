from django.db import models, IntegrityError, transaction
from authentication.models import Professor
from claim.models import *
from authentication.models import Professor

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

    def create(edit_meeting: dict, is_deleted: bool = False, primary_professor: Professor = None) -> 'EditMeeting':
        start_time = edit_meeting['startTime']
        end_time = edit_meeting['endTime']
        
        start_time = time.fromisoformat(start_time)
        end_time = time.fromisoformat(end_time)

        day = edit_meeting['day']

        building = edit_meeting.get('building')
        if isinstance(building, str):
            building = Building.objects.get(pk=building)
        
        room = edit_meeting.get('room')
        if (room == 'any') or (room == '') or (room is None):
            room = None
        else:
            room = Room.objects.get(pk=room)

        meeting = edit_meeting.get('meeting')
        if (meeting == '') or (meeting is None):
            meeting = None
            professor = primary_professor
        else:
            meeting = Meeting.objects.get(pk=meeting)
            professor = meeting.professor


        counter = edit_meeting['counter']
        
        return EditMeeting(
            start_time=start_time,
            end_time=end_time,
            day=day,
            building=building,
            room=room,
            meeting=meeting,
            counter=counter,
            professor=professor,
            is_deleted=is_deleted
        )
    
    def get_warnings(section_edit_meetings: list[tuple['Section', list['EditMeeting']]]) -> list[tuple[str, str]]:
        DANGER = 'danger'
        flattened: list[tuple[Section, EditMeeting]] = []
        for section, edit_meetings in section_edit_meetings:
            for edit_meeting in edit_meetings:
                flattened.append((section, edit_meeting))

        problems: list[tuple[str, str]] = []
        for i, section_meeting1 in enumerate(flattened[:-1]):
            section1, edit_meeting1 = section_meeting1
            for section2, edit_meeting2 in flattened[i+1:]:
                overlapping_time = (edit_meeting1.start_time_d() <= edit_meeting2.end_time_d()) \
                    and (edit_meeting1.end_time_d() >= edit_meeting2.start_time_d()) 
                same_day = (edit_meeting1.day == edit_meeting2.day)
                if not (overlapping_time and same_day): continue
                same_room = (edit_meeting1.room == edit_meeting2.room) \
                    and (edit_meeting1.room is not None)
                if same_room:
                    message = f"Meeting {edit_meeting1.counter} from {section1} overlaps {edit_meeting1.room} with meeting {edit_meeting2.counter} from {section2}."
                    problems.append((DANGER, message))
                    continue
                same_professor = (edit_meeting1.professor == edit_meeting2.room) \
                    and (edit_meeting1.room is not None)
                if same_professor:
                    message = f"Meeting {edit_meeting1.counter} from {section1} overlaps professor with meeting {edit_meeting2.counter} from {section2}."
                    problems.append((DANGER, message))
        return problems

    def is_changed(self) -> bool:
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

        return False

    def start_time_d(self):
        return timedelta(hours=self.start_time.hour, minutes=self.start_time.minute)

    def end_time_d(self):
        return timedelta(hours=self.end_time.hour, minutes=self.end_time.minute)

class EditRequestBundle(models.Model):
    verbose_name = "Edit Meeting Bundle"

    requester = models.ForeignKey(Professor, related_name="edit_request_bundles", on_delete=models.CASCADE)

class EditSectionRequest(models.Model):
    verbose_name = "Edit Section"

    is_primary = models.BooleanField()

    section = models.ForeignKey(Section, related_name="edit_sections", on_delete=models.CASCADE)
    bundle = models.ForeignKey(EditRequestBundle, related_name="edit_sections", on_delete=models.CASCADE)

    def get_warnings(edit_meetings: list[EditMeeting], section_pks: list[str], professor: Professor = None) -> list[tuple[str, str]]:
        DANGER = 'danger'
        WARNING = 'warning'
        problems: list[tuple[str, str]]= []

        
        # room empty check
        meetings = Meeting.objects.filter(section__term=self.term).exclude(section__pk__in=section_pks)

        # TODO change this once sharable meetings gets changed
        for edit_meeting in edit_meetings:
            if edit_meeting.room is None: continue
            overlaps_time_room = Q(
                time_block__start_end_time__start__lte = edit_meeting.end_time,
                time_block__start_end_time__end__gte = edit_meeting.start_time,
                time_block__day = edit_meeting.day,
                room=edit_meeting.room
            )

            overlapping_sections: set[str] = set(map(lambda m: str(m.section), meetings.filter(overlaps_time_room).all()))
            if overlapping_sections:
                sections = ", ".join(overlapping_sections)
                problems.append((DANGER, f"Meeting {edit_meeting.counter} overlaps {edit_meeting.room} with {sections}."))

        professor = self.primary_professor if professor is None else professor
        if professor is not None:
            for edit_meeting in edit_meetings:
                overlaps_time_room = Q(
                    time_block__start_end_time__start__lte = edit_meeting.end_time,
                    time_block__start_end_time__end__gte = edit_meeting.start_time,
                    time_block__day = edit_meeting.day,
                    professor=professor
                )
                
                overlapping_sections: set[str] = set(map(lambda m: str(m.section), meetings.filter(overlaps_time_room).all()))

                if overlapping_sections:
                    sections = ", ".join(overlapping_sections)
                    problems.append((DANGER, f"Meeting {edit_meeting.counter} overlaps professor with {sections}."))

        # regular time check
        total_time = sum(map(lambda t: t.end_time_d() - t.start_time_d(), edit_meetings), start=timedelta())

        if total_time not in self.course.get_approximate_times():
            problems.append((WARNING, f'The total time for this section does not match {self.course.credits} credit hours.'))

        for edit_meeting in edit_meetings:
            if edit_meeting.room is None: continue
            if not edit_meeting.room.is_general_purpose: continue
            time_blocks = TimeBlock.get_official_time_blocks(edit_meeting.start_time, edit_meeting.end_time, day=edit_meeting.day)
            department_allocations = DepartmentAllocation.objects.filter(
                department = self.course.subject.department,
                allocation_group__in = time_blocks.values('allocation_groups')
            )
            # when doing multiple sections in the request that add to the same allocation group
            #   This will not work properly
            if any(map(lambda d_a: d_a.exceeds_allocation(self.term), department_allocations.all())):
                problems.append((WARNING, f"Meeting {edit_meeting.counter} exceeds department constraints for that time slot."))
        
        # TODO implement a warning for giving a professor too many teaching hours

        return problems

    def no_recommendation(counter: str = 1, building: Building = None, professor=None) -> EditMeeting:
        t_s = time(hour=0, minute=0)
        t_e = time(hour=1, minute=15)

        return EditMeeting(start_time=t_s, end_time=t_e, day=Day.MONDAY, building=building, room=None, meeting=None, counter=counter, professor=professor)

    # recommendations currently to not take into account meetings in the group
    # TODO add professors to recommendations
    def get_recommendations(partial_meetings: list[EditMeeting] | None = None) -> None:
        if partial_meetings is None: partial_meetings = []

        existing_time = sum(map(lambda t: t.end_time_d() - t.start_time_d(),
            filter(lambda m: not m.is_deleted, partial_meetings)), start=timedelta())

        possible_times_to_achieve = list(map(lambda approx: approx - existing_time, self.course.get_approximate_times()))

        if len(partial_meetings) == 0:
            desired_building = Building.recommend(self.course, self.term)
        elif partial_meetings[0].building is not None:
            desired_building = partial_meetings[0].building
        else:
            desired_building = Building.recommend(self.course, self.term) 

        count = '1' if len(partial_meetings) == 0 else str(int(partial_meetings[-1].counter) + 1)
        if any(map(lambda time: time == timedelta(days=0), possible_times_to_achieve)):
            print('early exit 1')
            partial_meetings.append(Section.no_recommendation(counter=count, building=desired_building, professor=self.primary_professor))
            return
        
        if any(map(lambda approx: approx == TimeBlock.ONE_BLOCK * 3, possible_times_to_achieve)):
            print("recommending 3")
            partial_meetings.extend(self.recommend_2_time_blocks(desired_building, partial_meetings))
            edit_meeting = self.recommend_1_time_block(desired_building, partial_meetings)
            if edit_meeting is not None:
                partial_meetings.append(edit_meeting)
        elif any(map(lambda approx: approx == TimeBlock.ONE_BLOCK * 2, possible_times_to_achieve)):
            print("recommending 2")
            partial_meetings.extend(self.recommend_2_time_blocks(desired_building, partial_meetings))
        elif any(map(lambda approx: approx == TimeBlock.ONE_BLOCK, possible_times_to_achieve)):
            print("recommending 1")
            edit_meeting = self.recommend_1_time_block(desired_building, partial_meetings)
            if edit_meeting is not None:
                partial_meetings.append(edit_meeting)
        else:
            print('early exit 2')
            partial_meetings.append(Section.no_recommendation(counter=count, building=desired_building, professor=self.primary_professor))
            
    def recommend_2_time_blocks(building: Building = None, partial_meetings: list[EditMeeting] = None) -> list[EditMeeting]:
        professor = self.primary_professor # TODO change when shareable sections change
        if building is None:
            building = Building.recommend(self.course, self.term)
        if partial_meetings is None:
            partial_meetings = []
        if not partial_meetings:
            last_counter = "0"
        else:
            last_counter = partial_meetings[-1].counter
        allocations_counted: list[tuple[DepartmentAllocation, int]] = []
        department_allocations = DepartmentAllocation.objects.filter(
            department=self.course.subject.department
        )
        for dep_allo in department_allocations.all():
            allocations_counted.append( (dep_allo, dep_allo.count_rooms(self.term)) )
        
        allocations_counted.sort(key=lambda a_c: a_c[1])

        meetings_to_add: list[EditMeeting] = []
        for a_c in allocations_counted:
            department_allocation  = a_c[0]
            count = a_c[1]
            allocation_group = department_allocation.allocation_group
            # allocation_groups that have are at night have different numbers
            #   Therefore will need to be implemented differently
            if allocation_group.is_night(): continue

            number = allocation_group.time_blocks.first().number

            include_general = department_allocation.number_of_classrooms < count
            available_rooms = building.get_available_rooms_in_number(number, self.term, include_general, True)

            if available_rooms.exists(): continue
            for time_block in allocation_group.time_blocks.filter(number__isnull=False).all():
                start_time = time_block.start_end_time.start
                end_time = time_block.start_end_time.end
                day = time_block.day
                last_counter = str(int(last_counter) + 1)
                meetings_to_add.append(EditMeeting(
                    start_time=start_time,
                    end_time=end_time,
                    day=day,
                    building=building,
                    room=None, # Question on whether or not it should recommend a room in this case
                    meeting=None,
                    counter=last_counter,
                    professor=professor
                ))
            return meetings_to_add
        meetings_to_add.append(Section.no_recommendation(counter=last_counter, building=building, professor=professor))
        return meetings_to_add

    def recommend_1_time_block(self, building: Building, partial_meetings: list[EditMeeting] | None) -> list[EditMeeting]:
        professor = self.primary_professor # TODO change this for shared sections
        def get_all_time_blocks() -> QuerySet[TimeBlock]:
            in_problematic_meetings = Q()
            for m in partial_meetings:
                if m.is_deleted: continue
                in_problematic_meetings |= Q(
                    start_end_time__start__lte=m.end_time,
                    start_end_time__end__gte=m.start_time,
                    day=m.day
                )
            if professor is not None:
                for m in professor.meetings.filter(section__term=self.term).exclude(section__pk=self.pk).all():
                    tm = m.time_block
                    in_problematic_meetings |= Q(
                    start_end_time__start__lte=tm.start_end_time.end,
                    start_end_time__end__gte=tm.start_end_time.start,
                    day=tm.day
                )

            time_blocks = TimeBlock.objects \
                .filter(number__isnull=False) \
                .exclude(number__in=TimeBlock.LONG_NIGHT_NUMBERS) \
                .exclude(in_problematic_meetings)
            
            return time_blocks
        time_blocks_info: list[tuple[TimeBlock, int, Room]] = []
        if partial_meetings is None:
            last_counter = 0
            partial_meetings = []
        else:
            last_counter = partial_meetings[-1].counter
        if any([partial_meetings is None, all(map(lambda m: m.is_deleted, partial_meetings))]):
            time_blocks = get_all_time_blocks()
            for time_block in time_blocks.all():
                department_allocation = DepartmentAllocation.objects.get(
                    department = self.course.subject.department,
                    allocation_group=time_block.allocation_groups.first()
                )

                count = department_allocation.count_rooms(self.term)
                time_blocks_info.append(
                    (time_block, count, None)
                )
        else:
            all_time_blocks = get_all_time_blocks()
            time_blocks = time_blocks = TimeBlock.objects.none()
            for edit_meeting in filter(lambda m: not m.is_deleted,partial_meetings):
                start = edit_meeting.start_time
                end = edit_meeting.end_time
                day = edit_meeting.day
                t_bs = TimeBlock.objects.filter(
                    number__isnull=False,
                    start_end_time__start__lte = end,
                    start_end_time__end__gte = start,
                    day=day
                )
                # sort of cheaty way to do this since this only works bc time blocks with the same number
                #   are never on the same day
                for t_b in t_bs.all():
                    time_blocks |= TimeBlock.objects \
                        .filter(number=t_b.number) \
                        .exclude(day=t_b.day)
            time_blocks = time_blocks.filter(pk__in=all_time_blocks.values('pk'))
            if not time_blocks.exists():
                time_blocks = all_time_blocks 
            for time_block in time_blocks.all():
                department_allocation = DepartmentAllocation.objects.get(
                    department = self.course.subject.department,
                    allocation_group=time_block.allocation_groups.first()
                )
                count = department_allocation.count_rooms(self.term)
                time_blocks_info.append(
                    (time_block, count, edit_meeting.room)
                )
                
        time_blocks_info.sort(key=lambda t_b: t_b[1])
        for time_block, count, room in time_blocks_info:
            department_allocation = DepartmentAllocation.objects.get(
                department = self.course.subject.department,
                allocation_group=time_block.allocation_groups.first()
            )
            start_time = time_block.start_end_time.start
            end_time = time_block.start_end_time.end
            day = time_block.day

            # include_general = count < department_allocation.number_of_classrooms
            open_rooms = building.get_available_rooms(start_time, end_time, day, self.term, True, section=self)
            
            if not open_rooms.exists(): continue

            try:
                if room is not None:
                    desired_room = open_rooms.get(id=room.pk)
                else:
                    desired_room = None # question on whether we should select the room
            except Room.DoesNotExist:
                continue

            return EditMeeting(
                start_time=start_time,
                end_time=end_time,
                day=day,
                building=building,
                room=desired_room,
                meeting=None,
                counter=str(int(last_counter) + 1),
                professor=professor
            )

        return Section.no_recommendation(counter=str(int(last_counter) + 1), building=building, professor=professor)


class EditMeetingRequest(models.Model):
    verbose_name = "Edit Meeting"

    start_time = models.TimeField()
    end_time = models.TimeField()
    day = models.CharField(max_length=2, choices=Day.DAY_CHOICES)

    building = models.ForeignKey(Building, related_name="edit_requests", blank=True, null=True, on_delete=models.SET_NULL)
    # If the room is None then the new meeting can be any room in the building 
    room = models.ForeignKey(Room, related_name="edit_requests", blank=True, null=True, on_delete=models.SET_NULL)
    professor = models.ForeignKey(Professor, related_name="edit_requests_involving", blank=True, null=True, default=None, on_delete=models.CASCADE)
    # If there is no original then it is a created meeting
    original = models.ForeignKey(Meeting, related_name="edit_meetings", blank=True, null=True, default=None, on_delete=models.CASCADE)

    edit_section = models.ForeignKey(EditSectionRequest, related_name="edit_meetings", on_delete=models.CASCADE)


    messages: QuerySet['EditMeetingMessage']

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
            request=self,
            bundle=bundle,
        )
        message.save()
        return message


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

    messages: QuerySet['EditMeetingMessage']

    class Meta:
        ordering = ["date_sent"]
    

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

    # If none the request is no longer active and has been resolved
    # may not be in sync with the message information instead points to the most recent edit of it
    request = models.ForeignKey(EditMeetingRequest, related_name="messages", null=True, on_delete=models.SET_NULL)
    bundle = models.ForeignKey(EditMeetingMessageBundle, related_name="messages", null=True, on_delete=models.CASCADE)

    def get_old_start_time(self):
        return self.old_start_time.strftime('%I:%M %p')
    
    def get_old_end_time(self):
        return self.old_end_time.strftime('%I:%M %p')

    def get_new_start_time(self):
        return self.new_start_time.strftime('%I:%M %p')

    def get_new_end_time(self):
        return self.new_end_time.strftime('%I:%M %p')

