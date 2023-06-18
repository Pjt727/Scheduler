function groupHover(){
    const departmentAllocations = document.getElementById("department_allocations");
    const timeBlocks = departmentAllocations.querySelectorAll(".time_block");
    timeBlocks.forEach((timeBlock) =>{
        timeBlock.addEventListener('mouseenter', ()=> highlightGroup(timeBlock.getAttribute("value"), "table-secondary"));
        timeBlock.addEventListener('mouseleave', ()=> unHighlightGroup(timeBlock.getAttribute("value"), "table-secondary"));
    });
}

function highlightGroup(group, className){
    const departmentAllocations = document.getElementById("department_allocations");
    const groupTimeBlocks = departmentAllocations.querySelectorAll(`.time_block[value="${group}"]`);
    groupTimeBlocks.forEach((timeBlock) => { timeBlock.classList.add(className) })
}

function unHighlightGroup(group, className){
    const departmentAllocations = document.getElementById("department_allocations");
    const groupTimeBlocks = departmentAllocations.querySelectorAll(`.time_block[value="${group}"]`);
    groupTimeBlocks.forEach((timeBlock) => { timeBlock.classList.remove(className) })
}

function groupSectionsAdd(group){
    const termSelect = document.getElementById("id_term");
    const selectedTerm = termSelect.options[termSelect.selectedIndex].value

    const departmentSelect = document.getElementById("id_department");
    const selectedDepartment = departmentSelect.options[departmentSelect.selectedIndex].value

    const url = new URL('dep_allo_sections/', window.location.origin);
    url.searchParams.set('term', selectedTerm);
    url.searchParams.set('department', selectedDepartment);
    url.searchParams.set('allocation_group', group);

    fetch(url, {
        method: 'get',
        headers: {'Content-Type': 'application/json',}
    })
        .then(response => response.json())
        .then(data =>{
            if(!data['ok']){
                console.error(data['error']);
                return;
            }
            const sectionsContainer = document.getElementById("sections_container");
            sectionsContainer.innerHTML = data['sections_html'];
        })
}

function groupClick() {
    const departmentAllocations = document.getElementById("department_allocations");
    const timeBlocks = departmentAllocations.querySelectorAll(".time_block");

    let lastClick = null;
    timeBlocks.forEach((timeBlock) =>{
        timeBlock.addEventListener('click', ()=> {
            if (lastClick != null){
                unHighlightGroup(lastClick.getAttribute("value"), "table-dark");
            }
            if(lastClick==timeBlock){
                lastClick = null;
                const sectionsContainer = document.getElementById("sections_container");
                sectionsContainer.innerHTML = '';
                return;
            }
            
            groupSectionsAdd(timeBlock.getAttribute("value"));
            highlightGroup(timeBlock.getAttribute("value"), "table-dark");
            lastClick = timeBlock;
        });
    });

}

function addGroupListeners(){
    groupClick();
    groupHover();
}

function getDepartmentAllo(){
    const termSelect = document.getElementById("id_term");
    const selectedTerm = termSelect.options[termSelect.selectedIndex].value

    const departmentSelect = document.getElementById("id_department");
    const selectedDepartment = departmentSelect.options[departmentSelect.selectedIndex].value

    const url = new URL('dep_allo/', window.location.origin);
    url.searchParams.set('term', selectedTerm);
    url.searchParams.set('department', selectedDepartment);

    fetch(url, {
        method: 'get',
        headers: {'Content-Type': 'application/json',}
    })
        .then(response => response.json())
        .then(data =>{
            if(!data['ok']){
                console.error(data['error']);
                return;
            }
            const alloContainer = document.getElementById("dep_allo_container");
            alloContainer.innerHTML = data['dep_allo_html'];
            const sectionsContainer = document.getElementById("sections_container");
            sectionsContainer.innerHTML = '';
            addGroupListeners();
        })
}

document.addEventListener('DOMContentLoaded', () => {
    getDepartmentAllo();
    const termSelect = document.getElementById("id_term");
    const departmentSelect = document.getElementById("id_department");
    termSelect.addEventListener('change', getDepartmentAllo);
    departmentSelect.addEventListener('change', getDepartmentAllo);
});