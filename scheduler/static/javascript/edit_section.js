function timeInputToSeconds(timeInput){
    const [hours, minutes]= timeInput.split(':')
    const seconds = parseInt(hours)*60*60 + parseInt(minutes)*60;
    return seconds;
}

function getMeetingPosition(startTime, endTime, day){
    const timeIntervals = [
        28800,
        32400,
        33300,
        38700,
        39600,
        44100,
        45000,
        49500,
        50400,
        54900,
        55800,
        60300,
        61200,
        65700,
        66600,
        71100,
        72000,
        75600,
        79200,
    ];

    const timeIntervalsToRow = {
        28800: 2,
        32400: 3,
        33300: 3,
        38700: 4,
        39600: 4,
        44100: 5,
        45000: 5,
        49500: 6,
        50400: 6,
        54900: 7,
        55800: 7,
        60300: 8,
        61200: 8,
        65700: 9,
        66600: 9,
        71100: 10,
        72000: 10,
        75600: 11,
        79200: 12
    };

    const dayCodesToCol = {
        'MO': 3,
        'TU': 4,
        'WE': 5,
        'TH': 6,
        'FR': 7,
        'SA': 8,
        'SU': 9,
    };

    const seconds_start = timeInputToSeconds(startTime)
    const seconds_end = timeInputToSeconds(endTime)

    let minTimeInterval;
    let minDifference = Infinity;
    for (const interval of timeIntervals) {
        const difference = Math.abs(seconds_start-interval);
        if(difference < minDifference){
            minTimeInterval = interval;
            minDifference = difference
        }
    }

    const row = timeIntervalsToRow[minTimeInterval];
    const col = dayCodesToCol[day];
    const span = Math.round((seconds_end - seconds_start) / 4500)

    return {"row": row, "col": col, "span": span}
}

function addMeetingToTable(startTime, endTime, day, text, sectionPk, counter, classCounter, isSelected=true, isHidden=false, doScale=false){

    const {row, col, span} = getMeetingPosition(startTime, endTime, day)
    const meeting = document.createElement('div');

    // calendar 9 - 17 are bordered css classes
    const calendarClass = `calendar${(classCounter  % 8) + 9}`

    if(isSelected){
        meeting.classList.add('event', calendarClass,  'selectedCalendar');
        meeting.setAttribute('id', `selected${sectionPk}${counter}`)
        meeting.style.userSelect = 'none';
        if(isHidden){
            meeting.style.display = 'none';
        }
    } else{
        meeting.classList.add('event', 'hoverCalendar', calendarClass);
        meeting.setAttribute('id', `hover${sectionPk}${counter}`)
        meeting.addEventListener('mouseout', leaveMeeting)
        meeting.addEventListener('click', clickMeeting)
        meeting.style.display = 'none';
        meeting.style.userSelect = 'none';
        meeting.style.cursor = 'pointer';
    }
    if(doScale){
        meeting.style.transform = "scale(1.2)"
    }

    

    meeting.style.gridColumn = col;
    meeting.style.gridRow = `${row}/span ${span}`;

    meeting.innerText = text;

    const editContainer = document.getElementById('meetingsGrid');
    editContainer.appendChild(meeting);

}

function addInputRow(inputRow, sectionPk, sectionCounter){
    const newStartTime = inputRow.querySelector('[name="startTime"]').value;
    const newEndTime = inputRow.querySelector('[name="endTime"]').value;
    const newDay = inputRow.querySelector('[name="day"]').value;
    const counter = inputRow.getAttribute('counter');

    const {isValid} = checkInputRow(inputRow);

    if(isValid){
        addMeetingToTable(
            newStartTime,
            newEndTime,
            newDay,
            `Meeting ${counter} (Editing)`,
            sectionPk,
            counter,
            sectionCounter,
            true,
            false,
            true,
        )
    } else {
        addMeetingToTable(
            newStartTime,
            newEndTime,
            newDay,
            `Meeting ${counter} (Editing)`,
            sectionPk,
            counter,
            sectionCounter,
            true,
            true,
            true,
        )
    }
    // hover
    addMeetingToTable(
        newStartTime,
        newEndTime,
        newDay,
        null,
        sectionPk,
        counter,
        sectionCounter,
        false,
        true,
        true
    )
}

function addDisplayRow(displayRow, sectionPk, sectionCounter, titleForNonEditing=null){
    const startTime = displayRow.getAttribute('startTime');
    const endTime = displayRow.getAttribute('endTime');
    const day = displayRow.getAttribute('day')
    const counter = displayRow.getAttribute('counter')
    let text;
    if(titleForNonEditing === null){
        text = `Meeting ${counter}`
    } else {
        text = titleForNonEditing;
    }
    addMeetingToTable(
        startTime, 
        endTime, 
        day,
        text,
        sectionPk,
        counter,
        sectionCounter,
    )
}

function openTimeSlotEnter(e){
    const openTimeBlock = e.target;

    const startTime = openTimeBlock.getAttribute('startTime');
    const endTime = openTimeBlock.getAttribute('endTime');
    const day = openTimeBlock.getAttribute('day');

    const inputRows = document.getElementsByClassName('inputRow');
    let inputRow;
    let counter
    for(const row of inputRows){
        if(!row.hidden){
            inputRow = row;
            counter = row.getAttribute('counter')
        }
    }

    const sectionGroup = document.querySelector(
        `[name="section"][value="${inputRow.getAttribute('section')}"]`
    );

    const sectionPk = sectionGroup.getAttribute('value');

    const meeting = document.getElementById(`hover${sectionPk}${counter}`)
    meeting.setAttribute('startTime', startTime);
    meeting.setAttribute('endTime', endTime);
    meeting.setAttribute('day', day);

    meeting.style.display = 'block';
    const {row, col, span} = getMeetingPosition(startTime, endTime, day);
    meeting.style.gridColumn = col;
    meeting.style.gridRow = `${row}/span ${span}`;
}

function leaveMeeting(e){
    e.target.style.display = 'none';
}

function clickMeeting(e){
    const meetingHover = e.target;
    const startTime = meetingHover.getAttribute('startTime');
    const endTime = meetingHover.getAttribute('endTime');
    const day = meetingHover.getAttribute('day');

    const inputRows = document.getElementsByClassName('inputRow');
    let counter
    let inputRow
    for(const inputRowItem of inputRows){
        if(!inputRowItem.hidden){
            inputRow = inputRowItem;
            counter = inputRowItem.getAttribute('counter');
        }
    }

    inputRow.querySelector('[name="startTime"]').value = startTime;
    inputRow.querySelector('[name="endTime"]').value = endTime;
    inputRow.querySelector('[name="day"]').value = day;

    const sectionGroup = document.querySelector(
        `[name="section"][value="${inputRow.getAttribute('section')}"]`
    );

    const sectionPk = sectionGroup.getAttribute('value');

    const meetingSelect = document.getElementById(`selected${sectionPk}${counter}`);
    const {col, row, span} = getMeetingPosition(startTime, endTime, day);

    meetingSelect.style.gridColumn = col;
    meetingSelect.style.gridRow = `${row}/span ${span}`;
    meetingSelect.style.display = 'block'

    meetingHover.style.display ='none';
}

function addOpenTimeSlotListeners(){
    const openSlots = document.getElementsByClassName('openSlots');
    for(const openSlot of openSlots){
        openSlot.addEventListener('mouseenter', openTimeSlotEnter);
    }
}

function buildingChange(inputRow){
    const building = inputRow.querySelector('[name="building"]').value;
    const roomSelect = inputRow.querySelector('[name="room"]');
    const roomOptions = inputRow.querySelector('[name="roomOptions"]');

    if(building === "any"){
        roomSelect.value = "any";
        roomOptions.innerHTML = "";
        return;
    }

    const url = new URL('get_rooms_edit_section', window.location.origin);
    url.searchParams.set('building', building);
    
    fetch(url, {
        method: 'get',
        headers: {
            'Content-Type': 'application/json',
        }
    })
        .then(response => response.json())
        .then(data => {
            const rooms = data['rooms'];
            roomOptions.innerHTML = "";
            for (const [roomPk, roomNumber] of rooms){
                const roomOption = document.createElement('option');
                roomOption.value = roomPk;
                roomOption.text = roomNumber;
                roomOptions.appendChild(roomOption);
            }

            updateMeetings(inputRow);
        });
}

let meetings_are_loading = false;
function updateMeetings(inputRow = null){
    if(meetings_are_loading){return;}

    const url = new URL('get_meetings_edit_section/', window.location.origin);

    const sections = [];
    
    const section_sections = document.getElementsByName('section');
    section_sections.forEach((sec) => {
        sections.push(sec.getAttribute('value'))
    });

    url.searchParams.set('sections', sections);
    if (!(inputRow === null)) {
        const primarySection = inputRow.getAttribute('section');
        const roomSelect = inputRow.querySelector('[name="room"]');
        const room = roomSelect.value;
        const building = inputRow.querySelector('[name="building"]').value;

        const startTime = inputRow.querySelector('[name="startTime"]').value;
        const endTime = inputRow.querySelector('[name="endTime"]').value;
        const totalSeconds = timeInputToSeconds(endTime) - timeInputToSeconds(startTime);
        const enforceDepartmentConstraints = document.getElementById('enforceDepartmentConstraints').checked;

        url.searchParams.set('primary_section', primarySection);
        url.searchParams.set('building', building);
        url.searchParams.set('room', room);
        url.searchParams.set('total_seconds', totalSeconds);
        url.searchParams.set('enforce_department_constraints', enforceDepartmentConstraints);
        url.searchParams.set('is_input', true);
    } else {
        url.searchParams.set('is_input', false);
    }

    meetings_are_loading = true
    
    fetch(url, {
        method: 'get',
        headers: {
            'Content-Type': 'application/json',
        }
    })
        .then(response => response.json())
        .then(data => {
            if(!data['ok']){
                console.error(data['error']);
            }
            const meetingsTemplate = data['get_meetings_template'];
            const meetingsContainer = document.getElementById('meetingContainer');
            meetingsContainer.innerHTML = meetingsTemplate;
            
            lastMeeting = null; // for collapse
            const meetingDetailButtons = document.getElementsByName('meetingDetail');
            meetingDetailButtons.forEach(button => {
                button.addEventListener('click', () => meetingDetails(button.getAttribute('value'), true)); 
            })

            let counterCheck = null;
            let currentSection = null;
            if(inputRow){
                counterCheck = inputRow.getAttribute('counter');
                currentSection = inputRow.getAttribute('section')
            } 

            const sectionGroups = document.querySelectorAll(`[name="section"]`);
            
            
            for(let i=0; i < sectionGroups.length; i++){
                const section = sectionGroups[i];

                const displayRows = section.querySelectorAll('.displayRow');
                const sectionPk = section.getAttribute("value");
                for( const displayRow of displayRows){
                    const counter = displayRow.getAttribute('counter');
                    if(((counter === counterCheck)
                        && (sectionPk === currentSection))){
                        addInputRow(inputRow, sectionPk, i)
                    } else if(sectionPk === currentSection){
                        addDisplayRow(displayRow, sectionPk, i);
                    } else {
                        const title = section.querySelector('[name="title"]');
                        addDisplayRow(displayRow, sectionPk, i, `${counter}: ${title.innerHTML.trim()}`);
                    }
                }
            };

            addOpenTimeSlotListeners();

            meetings_are_loading = false;
        })
}

function checkInputRow(inputRow){
    const newStartTime = inputRow.querySelector('[name="startTime"]').value;
    const newEndTime = inputRow.querySelector('[name="endTime"]').value;
    const newDay = inputRow.querySelector('[name="day"]').value;

    const buildingSelect = inputRow.querySelector('[name="building"]');
    const buildingVerbose = buildingSelect.options[buildingSelect.selectedIndex].innerText.trim();

    const roomSelect = inputRow.querySelector('[name="room"]');
    const newRoom = roomSelect.value;
    const roomVerbose = roomSelect.options[roomSelect.selectedIndex].innerText.trim();

    const newStartTimeSeconds = timeInputToSeconds(newStartTime);
    const newEndTimeSeconds = timeInputToSeconds(newEndTime);

    if(newEndTimeSeconds <= newStartTimeSeconds){
        const errorMessage = `Invalid start and end time. The end time cannot be prior to the start time.`;
        return {'isValid': false, 'reason': errorMessage };
    }

    const section = document.querySelector(`[name="section"][value="${inputRow.getAttribute("section")}"]`);

    const displayRow = section.querySelector(`.displayRow[counter="${inputRow.getAttribute("counter")}"]`)
    
    const sameStartTime = displayRow.getAttribute('startTime') === newStartTime;
    const sameEndTime = displayRow.getAttribute('endTime') === newEndTime;
    const sameDay = displayRow.getAttribute('day') === newDay;
    const sameRoom = displayRow.getAttribute('room') === newRoom;
    const sameBuilding = displayRow.querySelector('[name="place"]').getAttribute('buildingValue') === buildingSelect.value;
    if(sameStartTime && sameEndTime && sameDay && sameRoom && sameBuilding){
        return {'isValid': true, 'reason': 'same'};
    }

    const addedMeetings = document.getElementsByName('addedMeetings');
    for (const addedMeeting of addedMeetings){
        const startTime = addedMeeting.getAttribute('startTime');
        const startTimeSeconds = timeInputToSeconds(startTime);
        const endTime = addedMeeting.getAttribute('endTime');
        const endTimeSeconds = timeInputToSeconds(endTime);
        const day = addedMeeting.getAttribute('day');
        const room = addedMeeting.getAttribute('room');

        if(day != newDay){
            continue;
        }else if(!(newStartTimeSeconds  <= endTimeSeconds  && newEndTimeSeconds  >= startTimeSeconds)){
            continue;
        }

        const meeting = addedMeeting.getAttribute('meeting');
        if(newRoom == room){
            const errorMessage = `The meeting overlaps with ${meeting}, and they both use ${buildingVerbose} ${roomVerbose}.`;
            return {'isValid': false, 'reason': errorMessage};
        }
        const errorMessage = `The meeting overlaps with ${meeting} and the same professor teaches both.`;
        return {'isValid': false, 'reason': errorMessage};
    }

    return {'isValid': true, 'reason': 'new'}
}

function submitInputRow(inputRow){

    const {isValid, reason} = checkInputRow(inputRow);
    if(!isValid){
        errorMessage(reason);
        window.scroll(0,0)
        return false;
    } else if(reason === 'same'){
        return true;
    }

    const newStartTime = inputRow.querySelector('[name="startTime"]').value;
    const newEndTime = inputRow.querySelector('[name="endTime"]').value;
    const newDay = inputRow.querySelector('[name="day"]').value;

    const buildingSelect = inputRow.querySelector('[name="building"]');
    const buildingVerbose = buildingSelect.options[buildingSelect.selectedIndex].innerText.trim();

    const roomSelect = inputRow.querySelector('[name="room"]');
    const newRoom = roomSelect.value;
    const roomVerbose = roomSelect.options[roomSelect.selectedIndex].innerText.trim();

    const section = document.querySelector(`[name="section"][value="${inputRow.getAttribute("section")}"]`);

    const displayRow = section.querySelector(`.displayRow[counter="${inputRow.getAttribute("counter")}"]`)
    
    displayRow.setAttribute('startTime', newStartTime);
    displayRow.setAttribute('endTime', newEndTime);
    displayRow.setAttribute('day', newDay);
    displayRow.setAttribute('room', newRoom);
    displayRow.querySelector('[name="place"]').setAttribute('roomValue', roomSelect.value); 

    const startDate = new Date();
    const [startHours, startMinutes] = newStartTime.split(':');
    startDate.setHours(startHours);
    startDate.setMinutes(startMinutes);
    const formattedStartTime = startDate.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hours12: true});

    const endDate = new Date();
    const [endHours, endMinutes] = newEndTime.split(':');
    endDate.setHours(endHours);
    endDate.setMinutes(endMinutes);
    const formattedEndTime = endDate.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hours12: true});

    const timeBlock = displayRow.querySelector('[name="timeBlock"]');
    const place = displayRow.querySelector('[name="place"]');

    timeBlock.innerHTML = `${formattedStartTime} - ${formattedEndTime} &nbsp ${newDay}`;
    place.innerText = `${buildingVerbose} ${roomVerbose}`;
    return true;
}

function addEditSubmitListeners(sectionGroup){
    Array.from(sectionGroup.querySelectorAll('.displayRow')).forEach(meetingRow => {
        const onActivate = (meetingRow) => {
            const meetingDisplayRows = document.querySelectorAll('.displayRow');
            const meetingInputRows = document.querySelectorAll('.inputRow');
            const counter = meetingRow.getAttribute('counter');
            const inputRow = sectionGroup.querySelector(`.inputRow[counter="${counter}"]`);

            // hide all input rows and submit if the input row was shown
            console.log(meetingInputRows)
            for(const row of meetingInputRows){
                if(row.hidden===false){
                    const isValid = submitInputRow(row);
                    if(!isValid){
                        return;
                    }
                    row.hidden = true;
                }
            }
            console.log('spacing')

            // show all display rows
            Array.from(meetingDisplayRows).forEach(row =>{
                if(row.hidden===true){
                    row.hidden = false;
                } 
            });
            inputRow.hidden = false;
            meetingRow.hidden = true;
            updateMeetings(inputRow);
        }

        meetingRow.addEventListener('dblclick', () => onActivate(meetingRow));

        const editCol = meetingRow.querySelector('[name="editCol"]')
        editCol.addEventListener('click', () => onActivate(meetingRow));
    });

    Array.from(sectionGroup.querySelectorAll('.inputRow')).forEach(meetingRow => {
        const buildingSelect = meetingRow.querySelector('[name="building"]');
        buildingSelect.addEventListener('change', ()=>{
            buildingChange(meetingRow);
        });

        const roomSelect =  meetingRow.querySelector('[name="room"]');
        roomSelect.addEventListener('change', ()=>{
            updateMeetings(meetingRow);
        })

        const submitCol = meetingRow.querySelector('[name="submitCol"]');
        submitCol.addEventListener('click', ()=>{
            const counter = meetingRow.getAttribute('counter');
            const displayRow = sectionGroup.querySelector(`.displayRow[counter="${counter}"]`);
            const is_valid = submitInputRow(meetingRow);
            if (!is_valid){
                return;
            }
            displayRow.hidden = false;
            meetingRow.hidden = true;
            updateMeetings();
        });
    });

    const enforceDepartmentConstraints = document.getElementById('enforceDepartmentConstraints');
    enforceDepartmentConstraints.addEventListener('change', () => {
        const meetingInputRows = document.querySelectorAll('.inputRow');
        for(const meetingInputRow of meetingInputRows){
            if(!meetingInputRow.hidden){
                updateMeetings(meetingInputRow);
                return;
            }
        }
    })
}

function addSection(section){
    const sectionSections = document.getElementsByName('section');
    for(let i=0; i < sectionSections.length; i++){

        if (sectionSections[i].getAttribute('value') == section){
            errorMessage("You are already editing that section!")
            return;
        }
    }

    const url = new URL('get_edit_section/', window.location.origin);

    url.searchParams.set('section', section)

    fetch(url)
        .then(response => response.json())
        .then(data=> {
            const editSectionHtml = data['edit_section_html'];

            const newSection = document.createElement('section');
            newSection.setAttribute('name', 'section');
            newSection.setAttribute('value', section);
            newSection.innerHTML = editSectionHtml;

            const sections = document.getElementById('sections');
            sections.appendChild(newSection);
            addEditSubmitListeners(newSection);
            let inputRow = null;
            const inputRows = document.getElementsByClassName('inputRow');

            Array.from(inputRows).forEach( row => {
                if(!row.hidden){
                    inputRow = row;
                }
            });
            updateMeetings(inputRow);
        })
}

document.addEventListener('DOMContentLoaded', () => {
    const firstSectionGroup = document.querySelector('[name="section"]');
    addEditSubmitListeners(firstSectionGroup);
    updateMeetings();
});