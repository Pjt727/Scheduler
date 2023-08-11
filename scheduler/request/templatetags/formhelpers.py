from django import template
from claim.models import Meeting, Day, TimeBlock
from datetime import timedelta, time

register = template.Library()

@register.filter
def get_list(dictionary, key):
    return dictionary.getlist(key)

@register.filter
def get_item(dictionary: dict, key):
    return dictionary.get(key)

@register.filter
def get_time_block_col(time_block: TimeBlock) -> int:
    codes_to_col = {
        Day.MONDAY: 3,
        Day.TUESDAY: 4,
        Day.WEDNESDAY: 5,
        Day.THURSDAY: 6,
        Day.FRIDAY: 7,
        Day.SATURDAY: 8,
        Day.SUNDAY: 9,
    }

    return codes_to_col[time_block.day]

@register.filter
def get_time_block_row(time_block: TimeBlock) -> int:
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
    meeting_seconds = time_block.start_end_time.start.hour * 3600 + time_block.start_end_time.start.minute * 60
    closest_time_delta = min(times_to_col.keys(), key=lambda time: abs(meeting_seconds-time.total_seconds()))
    return times_to_col[closest_time_delta]

@register.filter
def get_time_block_span(time_block: TimeBlock) -> int:
    start_end_time= time_block.start_end_time
    start_seconds = start_end_time.start.hour * 3600 + start_end_time.start.minute * 60
    end_seconds = start_end_time.end.hour * 3600 + start_end_time.end.minute * 60

    spanning_time_blocks = round((end_seconds - start_seconds) / 4500) # 4500 seconds is 1:15
    return spanning_time_blocks

@register.filter
def modulo(num, val):
    return num % val

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
