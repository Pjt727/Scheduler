let lastMeeting = null;

function meetingDetails(meeting){
    if(lastMeeting === meeting){
        return;
    }
    lastMeeting = meeting;
    const url = new URL('get_meeting_details/', window.location.origin);
    url.searchParams.set('meeting', meeting);

    
    fetch(url, {
        method: 'get',
        headers: {
            'Content-Type': 'application/json',
        }
    })
        .then(response => response.json())
        .then(data => {
            const meetingDetailsHtml = data['meeting_details_html'];
            const meetingDetailContainer = document.getElementById('meetingDetailsContainer');
            meetingDetailContainer.innerHTML = meetingDetailsHtml;
            const meetingsCollapse = new bootstrap.Collapse('#meetingDetails');
            meetingsCollapse.show();
            
        });

}