# this is grouping between program school names
#   and the valid "department" names on banner which are really also the school
#  names
# there might still be some edge departments mappings to account for use this example jq command to
#    reason about them:
# cat data/banner/courses.json | jq 'group_by(.department) | map({department: .[0].department, count: length})'
SCHOOL_CODE_AND_VALID_DEPARTMENTS: list[tuple[str, list[str]]] = [
        
        ("CO", ["School Communication  Arts"]),
        ("CC", ["School Computer Sci/ Math"]),
        ("LA", ["School of Liberal Arts"]),
        ("SM", ["School of Management"]),
        ("SI", ["School of Science", "Science"]),
        ("SB", ["School Behavioral/Social Sci"]),
        ("PP", ["Professional Programs"]),
        ("MSCS", ["MSCS Computer Science"]),
        ]

SCHOOL_CODE_TO_SCHOOL: dict[str, str] = {
    "CO": "Communication and the Arts",
    "CC": "Computer Science and Mathematics",
    "LA": "Liberal Arts",
    "SM": "Management",
    "SI": "Science",
    "SB": "Social and Behavioral Sciences",
    "PP": "Professional Programs",
    "MSCS": "Masters Computer Science"
}
