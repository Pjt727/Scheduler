from django import template
from claim.models import Day
from django.utils import timezone
from datetime import timedelta, time, datetime

from request.models import EditMeeting

register = template.Library()

@register.filter
def get_list(dictionary, key):
    return dictionary.getlist(key)

@register.filter
def get_item(dictionary: dict, key):
    return dictionary.get(key)

@register.simple_tag
def grid_area(start_time: time, end_time: time, day: str) -> str:
    codes_to_col = {
        Day.MONDAY: 3,
        Day.TUESDAY: 4,
        Day.WEDNESDAY: 5,
        Day.THURSDAY: 6,
        Day.FRIDAY: 7,
        Day.SATURDAY: 8,
        Day.SUNDAY: 9,
    }
    times_to_col = {
        timedelta(hours=8): 2,
        timedelta(hours=9): 3,
        timedelta(hours=9, minutes=15): 3,
        timedelta(hours=10, minutes=45): 4,
        timedelta(hours=11): 4,
        timedelta(hours=12, minutes=15): 5,
        timedelta(hours=12, minutes=30): 5,
        timedelta(hours=13, minutes=45): 6,
        timedelta(hours=14): 6,
        timedelta(hours=15, minutes=15): 7,
        timedelta(hours=15, minutes=30): 7,
        timedelta(hours=16, minutes=45): 8,
        timedelta(hours=17): 8,
        timedelta(hours=18, minutes=15): 9,
        timedelta(hours=18, minutes=30): 9,
        timedelta(hours=19, minutes=45): 10,
        timedelta(hours=20): 10,
        timedelta(hours=21): 11,
        timedelta(hours=22): 12
    }

    grid_col_start = codes_to_col.get(day)
    if grid_col_start is None:
        grid_col_start = 3

    meeting_seconds = start_time.hour * 3600 + start_time.minute * 60
    closest_time_delta = min(times_to_col.keys(), key=lambda time: abs(meeting_seconds-time.total_seconds()))
    grid_row_start = times_to_col[closest_time_delta]

    meeting_seconds = end_time.hour * 3600 + end_time.minute * 60
    closest_time_delta = min(times_to_col.keys(), key=lambda time: abs(meeting_seconds-time.total_seconds()))
    grid_row_end = times_to_col[closest_time_delta]

    return f"{grid_row_start} / {grid_col_start} / {grid_row_end} / {grid_col_start}"

@register.filter
def modulo(num, val):
    return num % val

@register.filter
def subtract(num1: int, num2: int) -> int:
    return num1 - num2

@register.filter
def time_display(t: time) -> str:
    try:
        return t.strftime('%I:%M %p')
    except AttributeError:
        return ''

@register.filter
def time_input(t: time) -> str:
    try:
        return t.strftime('%H:%M')
    except AttributeError:
        return ''

@register.filter
def format_date(d: datetime):
    return timezone.localtime(d).strftime('%b. %d, %Y %I:%M %p')

@register.filter
def sort_edit_meetings(e_ms: list[EditMeeting]):
    compare_days = {
            Day.MONDAY: 1,
            Day.TUESDAY: 2,
            Day.WEDNESDAY: 3,
            Day.THURSDAY: 4,
            Day.FRIDAY: 5,
            Day.SATURDAY: 6,
            Day.SUNDAY: 7,
            None: 8
            }

    return sorted(e_ms, key=lambda e: compare_days.get(e.day, 8))
