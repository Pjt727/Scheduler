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
    console.log(roomSelect)
    const room = roomSelect.value;
    console.log(room)


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

            const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
            popoverTriggerList.forEach((popoverTriggerEl) => {
                new bootstrap.Popover(popoverTriggerEl);
            });
        })
}



document.addEventListener('DOMContentLoaded', () => {
    const meetingRows = document.getElementsByClassName('meetingRow');
    Array.from(meetingRows).forEach(meetingRow => {
        const buildingSelect = meetingRow.querySelector('[name="building"]');
        buildingSelect.addEventListener('change', ()=>{
            buildingChange(meetingRow)
        });
        meetingRow.addEventListener('click', ()=>{
            updateMeetings(meetingRow)
        });
    });
});