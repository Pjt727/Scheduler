let startSlice = 0;
const jumpSlice = 10;
let endSlice = startSlice + jumpSlice;

function iterateSort(e){
    const options = ["noSort", "ascending", "descending"];
    const column = e.currentTarget;
    const sortOption = column.querySelector("svg").getAttribute("sort");
    const sortCurIndex = options.indexOf(sortOption);
    const sortNextIndex = (sortCurIndex + 1) % options.length;
    console.log(column.parentNode.id)
    return {"sortColumn": column.id, "sortType": options[sortNextIndex]};
}

function addSortListeners(callback) {
  const sortClicks = document.getElementsByClassName("sort");
  Array.from(sortClicks).forEach(sortClick => {
    sortClick.addEventListener('click', (e) => {
      const { sortColumn, sortType } = iterateSort(e);
      startSlice = 0;
      endSlice = jumpSlice + startSlice;
      callback(sortColumn, sortType);
    });
  });
}

function addMeetingPopovers(){
  const sectionsTable = document.getElementById("sectionsTable");
  const popoverTriggerList = sectionsTable.querySelectorAll('[data-bs-toggle="popover"');
  bootstrap.Tooltip.Default.allowList.table = [];
  bootstrap.Tooltip.Default.allowList.thead = [];
  bootstrap.Tooltip.Default.allowList.tbody = [];
  bootstrap.Tooltip.Default.allowList.tr = [];
  bootstrap.Tooltip.Default.allowList.td = [];

  popoverTriggerList.forEach((popoverTriggerEl) => {
    new bootstrap.Popover(popoverTriggerEl);
  });

} 

function addPaginationListeners(callback) {
  const prevClick = document.getElementById("prevSections");
  const nextClick = document.getElementById("nextSections");

  const sortClicks = document.getElementsByClassName("sort");
  let sortColumn = null;
  let sortType = null;
  Array.from(sortClicks).forEach(sortClick => {
    const sortOption = sortClick.querySelector("svg").getAttribute("sort");
    if(sortOption === "ascending" || sortOption === "descending"){
      sortColumn = sortClick.id;
      sortType = sortOption;
    }
  })

  if(!prevClick.disabled){
    prevClick.addEventListener('click', () =>{
      startSlice -= jumpSlice;
      endSlice -= jumpSlice;
      callback(sortColumn, sortType);
    });
  }

  if(!nextClick.disabled){
    nextClick.addEventListener('click', () =>{
      startSlice += jumpSlice;
      endSlice += jumpSlice;
      callback(sortColumn, sortType);
    });
  }
}