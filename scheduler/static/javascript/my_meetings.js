function getMeetings(){
    const termSelect = document.getElementById("id_term");
    const selectedTerm = termSelect.options[termSelect.selectedIndex].value

    const url = new URL('get_meetings/', window.location.origin);
    url.searchParams.set('term', selectedTerm);

    fetch(url, {
        method: 'get',
        headers: {'Content-Type': 'application/json',}
    })
        .then(response => response.json())
        .then(data => {
            if(!data['ok']){
                console.error(data['error']);
                return;
            }

            const meetingsContainer = document.getElementById("meetings")
            meetingsContainer.innerHTML = data["get_meetings_template"]
            const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
                popoverTriggerList.forEach((popoverTriggerEl) => {
                new bootstrap.Popover(popoverTriggerEl);
            });

        })
}


document.addEventListener('DOMContentLoaded', () => {
    getMeetings();
    const termSelect = document.getElementById("id_term");
    termSelect.addEventListener('change', getMeetings);
});