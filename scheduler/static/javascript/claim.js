function getCourse(course_rep){
    const courseDataList = document.getElementById("id_course-options");
    const courseOptions = courseDataList.querySelectorAll("option");
    let foundCourseOption = null;
    courseOptions.forEach( (courseOption) => {
        if(courseOption.value == course_rep){
            foundCourseOption = courseOption
        }
    });

    return foundCourseOption;
}

function addCourseSelect(course_selection){
    // check to see if select element is already selected
    const courseSelectID = `multiSelect${course_selection.id}`
    const courseMultiSelect = document.getElementById("courseMultiSelect");
    if(!(courseMultiSelect.querySelector(`#${courseSelectID}`) === null)){ return };

    // creating select elements
    const courseSelect = document.createElement('span');
    courseSelect.classList.add('badge', 'text-bg-light', 'fs-5', 'm-2');
    courseSelect.textContent = `${course_selection.getAttribute('subject')}: ${course_selection.getAttribute('code')}`;
    courseSelect.setAttribute('value',  course_selection.getAttribute('value'))
    courseSelect.id = courseSelectID

    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.classList.add('btn-close');
    closeButton.setAttribute('aria-label', 'Close');
    closeButton.addEventListener('click', (event) => {event.target.parentNode.remove();});
    courseSelect.appendChild(closeButton); 

    // append to container
    courseMultiSelect.appendChild(courseSelect);
}

function submitEnterListener(){
    const courseText = document.getElementById("id_course-text");
    courseText.addEventListener('keydown', (event)=>{
        if(event.key === 'Enter'){
            event.preventDefault();
            addCourseSelect(courseText.value);
        }
    });
}

function hideOptions(options, attribute, selectedValue){
    options.forEach((option)=> {
        if(option.value === "any"){return;}
        if(option.getAttribute(attribute) === selectedValue){
            option.hidden = false;
        } else {
            option.hidden = true;
        }
    })
}

function selectUpdates(){
    // Getting the selects and the options (removing any from options because that should always be visible)
    const departmentSelect = document.getElementById("id_department");

    const subjectSelect = document.getElementById("id_subject");
    const subjectSelectOptions = subjectSelect.querySelectorAll("option");

    // when changed update subjects, and course selections
    departmentSelect.addEventListener('change', () => {
        const selectedDepartment = departmentSelect.options[departmentSelect.selectedIndex];
        const selectedDepartmentPk = selectedDepartment.value;
        subjectSelect.value = "any";
        if (selectedDepartmentPk === "any"){
            subjectSelectOptions.forEach((option) =>{option.hidden = false;})
            updateCourseLiveSearch();
            return;
        }
        hideOptions(subjectSelectOptions, "department", selectedDepartmentPk);
        updateCourseLiveSearch();
    });

    subjectSelect.addEventListener('change', ()=>{
        const selectedSubject = subjectSelect.options[subjectSelect.selectedIndex];
        if(selectedSubject.value === "any"){
            departmentSelect.value = "any";
            updateCourseLiveSearch();
            return;
        }
        departmentSelect.value = selectedSubject.getAttribute("department");
        updateCourseLiveSearch();
    });
}

function addCourse(course){
    const courseOptions = document.getElementById('course-options');
    const courseOption = document.createElement('tr');
    courseOption.setAttribute('subject', course['subject']);
    courseOption.setAttribute('code', course['code'])
    courseOption.id = course['subject'] + course['code'];
    const title = document.createElement('td');
    const subject = document.createElement('td');
    courseOption.setAttribute('value', course['pk'])
    title.textContent = course['title'];
    subject.textContent = course['code'];

    courseOption.appendChild(title);
    courseOption.appendChild(subject);
    courseOptions.appendChild(courseOption);

    courseOption.addEventListener('click', () => addCourseSelect(courseOption))
}

let count = 10;
let bottom = false;
function updateCourseLiveSearch(){
    const departmentSelect = document.getElementById("id_department");
    const selectedDepartment = departmentSelect.options[departmentSelect.selectedIndex].value
    const subjectSelect = document.getElementById("id_subject");
    const selectedSubject = subjectSelect.options[subjectSelect.selectedIndex].value;

    const search = document.getElementById('id_course-text');
    const url = new URL('course_search/', window.location.origin);
    url.searchParams.set('department', selectedDepartment);
    url.searchParams.set('subject', selectedSubject);
    url.searchParams.set('search', search.textContent)
    url.searchParams.set('count', count)

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
                return; 
            }
            bottom = data['bottom']
            const table = document.getElementById('course-options');
            table.innerHTML = '';
            const courses = data['courses']
            if (courses.length === 0){
                const courseOptions = document.getElementById('course-options');
                const courseOption = document.createElement('tr');
                courseOption.innerText = "No courses match those criteria";
                courseOptions.appendChild(courseOption);
                return;
            }
            courses.forEach((course)=> addCourse(course));
        })
    
}

function handleCourseOptionScroll(){
    const scrollContainer = document.getElementById('search-container');
    const padding = 10;

    if(scrollContainer.scrollHeight - scrollContainer.scrollTop <= scrollContainer.clientHeight + padding){
        count += 5;
        if(!bottom){updateCourseLiveSearch();}
    }
}

let timeoutId;
function searchDebounce(){
    clearTimeout(timeoutId);
    count = 10
    timeoutId = setTimeout(() => {
        updateCourseLiveSearch();
        document.getElementById('search-container').scrollTop = 0;
    }, 200)

}


function updateSections(sortColumn=null, sortType=null) {
    const term = document.getElementById('id_term').options[document.getElementById('id_term').selectedIndex].getAttribute('value');
    const doesFit = document.getElementById('fits').checked;
    const isAvailable = document.getElementById('available').checked;
    const courses = [];

    const coursesSelect = document.getElementById('courseMultiSelect');
    const coursesSpan = coursesSelect.getElementsByTagName('span');
    Array.from(coursesSpan).forEach((span) => { courses.push(span.getAttribute('value')) });

    const preCoursesContainer = document.getElementById('previousCourses');
    const preCoursesCheck = preCoursesContainer.getElementsByTagName('input');
    Array.from(preCoursesCheck).forEach((check) => { if (check.checked) { courses.push(check.getAttribute('value')) } });

    if(courses.length === 0){
        errorMessage("Please select course(s) to search for meetings");
        return;
    }

    const exclusionTimes = [];
    const exclusionTimesContainer = document.getElementById('exclusionTimes');
    const exclusionTimesSpan = exclusionTimesContainer.getElementsByTagName('span');
    Array.from(exclusionTimesSpan).forEach((exclusionTime) => exclusionTimes.push({
        'day': exclusionTime.getAttribute('day'),
        'start_time': exclusionTime.getAttribute('start_time'),
        'end_time': exclusionTime.getAttribute('end_time'),
    }))

    const url = new URL('section_search/', window.location.origin);
    const payload = {
        term: term,
        does_fit: doesFit,
        is_available: isAvailable,
        courses: courses,
        exclusion_times: exclusionTimes,
        sort_column: sortColumn,
        sort_type: sortType,
        start_slice: startSlice,
        end_slice: endSlice
    };

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value
        },
        body: JSON.stringify(payload)
    })
        .then(response => response.json())
        .then(data => {
            if (!data['ok']) {
                console.error(data['error']);
                return;
            }
            const tableBody = document.getElementById('sections');
            tableBody.innerHTML = data['section_html']
            addSortListeners(updateSections);
            addPaginationListeners(updateSections);
            addMeetingPopovers();
        });
}


function addExclusionTime(){
    const startTime = document.getElementById("startTime").value;
    const endTime = document.getElementById("endTime").value;
    if (startTime == '' ||  endTime == ''){return}
    const startDate = new Date(`2000-01-01T${startTime}`);
    const endDate = new Date(`2000-01-01T${endTime}`);
    const timeFormat = {
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
    };
    // Check if the selected times are valid
    if (startDate >= endDate) {
      errorMessage("Start time must be less than end time.");
      return;
    }

    const daySelect = document.getElementById("day");
    const dayCode = daySelect.options[daySelect.selectedIndex].value;
    const dayVerbose = daySelect.options[daySelect.selectedIndex].textContent;

    // creating elements
    
    const column = document.createElement('div');
    column.classList.add('col-5')

    const exclusionTime = document.createElement('span');
    exclusionTime.classList.add('badge', 'text-bg-light', 'fs-5', 'm-2');
    exclusionTime.textContent = `${dayVerbose} ${startDate.toLocaleTimeString(undefined, timeFormat)} - ${endDate.toLocaleTimeString(undefined, timeFormat)}`;
    exclusionTime.setAttribute('start_time',  startTime);
    exclusionTime.setAttribute('end_time',  endTime);
    exclusionTime.setAttribute('day',  dayCode);
    column.appendChild(exclusionTime);

    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.classList.add('btn-close');
    closeButton.setAttribute('aria-label', 'Close');
    closeButton.addEventListener('click', (event) => {event.target.parentNode.parentNode.remove()});
    exclusionTime.appendChild(closeButton); 

    document.getElementById('exclusionTimes').appendChild(column);
}

function updateClaimModal(event){
    const claimModal = document.getElementById('submitClaim');

    // populating the title
    const button = event.relatedTarget;
    const title = button.getAttribute("data-bs-title");
    const subject = button.getAttribute("data-bs-subject");
    const course = button.getAttribute("data-bs-course");

    const modalTitle = claimModal.querySelector('.modal-title');
    modalTitle.textContent = `${title} ${subject} ${course}`;

    // creating the checkbox inputs
    const meetingsContainer = claimModal.querySelector("#claimMeetings");
    //emptying it
    meetingsContainer.innerHTML = "";

    const meetingsId = button.getAttribute("meetings");
    const meetingRows = document.getElementById(meetingsId).getElementsByTagName('tr');

    for(let i=0; i < meetingRows.length; i++){
        row = meetingRows[i];
        const meetingContainer = document.createElement('div');

        const meetingInput = document.createElement('input');
        meetingInput.id = `meeting${i}`;
        meetingInput.checked = true;
        meetingInput.value = row.getAttribute('value');
        meetingInput.setAttribute("type", "checkbox")

        const meetingLabel = document.createElement('label');
        meetingLabel.setAttribute("for", `meeting${i}`);
        meetingLabel.textContent = row.textContent;
        meetingContainer.appendChild(meetingInput);
        meetingContainer.appendChild(meetingLabel);

        meetingsContainer.appendChild(meetingContainer);
    }
}

function claimMeetings(){
    // get the meetings
    const meetingContainer = document.getElementById("claimMeetings");
    const meetingRows = meetingContainer.getElementsByTagName("input");

    const meetings = [];
    for(let i=0; i < meetingRows.length; i++){
        if(meetingRows[i].checked){meetings.push(meetingRows[i].value)}
    }

    payload = {meetings: meetings}
    const url = new URL('submit_claim/', window.location.origin);

    fetch(url,{
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrfmiddlewaretoken"]').value
        },
        body: JSON.stringify(payload)
    })
        .then(response => response.json())
        .then(data => {
            if (!data['ok']) {
                errorMessage(data['error']);
                return;
            }
            successMessage(data['success_message']);
        });
}


document.addEventListener('DOMContentLoaded', ()=>{
    submitEnterListener();
    selectUpdates();

    // live search
    document.getElementById('id_course-text').addEventListener('input', searchDebounce);
    document.getElementById('search-container').addEventListener('scroll', handleCourseOptionScroll);
    updateCourseLiveSearch();

    // section search
    document.getElementById('meetingSearch').addEventListener('click', () => updateSections());
    document.getElementById('excludeButton').addEventListener('click', addExclusionTime);

    // claim
    const claimModal = document.getElementById('submitClaim');
    claimModal.addEventListener('show.bs.modal', (event)=> updateClaimModal(event));
    document.getElementById('claimButton').addEventListener('click', claimMeetings);
});