function timeInputToSeconds(timeInput){
    const [hours, minutes]= timeInput.split(',')
    return parseInt(hours)*60*60 + parseInt(minutes)*60
}

function getMeetingPosition(time_start, time_end, day){
    const timeIntervals = [
        28800,
        32400,
        33300,
        38700,
        39600,
        44100,
        44700,
        51300,
        50400,
        54900,
        55800,
        62100,
        61200,
        65700,
        66600,
        71700,
        72000,
        75600,
        79200
    ];

    const timeIntervalsToRow = {
        28800: 2,
        32400: 3,
        33300: 3,
        38700: 4,
        39600: 4,
        44100: 5,
        44700: 5,
        51300: 6,
        50400: 6,
        54900: 7,
        55800: 7,
        62100: 8,
        61200: 8,
        65700: 9,
        66600: 9,
        71700: 10,
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

    const seconds_start = timeInputToSeconds(time_start)
    const seconds_end = timeInputToSeconds(time_end)

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
    const span = round((seconds_end - seconds_start) / 4500)

    return {"row": row, "col": col, "span": span}
}

function addMeetingToTable(time_start, time_end, day, text, calendarType){

    const {row, col, span} = getMeetingPosition(time_start, time_end, day)
    const meeting = document.createElement('div');
    meeting.classList.add('event', calendarType);
    meeting.style.gridColumn = col;
    meeting.style.gridRow = `${row}/span ${span}`;

    meeting.innerText = text;

    const editContainer = document.getElementById('editContainer');
    editContainer.appendChild(meeting);
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
        });
}


function updateMeetings(inputRow){
    const section = document.getElementById('section').getAttribute('value');
    const roomSelect = inputRow.querySelector('[name="room"]');
    const room = roomSelect.value;


    const url = new URL('get_meetings_edit_section/', window.location.origin);
    url.searchParams.set('section', section);
    url.searchParams.set('room', room);
    
    fetch(url, {
        method: 'get',
        headers: {
            'Content-Type': 'application/json',
        }
    })
        .then(response => response.json())
        .then(data => {
            const meetingsTemplate = data['get_meetings_template'];
            const meetingsContainer = document.getElementById('meetingContainer');
            meetingsContainer.innerHTML = meetingsTemplate;
            
            lastMeeting = null;
            const meetingDetailButtons = document.getElementsByName('meetingDetail');
            meetingDetailButtons.forEach(button => {
                button.addEventListener('click', () => meetingDetails(button.getAttribute('value'))); 
            })

        })
}

function submitInputRow(inputRow){

    console.log(inputRow)
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
        errorMessage(`Invalid start and end time. The end time cannot be prior to the start time.`)
        return false;
    }

    const displayRow = document.querySelector(`[inputRow=${inputRow.id}]`);
    
    const sameStartTime = displayRow.getAttribute('startTime') === newStartTime;
    const sameEndTime = displayRow.getAttribute('endTime') === newEndTime;
    const sameDay = displayRow.getAttribute('day') === newDay;
    const sameRoom = displayRow.getAttribute('room') === newRoom;
    const sameBuilding = displayRow.querySelector('[name="place"]').getAttribute('buildingValue') === buildingSelect.value;
    if(sameStartTime && sameEndTime && sameDay && sameRoom && sameBuilding){
        return false;
    }

    const addedMeetings = document.getElementsByClassName('addedMeetings');
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
            errorMessage(`The meeting overlaps with ${meeting}, and they both use ${buildingVerbose} ${roomVerbose}.`);
            return false;
        }
        errorMessage(`The meeting overlaps with ${meeting} and the same professor teaches both.`);
        return false;
    }
    
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
function addEditSubmitListeners(){
    const meetingDisplayRows = document.getElementsByClassName('displayRow');
    const meetingInputRows = document.getElementsByClassName('inputRow');

    Array.from(meetingDisplayRows).forEach(meetingRow => {
        const onActivate = (meetingRow) => {
            const inputRowId = meetingRow.getAttribute('inputRow');
            const inputRow = document.getElementById(inputRowId);

            // show all display rows
            Array.from(meetingDisplayRows).forEach(row =>{
                if(row.hidden===true){
                    row.hidden = false;
                } 
            });

            // hide all input rows and submit if the input row was shown
            Array.from(meetingInputRows).forEach(row =>{
                if(row.hidden===false){

                    submitInputRow(row);
                    row.hidden = true;
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

    Array.from(meetingInputRows).forEach(meetingRow => {
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
            const displayRow = document.querySelector(`[inputRow=${meetingRow.id}]`);
            submitInputRow(meetingRow);
            displayRow.hidden = false;
            meetingRow.hidden = true;

            const meetingsContainer = document.getElementById('meetingContainer');
            meetingsContainer.innerHTML = '';
        });
    });
}

document.addEventListener('DOMContentLoaded', () => {
    addEditSubmitListeners();
});