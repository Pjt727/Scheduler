# pyright does not like me importing * here bc of the type checking import i think
from dataclasses import dataclass
from datetime import time, timedelta
from typing import TypedDict

from authentication.models import Professor
from claim.models import (
    Building,
    Course,
    Day,
    Department,
    DepartmentAllocation,
    Meeting,
    Room,
    Section,
    StartEndTime,
    Term,
    TimeBlock,
)
from django.db import models
from django.db.models import Q, QuerySet
from django.http import QueryDict


class TimeSlot(TypedDict):
    start: time
    end: time
    day: str
    allocation_max: int
    allocation: int
    numbers: list[str]


class Problem:
    DANGER = "danger"
    WARNING = "warning"

    def __init__(self, type: str, text: str) -> None:
        self.type = type
        self.text = text


@dataclass
class Node:
    id: int
    meeting: "EditMeeting"
    overlapping_nodes: list["Node"]
    is_seen: bool

    def __eq__(self, other):
        return isinstance(other, Node) and self.id == other.id

    def __hash__(self):
        return hash(self.id)


def add_children(
    nodes: list[Node],
    running_group: list["EditMeeting"],
    nodes_in_group: set[Node],
):
    if len(nodes) == 0:
        return
    for node in nodes:
        node.is_seen = True
        if node not in nodes_in_group:
            nodes_in_group.add(node)
            running_group.append(node.meeting)
            add_children(node.overlapping_nodes, running_group, nodes_in_group)


@dataclass
class EditMeeting:
    start_time: time | None
    duration: timedelta
    day: str | None
    building: Building | None
    room: Room | None
    meeting: Meeting | None
    section: Section
    counter: int
    professor: Professor | None = None
    is_deleted: bool = False

    def overlaps_with(self, other_meeting: "EditMeeting") -> bool:
        nullables = [
            self.day,
            other_meeting.day,
            self.start_time,
            other_meeting.start_time,
        ]
        if any(map(lambda n: n is None, nullables)):
            return False
        if self.day != other_meeting.day:
            return False
        start1 = self.start_time_d()
        end1 = self.start_time_d() + self.duration
        start2 = other_meeting.start_time_d()
        end2 = other_meeting.start_time_d() + other_meeting.duration
        return end1 >= start2 and start1 <= end2

    # could possibly cause weird groups of a day if meetings overlap into more than
    #   1 timeslot and when there's a lot of overlapping sections
    @staticmethod
    def get_intersection_groups(
        meetings: list["EditMeeting"],
    ) -> list[list["EditMeeting"]]:
        """
        each intersection group is like the different isolated groups of nodes if edges
        are made on connections. Connections are made on time overlap and for the same section
        """

        # make all meetings into nodes
        nodes: list[Node] = []
        for i, meeting in enumerate(meetings):
            nodes.append(
                Node(id=i, meeting=meeting, overlapping_nodes=[], is_seen=False)
            )

        # add the initial edges to the nodes if their times overlap or
        # if their sections are the same
        for node1 in nodes:
            meeting1 = node1.meeting
            for node2 in nodes:
                if node1 == node2:
                    continue
                meeting2 = node2.meeting
                if (
                    meeting1.section.pk == meeting2.section.pk
                    or meeting1.overlaps_with(meeting2)
                ):
                    # we also know meeting 2 overlaps
                    # but that will be added later anyway
                    node1.overlapping_nodes.append(node2)

        intersection_groups: list[list[EditMeeting]] = []
        for node in nodes:
            if node.is_seen:
                # the node was traversed in a different iteration so is already part of another group
                continue
            intersection_group = [node.meeting]
            node.is_seen = True
            add_children(node.overlapping_nodes, intersection_group, set())
            intersection_groups.append(intersection_group)

        return intersection_groups

    @staticmethod
    def from_meeting(meeting: Meeting, counter: int) -> "EditMeeting":
        time_block = meeting.time_block
        start_end_time = None if time_block is None else time_block.start_end_time
        start_time = None if start_end_time is None else start_end_time.start
        day = None if time_block is None else time_block.day
        room = meeting.room
        building = None if room is None else room.building

        edit_meeting = EditMeeting(
            start_time=start_time,
            duration=meeting.get_duration(),
            day=day,
            building=building,
            room=meeting.room,
            meeting=meeting,
            section=meeting.section,
            counter=counter,
            professor=meeting.professor,
            is_deleted=False,
        )
        return edit_meeting

    @staticmethod
    def from_section(section: Section) -> list["EditMeeting"]:
        edit_meetings = []

        # make sure this is sorted
        for i, meeting in enumerate(section.meetings_sorted().all(), start=1):
            edit_meeting = EditMeeting.from_meeting(meeting, i)
            edit_meetings.append(edit_meeting)

        return edit_meetings

    # I cant type hint 'EditMeeting' | None  sadly :(
    @staticmethod
    def create_all(data: QueryDict) -> tuple[list["EditMeeting"], "EditMeeting"]:
        are_deleted = data.getlist("isDeleted")
        sections = data.getlist("section")
        start_times = data.getlist("startTime")
        durations = data.getlist("duration")
        days = data.getlist("day")
        buildings = data.getlist("building")
        rooms = data.getlist("room")
        professors = data.getlist("professor")
        counters = data.getlist("counter")

        originals = data.getlist("original")

        selected_edit_meeting = None

        changed_section = data.get("outerSection")
        changed_counter = data.get("outerCounter")

        edit_meetings: list[EditMeeting] = []
        for i in range(len(are_deleted)):
            section_pk = sections[i]
            section = Section.objects.get(pk=section_pk)
            counter = int(counters[i])

            start_time = start_times[i]
            if start_time == "None":
                start_time = None
            else:
                start_time = time.fromisoformat(start_time)
            duration = durations[i]
            hour, minute = duration.split(":")
            duration = timedelta(hours=int(hour), minutes=int(minute))

            day = days[i]
            if day not in Day.CODE_TO_VERBOSE:
                day = None

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
            edit_meeting = EditMeeting(
                start_time=start_time,
                duration=duration,
                counter=counter,
                day=day,
                building=building,
                section=section,
                room=room,
                meeting=meeting,
                professor=professor,
                is_deleted=is_deleted,
            )
            edit_meetings.append(edit_meeting)
            if changed_section == section_pk and changed_counter == counters[i]:
                selected_edit_meeting = edit_meeting

        return edit_meetings, selected_edit_meeting  # pyright: ignore

    def get_time_intervals(self) -> list[tuple[time, time]]:
        if not self.day:
            return []
        duration = self.duration
        time_intervals = TimeBlock.get_time_intervals(duration, self.day)

        return time_intervals

    def room_problems(
        self, sections_to_exclude: list[Section] | None = None, check_allocation=True
    ) -> list[Problem]:
        if sections_to_exclude is None:
            sections_to_exclude = [self.section]

        overlaps_time = Q(
            time_block__start_end_time__start__lte=self.get_end_time(),
            time_block__start_end_time__end__gte=self.start_time,
            time_block__day=self.day,
        )

        meetings = (
            Meeting.objects.filter(section__term=self.section.term)
            .exclude(section__in=sections_to_exclude)
            .filter(overlaps_time)
        )

        problems = []
        if self.room is None:
            return problems

        sections = list(
            map(
                lambda s: str(Section.objects.get(pk=s["section"])),
                meetings.filter(room=self.room).values("section").distinct(),
            )
        )
        if sections:
            sections_text = ", ".join(sections)
            text = f"Meeting {self.counter} overlaps {self.room} with {sections_text}."
            problems.append(Problem(Problem.DANGER, text))

        if not (self.room.is_general_purpose and check_allocation):
            return problems

        if not self.start_time:
            return problems
        time_blocks = TimeBlock.get_official_time_blocks(
            self.start_time, self.get_end_time(), day=self.day
        )
        department_allocations = DepartmentAllocation.objects.filter(
            department=self.section.course.subject.department,
            allocation_group__in=time_blocks.values("allocation_groups"),
        )

        if any(
            map(
                lambda d_a: d_a.exceeds_allocation(self.section.term),
                department_allocations.all(),
            )
        ):
            text = f"Meeting {self.counter} exceeds department constraints for that time slot."
            problems.append(Problem(Problem.WARNING, text))

        return problems

    def professor_problems(
        self, sections_to_exclude: list[Section] | None = None
    ) -> list[Problem]:
        if sections_to_exclude is None:
            sections_to_exclude = [self.section]

        overlaps_time = Q(
            time_block__start_end_time__start__lte=self.get_end_time(),
            time_block__start_end_time__end__gte=self.start_time,
            time_block__day=self.day,
        )

        meetings = (
            Meeting.objects.filter(section__term=self.section.term)
            .exclude(section__in=sections_to_exclude)
            .filter(overlaps_time)
        )

        problems = []
        if self.professor is None:
            return problems

        sections = set(
            map(lambda m: str(m.section), meetings.filter(professor=self.professor))
        )
        if sections:
            sections_text = ", ".join(sections)
            text = f"Meeting {self.counter} overlaps with {sections_text} that {self.professor} also teaches."
            problems.append(Problem(Problem.DANGER, text))

        return problems

    @staticmethod
    def get_group_problems(edit_meetings: list["EditMeeting"]) -> list[Problem]:
        problems: list[Problem] = []
        for i, edit_meeting1 in enumerate(edit_meetings[:-1]):
            for edit_meeting2 in edit_meetings[i + 1 :]:
                e_m1_start_d = edit_meeting1.start_time_d()
                e_m1_end_d = e_m1_start_d + edit_meeting1.duration
                e_m2_start_d = edit_meeting2.start_time_d()
                e_m2_end_d = e_m2_start_d + edit_meeting2.duration

                overlapping_time = (e_m1_start_d <= e_m2_end_d) and (
                    e_m1_end_d >= e_m2_start_d
                )

                same_day = edit_meeting1.day == edit_meeting2.day
                if not (overlapping_time and same_day):
                    continue
                same_room = (edit_meeting1.room == edit_meeting2.room) and (
                    edit_meeting1.room is not None
                )
                if same_room:
                    message = f"Meeting {edit_meeting1.counter} from {edit_meeting1.section} overlaps {edit_meeting1.room} with meeting {edit_meeting2.counter} from {edit_meeting2.section}."
                    problems.append(Problem(Problem.DANGER, message))
                same_professor = (
                    edit_meeting1.professor == edit_meeting2.professor
                ) and (edit_meeting1.professor is not None)
                if same_professor:
                    message = f"Meeting {edit_meeting1.counter} from {edit_meeting1.section} overlaps with meeting {edit_meeting2.counter} from {edit_meeting2.section} that {edit_meeting1.professor} teaches."
                    problems.append(Problem(Problem.DANGER, message))
        return problems

    @staticmethod
    def get_section_problems(
        edit_meetings: list["EditMeeting"], sections_to_exclude: list[Section]
    ) -> list[Problem]:
        sections = set()
        for m in edit_meetings:
            sections.add(m.section)
        assert len(sections) == 1
        first_section = next(iter(sections), None)
        assert first_section is not None

        problems: list[Problem] = []
        section = edit_meetings[0].section

        for edit_meeting in edit_meetings:
            meeting_problems = edit_meeting.room_problems(
                sections_to_exclude, check_allocation=False
            )
            problems.extend(meeting_problems)
            problems.extend(edit_meeting.professor_problems(sections_to_exclude))

        total_time = sum(map(lambda t: t.duration, edit_meetings), start=timedelta())

        if total_time not in section.course.get_approximate_times():
            message = f"The total time for this section does not match {section.course.credits} credit hours."
            problems.append(Problem(Problem.WARNING, message))
        in_meetings = Q()
        for edit_meeting in edit_meetings:
            in_meetings |= Q(
                day=edit_meeting.day,
                start_end_time__start__lte=edit_meeting.get_end_time(),
                start_end_time__end__gte=edit_meeting.start_time,
            )
        official_time_blocks = (
            TimeBlock.objects.filter(number__isnull=False)
            .filter(in_meetings)
            .distinct()
        )
        exceeds_allocation = False
        dep_allocations = DepartmentAllocation.objects.filter(
            allocation_group__in=official_time_blocks.values("allocation_groups")
        )

        for dep_allocation in dep_allocations:
            # Maybe think about making this not add one for the section
            if dep_allocation.exceeds_allocation(first_section.term):
                exceeds_allocation = True
                break
        if exceeds_allocation:
            message = f"The department allocation is exceeded for one or more of these meetings."
            problems.append(Problem(Problem.WARNING, message))

        # TODO insure that time slots are followed
        # TODO? implement a warning for giving a professor too many teaching hours

        return problems

    def is_changed(self) -> bool:
        if self.is_deleted:
            return True
        if self.meeting is None:
            return True
        if self.meeting.room != self.room:
            return True
        if self.meeting.professor != self.professor:
            return True
        og_time_block = self.meeting.time_block
        if og_time_block is None:
            if self.start_time != None:
                return True
        else:
            if og_time_block.day != self.day:
                return True
            og_start_time = og_time_block.start_end_time.start
            og_duration = self.meeting.get_duration()
            if self.duration != og_duration:
                return True
            if self.start_time != og_start_time:
                return True
        return False

    @staticmethod
    def get_conflicting_meetings(
        *_,
        term: Term,
        room: Room | None,
        professor: Professor | None,
        sections_to_exclude: set[Section],
        conflicting_courses: set[Course],
    ) -> QuerySet[Meeting]:
        meetings = Meeting.objects.none()
        if professor:
            meetings |= professor.meetings.filter(section__term=term)
        if room:
            meetings |= Meeting.objects.filter(room=room, section__term=term)
        meetings |= Meeting.objects.filter(
            section__course__in=conflicting_courses, section__term=term
        )
        meetings = meetings.exclude(section__in=sections_to_exclude)
        meetings |= Meeting.objects.filter(section__in=sections_to_exclude)

        meetings = meetings.exclude(section__in=sections_to_exclude).distinct()

        return meetings

    @staticmethod
    def get_timeblock_exclusion_filter(
        conflicting_meetings: QuerySet[Meeting], duration: timedelta
    ) -> Q:
        duration_after_time_block = duration - TimeBlock.ONE_BLOCK
        in_meetings = Q()
        for meeting in conflicting_meetings.all():
            if meeting.time_block is None:
                continue
            new_start_d = (
                meeting.time_block.start_end_time.start_d() - duration_after_time_block
            )
            new_start_t = time(
                hour=new_start_d.seconds // 3600,
                minute=(new_start_d.seconds % 3600) // 60,
            )
            in_meetings |= Q(
                day=meeting.time_block.day,
                start_end_time__start__lte=meeting.time_block.start_end_time.end,
                start_end_time__end__gte=new_start_t,
            )

        return in_meetings

    # This is now a completely different thing from open_slots
    # just used to show the VISUALLY open slots
    @staticmethod
    def get_open_slots(
        *_,
        term: Term,
        building: Building | None,
        room: Room | None,
        department: Department | None,
        professor: Professor | None,
        sections_to_exclude: set[Section],
        duration: timedelta,
        conflicting_courses: set[Course],
        enforce_allocation: bool = False,
    ) -> tuple[QuerySet[Meeting], list[TimeSlot]]:
        meetings = EditMeeting.get_conflicting_meetings(
            term=term,
            room=room,
            professor=professor,
            sections_to_exclude=sections_to_exclude,
            conflicting_courses=conflicting_courses,
        )

        time_block_filter = EditMeeting.get_timeblock_exclusion_filter(
            conflicting_meetings=meetings, duration=duration
        )
        time_blocks = TimeBlock.objects.filter(number__isnull=False).exclude(
            time_block_filter
        )

        open_slots = []
        for time_block in time_blocks.all():
            new_end_d = time_block.start_end_time.start_d() + duration
            new_end_t = time(
                hour=new_end_d.seconds // 3600, minute=(new_end_d.seconds % 3600) // 60
            )
            allocation_group = time_block.allocation_groups.first()
            assert allocation_group is not None
            # TODO MAYBE CLEAN UP DATABASE SO I CAN SAFELY USE .get()
            department_allocation = allocation_group.department_allocations.filter(
                department=department
            ).first()
            assert department_allocation is not None
            allocation_max = department_allocation.number_of_classrooms
            allocation = department_allocation.count_rooms(term)
            slot: TimeSlot = {
                "start": time_block.start_end_time.start,
                "end": new_end_t,
                "day": time_block.day,
                "allocation_max": allocation_max,
                "allocation": allocation,
                "numbers": [str(time_block.number)],
            }

            if room is None and building:
                # have to check if there is any other room
                available_rooms = building.get_available_rooms(
                    start_time=slot["start"],
                    end_time=slot["end"],
                    day=slot["day"],
                    term=term,
                    include_general=(slot["allocation_max"] > slot["allocation"])
                    or (not enforce_allocation),
                    sections_to_exclude=sections_to_exclude,
                )
                if not available_rooms.exists():
                    continue
                open_slots.append(slot)
            elif not enforce_allocation:
                open_slots.append(slot)
            elif slot["allocation_max"] > slot["allocation"]:
                open_slots.append(slot)
            elif room is None or not room.is_general_purpose:
                open_slots.append(slot)

        return meetings, open_slots

    # There are still a lot problems with this and probably with forever have a lot of problems but at this points
    # it does not need to be perfect
    @staticmethod
    def open_slots(
        *_,
        room: Room | None,
        professor: Professor | None,
        building: Building | None,
        section: Section,
        duration: timedelta,
        edit_meetings: list["EditMeeting"],
        meetings: QuerySet[Meeting],
        enforce_allocation: bool = True,
    ) -> list[TimeSlot]:
        if building is None:
            building = Building.recommend(section.course, term=section.term)
        in_edit_meetings = Q()
        # duration is always greater than or equal to TimeBlock.ONE_BLOCK
        duration_after_time_block = duration - TimeBlock.ONE_BLOCK
        sections_to_exclude: set[Section] = set()
        for edit_meeting in edit_meetings:
            sections_to_exclude.add(edit_meeting.section)
            same_professor = (professor == edit_meeting.professor) and (
                professor is not None
            )
            same_room = (room == edit_meeting.room) and (room is not None)

            if not (same_professor or same_room):
                continue
            new_start_d = edit_meeting.start_time_d() - duration_after_time_block
            new_start_t = time(
                hour=new_start_d.seconds // 3600,
                minute=(new_start_d.seconds % 3600) // 60,
            )
            in_edit_meetings |= Q(
                day=edit_meeting.day,
                start_end_time__start__lte=edit_meeting.get_end_time(),
                start_end_time__end__gte=new_start_t,
            )

        in_meetings = Q()
        for meeting in meetings.all():
            if meeting.time_block is None:
                continue
            new_start_d = (
                meeting.time_block.start_end_time.start_d() - duration_after_time_block
            )
            new_start_t = time(
                hour=new_start_d.seconds // 3600,
                minute=(new_start_d.seconds % 3600) // 60,
            )
            in_meetings |= Q(
                day=meeting.time_block.day,
                start_end_time__start__lte=meeting.time_block.start_end_time.end,
                start_end_time__end__gte=new_start_t,
            )
        time_blocks = (
            TimeBlock.objects.filter(number__isnull=False)
            .exclude(number__in=TimeBlock.LONG_NIGHT_NUMBERS)
            .exclude(in_edit_meetings)
            .exclude(in_meetings)
        )
        open_slots = []
        for time_block in time_blocks.all():
            new_end_d = time_block.start_end_time.start_d() + duration
            new_end_t = time(
                hour=new_end_d.seconds // 3600, minute=(new_end_d.seconds % 3600) // 60
            )
            tbs = TimeBlock.objects.filter(
                number__isnull=False, day=time_block.day, start_end_time__end=new_end_t
            )
            if not tbs.exists():
                continue
            department_allocation = DepartmentAllocation.objects.get(
                department=section.course.subject.department,
                allocation_group=time_block.allocation_groups.first(),
            )

            allocation_max = department_allocation.number_of_classrooms
            # STILL COUNTS WITHOUT CHANGES WHEN EDITING
            allocation = department_allocation.count_rooms(section.term)
            slot: TimeSlot = {
                "start": time_block.start_end_time.start,
                "end": new_end_t,
                "day": time_block.day,
                "allocation_max": allocation_max,
                "allocation": allocation,
                "numbers": [str(time_block.number)],
            }
            if room is None:
                # DOES NOT INCLUDE ONES FROM EDIT MEETINGS
                available_rooms = building.get_available_rooms(
                    start_time=slot["start"],
                    end_time=slot["end"],
                    day=slot["day"],
                    term=section.term,
                    include_general=(slot["allocation_max"] > slot["allocation"])
                    or (not enforce_allocation),
                    sections_to_exclude=sections_to_exclude,
                )
                if not available_rooms.exists():
                    continue
                open_slots.append(slot)
                continue

            if not enforce_allocation:
                open_slots.append(slot)
                continue
            if slot["allocation_max"] > slot["allocation"]:
                open_slots.append(slot)
                continue
            if not room.is_general_purpose:
                open_slots.append(slot)
                continue

        return open_slots

    # Recommending meeting is painfully complex and pretty slow doing it this way.
    # To remove some of the complexity open_slots is used which probably is not the best way
    # There should be A LOT better of way to recommend bulk subjects without requesting
    # A lot of time improvements can be made here but like idk

    @staticmethod
    def recommend_meetings(
        edit_meetings: list["EditMeeting"],
        professor: Professor | None,
        section: Section,
    ) -> list["EditMeeting"]:
        total_duration = timedelta()
        sections_to_exclude = set()
        number_room_complement: list[tuple[int, Room | None]] = []
        last_counter = 1
        for edit_meeting in edit_meetings:
            sections_to_exclude.add(edit_meeting.section)
            if edit_meeting.section != section:
                continue
            last_counter = max(last_counter, edit_meeting.counter)
            if edit_meeting.is_deleted:
                continue
            tms = TimeBlock.get_official_time_blocks(
                edit_meeting.start_time, edit_meeting.get_end_time(), edit_meeting.day
            )
            for tm in tms.all():
                in_complements_flag = False
                for i, (num, _) in enumerate(number_room_complement):
                    if num != tm.number:
                        continue
                    del number_room_complement[i]
                    in_complements_flag = True
                if in_complements_flag:
                    continue
                assert tm.number is not None
                number_room_complement.append((tm.number, edit_meeting.room))
            total_duration += edit_meeting.duration
        edit_meetings = list(filter(lambda m: not m.is_deleted, edit_meetings))
        building = Building.recommend(section.course, term=section.term)
        no_recommendation = EditMeeting(
            start_time=time(0),
            duration=TimeBlock.ONE_BLOCK,
            day="MO",
            building=building,
            room=None,
            meeting=None,
            section=section,
            counter=last_counter + 1,
            professor=professor,
        )

        valid_times = section.course.get_approximate_times()
        valid_added_times = list(map(lambda t: t - total_duration, valid_times))
        base_meetings = Meeting.objects.none()
        if professor:
            base_meetings |= professor.meetings.filter(
                section__term=section.term
            ).exclude(section__in=sections_to_exclude)

        # purposefully slow to ensure that the same logic as open_slots is used
        # I also hate this code
        if timedelta(0) in valid_added_times:
            return [no_recommendation]
        elif TimeBlock.ONE_BLOCK in valid_added_times:
            return EditMeeting.recommend_one_block(
                edit_meetings=edit_meetings,
                professor=professor,
                base_meetings=base_meetings,
                section=section,
                number_room_complements=number_room_complement,
                sections_to_exclude=sections_to_exclude,
                last_counter=last_counter,
            )
        elif (TimeBlock.ONE_BLOCK * 2) in valid_added_times:
            return EditMeeting.recommend_two_block(
                edit_meetings=edit_meetings,
                professor=professor,
                base_meetings=base_meetings,
                section=section,
                number_room_complements=number_room_complement,
                sections_to_exclude=sections_to_exclude,
                last_counter=last_counter,
            )
        elif any(map(lambda t: t == TimeBlock.ONE_BLOCK * 3, valid_added_times)):
            recommended_edit_meetings = EditMeeting.recommend_two_block(
                edit_meetings=edit_meetings,
                professor=professor,
                base_meetings=base_meetings,
                section=section,
                number_room_complements=number_room_complement,
                sections_to_exclude=sections_to_exclude,
                last_counter=last_counter,
            )
            edit_meetings.extend(recommended_edit_meetings)
            recommended_edit_meetings.extend(
                EditMeeting.recommend_one_block(
                    edit_meetings=edit_meetings,
                    professor=professor,
                    base_meetings=base_meetings,
                    section=section,
                    number_room_complements=number_room_complement,
                    sections_to_exclude=sections_to_exclude,
                    last_counter=last_counter + len(recommended_edit_meetings),
                )
            )
            return recommended_edit_meetings

        return [no_recommendation]

    @staticmethod
    def no_recommendation(
        section: Section, counter: int, building: Building | None = None
    ):
        return EditMeeting(
            start_time=time(0),
            duration=TimeBlock.ONE_BLOCK,
            day="MO",
            building=building,
            room=None,
            meeting=None,
            section=section,
            counter=counter,
            professor=section.primary_professor,
        )

    @staticmethod
    def recommend_one_block(
        *_,
        edit_meetings: list["EditMeeting"],
        professor: Professor | None,
        base_meetings: QuerySet[Meeting],
        section: Section,
        number_room_complements: list[tuple[int, Room | None]],
        sections_to_exclude: set[Section],
        last_counter: int,
    ) -> list["EditMeeting"]:

        for num, room in number_room_complements:
            if room:
                meetings = base_meetings | Meeting.objects.filter(
                    room=room, section__term=section.term
                ).exclude(section__in=sections_to_exclude)
            else:
                meetings = base_meetings
            building = (
                Building.recommend(section.course, term=section.term)
                if room is None
                else room.building
            )
            open_slots: list[TimeSlot] = EditMeeting.open_slots(
                room=room,
                professor=professor,
                building=building,
                duration=TimeBlock.ONE_BLOCK,
                section=section,
                edit_meetings=edit_meetings,
                meetings=meetings,
                enforce_allocation=False,
            )
            for open_slot in open_slots:
                if num not in open_slot["numbers"]:
                    continue
                return [
                    EditMeeting(
                        start_time=open_slot["start"],
                        duration=TimeBlock.ONE_BLOCK,
                        day=open_slot["day"],
                        building=building,
                        room=room,
                        meeting=None,
                        section=section,
                        counter=last_counter + 1,
                        professor=professor,
                    )
                ]
        building = Building.recommend(section.course, term=section.term)
        open_slots: list[TimeSlot] = EditMeeting.open_slots(
            room=None,
            professor=professor,
            building=building,
            duration=TimeBlock.ONE_BLOCK,
            edit_meetings=edit_meetings,
            section=section,
            meetings=base_meetings,
            enforce_allocation=False,
        )
        open_slots.sort(key=lambda s: s["allocation"] / s["allocation_max"])
        best_open_slot = open_slots[0]
        return [
            EditMeeting(
                start_time=best_open_slot["start"],
                duration=TimeBlock.ONE_BLOCK,
                day=best_open_slot["day"],
                building=building,
                room=None,
                meeting=None,
                section=section,
                counter=last_counter + 1,
                professor=professor,
            )
        ]

    @staticmethod
    def recommend_two_block(
        *_,
        edit_meetings: list["EditMeeting"],
        professor: Professor | None,
        base_meetings: QuerySet[Meeting],
        section: Section,
        number_room_complements: list[tuple[int, Room | None]],
        sections_to_exclude: set[Section],
        last_counter: int,
    ) -> list["EditMeeting"]:
        recommended = []
        # There should at most only be one complement
        if number_room_complements:
            num, room = number_room_complements[0]
            if room:
                meetings = base_meetings | Meeting.objects.filter(
                    room=room, section__term=section.term
                ).exclude(section__in=sections_to_exclude)
            else:
                meetings = base_meetings

            building = (
                Building.recommend(section.course, term=section.term)
                if room is None
                else room.building
            )
            open_slots: list[TimeSlot] = EditMeeting.open_slots(
                room=room,
                professor=professor,
                building=building,
                duration=TimeBlock.ONE_BLOCK,
                edit_meetings=edit_meetings,
                meetings=meetings,
                enforce_allocation=False,
                section=section,
            )
            for open_slot in open_slots:
                if num not in open_slot["numbers"]:
                    continue
                building = building if room is None else room.building
                last_counter += 1
                recommended.append(
                    EditMeeting(
                        start_time=open_slot["start"],
                        duration=TimeBlock.ONE_BLOCK,
                        day=open_slot["day"],
                        building=building,
                        room=room,
                        meeting=None,
                        section=section,
                        counter=last_counter,
                        professor=professor,
                    )
                )
                recommended.extend(
                    EditMeeting.recommend_one_block(
                        edit_meetings=edit_meetings,
                        professor=professor,
                        base_meetings=base_meetings,
                        section=section,
                        number_room_complements=[],
                        sections_to_exclude=sections_to_exclude,
                        last_counter=last_counter,
                    )
                )
                return recommended
        building = Building.recommend(section.course, term=section.term)
        open_slots = EditMeeting.open_slots(
            room=None,
            professor=professor,
            building=building,
            duration=TimeBlock.ONE_BLOCK,
            edit_meetings=edit_meetings,
            meetings=base_meetings,
            enforce_allocation=False,
            section=section,
        )
        # yeah... i know
        seen_numbers: list[str] = []
        for i, slot1 in enumerate(open_slots):
            if any(number in seen_numbers for number in slot1["numbers"]):
                continue
            available_rooms_slot1 = building.get_available_rooms(
                start_time=slot1["start"],
                end_time=slot1["end"],
                day=slot1["day"],
                term=section.term,
                include_general=False,
                sections_to_exclude=sections_to_exclude,
            )
            slot2 = None
            if i + 1 == len(open_slots):
                continue
            for s in open_slots[i + 1 :]:
                if s["numbers"] == slot1["numbers"]:
                    slot2 = s
            if slot2 is None:
                continue
            available_rooms_slot2 = building.get_available_rooms(
                start_time=slot2["start"],
                end_time=slot2["end"],
                day=slot2["day"],
                term=section.term,
                include_general=False,
                sections_to_exclude=sections_to_exclude,
            )
            intersecting_rooms = available_rooms_slot1 & available_rooms_slot2
            if not intersecting_rooms.exists():
                continue

            room = intersecting_rooms.first()
            assert room is not None

            m1 = EditMeeting(
                start_time=slot1["start"],
                duration=TimeBlock.ONE_BLOCK,
                day=slot1["day"],
                building=room.building,
                room=room,
                meeting=None,
                section=section,
                counter=last_counter + 1,
                professor=professor,
            )
            m2 = EditMeeting(
                start_time=slot2["start"],
                duration=TimeBlock.ONE_BLOCK,
                day=slot2["day"],
                building=room.building,
                room=room,
                meeting=None,
                section=section,
                counter=last_counter + 2,
                professor=professor,
            )
            return [m1, m2]

        return [
            EditMeeting.no_recommendation(
                section=section, counter=last_counter + 1, building=building
            )
        ]

    def save_as_request(
        self, edit_section: "EditSectionRequest"
    ) -> "EditMeetingRequest":
        request = EditMeetingRequest(
            start_time=self.start_time,
            duration=self.duration,
            day=self.day,
            building=self.building,
            room=self.room,
            professor=self.professor,
            original=self.meeting,
            edit_section=edit_section,
            is_deleted=self.is_deleted,
        )
        request.save()
        return request

    def get_meeting_pk(self) -> None | str:
        return None if self.meeting is None else self.meeting.pk

    def get_end_time(self) -> time:
        if self.start_time is None:
            return time()
        total_seconds = self.duration.total_seconds()
        total_seconds += self.start_time.hour * (60 * 60)
        total_seconds += self.start_time.second * 60
        hour = int(total_seconds // (60 * 60))
        minute = int((total_seconds % (60 * 60)) // 60)
        return time(hour=hour, minute=minute)

    def start_time_d(self) -> timedelta:
        if self.start_time is None:
            return timedelta()
        total_seconds = self.start_time.hour * (60 * 60)
        total_seconds += self.start_time.second * 60
        return timedelta(seconds=total_seconds)


class EditRequestBundle(models.Model):
    verbose_name = "Edit Meeting Bundle"
    edit_sections: QuerySet["EditSectionRequest"]
    request_message: "EditMeetingMessageBundleRequest"

    def realize(self):
        for edit_section in self.edit_sections.all():
            edit_section.realize()


class EditSectionRequest(models.Model):
    verbose_name = "Edit Section"

    section = models.ForeignKey(
        Section, related_name="edit_sections", on_delete=models.CASCADE
    )
    bundle = models.ForeignKey(
        EditRequestBundle, related_name="edit_sections", on_delete=models.CASCADE
    )
    edit_meetings: QuerySet["EditMeetingRequest"]

    def realize(self):
        for edit_meeting in self.edit_meetings.all():
            edit_meeting.realize()

    def meetings_sorted(self) -> QuerySet["EditMeetingRequest"]:
        return self.edit_meetings.order_by(
            models.Case(
                models.When(day=Day.MONDAY, then=1),
                models.When(day=Day.TUESDAY, then=2),
                models.When(day=Day.WEDNESDAY, then=3),
                models.When(day=Day.THURSDAY, then=4),
                models.When(day=Day.FRIDAY, then=5),
                models.When(day=Day.SATURDAY, then=6),
                models.When(day=Day.SUNDAY, then=7),
            ),
        )

    def data_edit_meetings(self) -> list[EditMeeting]:
        edit_meetings: list[EditMeeting] = []
        for i, edit_meeting_request in enumerate(self.meetings_sorted().all(), start=1):
            edit_meeting = edit_meeting_request.reformat(i)
            edit_meetings.append(edit_meeting)
        return edit_meetings


class EditMeetingRequest(models.Model):
    verbose_name = "Edit Meeting"

    start_time = models.TimeField()
    duration = models.DurationField()
    day = models.CharField(max_length=2, choices=Day.DAY_CHOICES)
    is_deleted = models.BooleanField()

    building = models.ForeignKey(
        Building,
        related_name="edit_requests",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    # If the room is None then the new meeting can be any room in the building
    room = models.ForeignKey(
        Room,
        related_name="edit_requests",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    professor = models.ForeignKey(
        Professor,
        related_name="edit_requests_involving",
        blank=True,
        null=True,
        default=None,
        on_delete=models.CASCADE,
    )
    # If there is no original then it is a created meeting
    original = models.ForeignKey(
        Meeting,
        related_name="edit_meetings",
        blank=True,
        null=True,
        default=None,
        on_delete=models.CASCADE,
    )

    edit_section = models.ForeignKey(
        EditSectionRequest, related_name="edit_meetings", on_delete=models.CASCADE
    )

    def is_changed(self) -> bool:
        if self.original is None:
            return True
        old_time_block = self.original.time_block
        old_start_time = old_time_block.start_end_time.start if old_time_block else None
        old_duration = self.original.get_duration()
        old_day = old_time_block.day if old_time_block else None
        old_new = [
            (
                old_start_time,
                self.start_time,
            ),
            (
                old_duration,
                self.duration,
            ),
            (
                old_day,
                self.day,
            ),
            (
                self.original.room,
                self.room,
            ),
            (
                self.original.professor,
                self.professor,
            ),
        ]

        return any(map(lambda old_new: old_new[0] != old_new[1], old_new))

    def reformat(self, counter: int) -> EditMeeting:
        return EditMeeting(
            start_time=self.start_time,
            duration=self.duration,
            day=self.day,
            building=self.building,
            room=self.room,
            meeting=self.original,
            section=self.edit_section.section,
            counter=counter,
            professor=self.professor,
            is_deleted=self.is_deleted,
        )

    def get_end_time(self) -> time:
        if self.start_time is None:
            return time()
        total_seconds = self.duration.total_seconds()
        total_seconds += self.start_time.hour * (60 * 60)
        total_seconds += self.start_time.second * 60
        hour = int(total_seconds // (60 * 60))
        minute = int((total_seconds % (60 * 60)) // 60)
        return time(hour=hour, minute=minute)

    def realize(self) -> None:
        start_end_time, _ = StartEndTime.objects.get_or_create(
            start=self.start_time,
            end=self.get_end_time(),
        )
        time_block, _ = TimeBlock.objects.get_or_create(
            start_end_time=start_end_time, day=self.day
        )

        if self.original:
            if self.is_deleted:
                self.original.delete()
            else:
                self.original.room = self.room
                self.original.professor = self.professor
                self.original.time_block = time_block
                self.original.save()
            return

        meeting = Meeting(
            room=self.room,
            professor=self.professor,
            time_block=time_block,
            section=self.edit_section.section,
        )
        meeting.save()


class EditMeetingMessageBundleRequest(models.Model):
    verbose_name = "Update meeting message bundle"

    date_sent = models.DateTimeField(auto_now_add=True, blank=True)
    message = models.CharField(max_length=300, blank=True, null=True, default=None)

    response: "EditMeetingMessageBundleResponse"
    requester = models.ForeignKey(
        Professor, related_name="requested_bundles", on_delete=models.CASCADE
    )
    request: EditRequestBundle = models.OneToOneField(
        EditRequestBundle, related_name="request_message", on_delete=models.CASCADE
    )  # pyright: ignore


class EditMeetingMessageBundleResponse(models.Model):
    ACCEPTED = "accepted"
    REVISED_ACCEPTED = "revised_accepted"
    DENIED = "denied"
    choices = [
        (ACCEPTED, "Accepted"),
        (REVISED_ACCEPTED, "Revised and Accepted"),
        (DENIED, "Denied"),
    ]

    date_sent = models.DateTimeField(auto_now_add=True, blank=True)
    is_read = models.BooleanField(default=False, blank=True)
    status = models.CharField(max_length=20, choices=choices)
    message = models.CharField(max_length=300, blank=True, null=True, default=None)

    sender = models.ForeignKey(
        Professor, related_name="authorized_bundles", on_delete=models.CASCADE
    )
    request_bundle: EditRequestBundle = models.OneToOneField(
        EditRequestBundle, related_name="response", on_delete=models.CASCADE
    )  # pyright: ignore
    request: EditMeetingMessageBundleRequest = models.OneToOneField(
        EditMeetingMessageBundleRequest,
        related_name="response",
        on_delete=models.CASCADE,
    )  # pyright: ignore


class ConflictingCourseGroup(models.Model):
    """Unidirectional mapping between a selected course to a dependant one"""

    selected_course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="selected_course_groups"
    )
    dependant_course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="dependant_course_groups"
    )

    class Meta:  # pyright: ignore
        unique_together = ("selected_course", "dependant_course")

    @staticmethod
    def create_bidirectional_group(course1: Course, course2: Course):
        course_group1 = ConflictingCourseGroup(course1, course2)
        course_group1.save()
        course_group2 = ConflictingCourseGroup(course2, course1)
        course_group2.save()

    @staticmethod
    def delete_bidirectional_group(course1: Course, course2: Course):
        first_direction = Q(selected_course=course1, dependant_course=course2)
        second_direction = Q(selected_course=course1, dependant_course=course2)
        course_groups = ConflictingCourseGroup.objects.filter(
            first_direction | second_direction
        )
        course_groups.delete()
