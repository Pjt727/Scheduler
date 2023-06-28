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


function groupSectionsAdd(sortColumn=null, sortType=null){
    console.log(sortColumn);
    console.log(sortType);
    const lastTimeBlock = lastClick;
    let group;
    if(lastTimeBlock === null){
        group = null;
    } else {
        group = lastTimeBlock.getAttribute('value');
    }
    const termSelect = document.getElementById("id_term");
    const selectedTerm = termSelect.options[termSelect.selectedIndex].value

    const departmentSelect = document.getElementById("id_department");
    const selectedDepartment = departmentSelect.options[departmentSelect.selectedIndex].value

    const url = new URL('dep_allo_sections/', window.location.origin);
    url.searchParams.set('term', selectedTerm);
    url.searchParams.set('department', selectedDepartment);
    url.searchParams.set('allocation_group', group);
    url.searchParams.set('sort_column', sortColumn);
    url.searchParams.set('sort_type', sortType);
    url.searchParams.set('start_slice', startSlice);
    url.searchParams.set('end_slice', endSlice);

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
            addSortListeners(groupSectionsAdd);
            addPaginationListeners(groupSectionsAdd);
            addMeetingPopovers();
        })
}


let lastClick = null;
function groupClick() {
    const departmentAllocations = document.getElementById("department_allocations");
    const timeBlocks = departmentAllocations.querySelectorAll(".time_block");

    timeBlocks.forEach((timeBlock) =>{
        timeBlock.addEventListener('click', ()=> {

            if (lastClick != null){
                unHighlightGroup(lastClick.getAttribute("value"), "table-dark");
                if(lastClick.getAttribute("value")===timeBlock.getAttribute("value")){
                    lastClick = null;
                    startSlice = 0;
                    endSlice = startSlice + jumpSlice;
                    groupSectionsAdd();
                    return;
                }
            }

            startSlice = 0;
            endSlice = startSlice + jumpSlice;
            lastClick = timeBlock;

            groupSectionsAdd();
            highlightGroup(timeBlock.getAttribute("value"), "table-dark");
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
            groupSectionsAdd();
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