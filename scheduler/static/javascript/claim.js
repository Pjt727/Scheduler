function deleteCourseSelect(event){
    event.target.parentNode.remove();
}

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

function addCourseSelect(course_rep){
    courseOption = getCourse(course_rep);
    if (courseOption === null){ return }

    // check to see if select element is already selected
    const courseSelectID = `multiSelect${courseOption.id}`
    const courseMultiSelect = document.getElementById("courseMultiSelect");
    if(!(courseMultiSelect.querySelector(`#${courseSelectID}`) === null)){ return };

    // creating select elements
    const courseSelect = document.createElement('span');
    courseSelect.classList.add('badge', 'text-bg-secondary', 'fs-5', 'm-2');
    courseSelect.textContent = course_rep;
    courseSelect.value = courseOption.id;
    courseSelect.id = courseSelectID

    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.classList.add('btn-close');
    closeButton.setAttribute('aria-label', 'Close');
    closeButton.addEventListener('click', deleteCourseSelect);
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
    const departmentSelectOptions = departmentSelect.querySelectorAll("option");

    const subjectSelect = document.getElementById("id_subject");
    const subjectSelectOptions = subjectSelect.querySelectorAll("option");

    const courseInput = document.getElementById("id_course-text");
    const courseDataList = document.getElementById("id_course-options")
    const courseDataListOptions = courseDataList.querySelectorAll("option");

    // when changed update subjects, and course selections
    departmentSelect.addEventListener('change', () => {
        const selectedDepartment = departmentSelect.options[departmentSelect.selectedIndex];
        const selectedDepartmentPk = selectedDepartment.value;
        subjectSelect.value = "any";
        if (selectedDepartmentPk === "any"){
            subjectSelectOptions.forEach((option) =>{option.hidden = false;})
            return;
        }
        hideOptions(subjectSelectOptions, "department", selectedDepartmentPk);
    });

    subjectSelect.addEventListener('change', ()=>{
        const selectedSubject = subjectSelect.options[subjectSelect.selectedIndex];
        const selectedSubjectPk = selectedSubject.value;

        const selectedDepartment = departmentSelect.options[departmentSelect.selectedIndex];
        const selectedDepartmentPk = selectedDepartment.value;

        departmentSelect.value = selectedSubject.getAttribute("department");

        if(selectedSubjectPk === "any"){
            return;
        }
        courseInput.value = `${selectedSubject.innerHTML}: `;
    });
}
document.addEventListener('DOMContentLoaded', ()=>{
    submitEnterListener();
    selectUpdates();
});