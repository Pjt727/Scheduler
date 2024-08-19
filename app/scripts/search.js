function liveSearch(inputLiveSearchId, searchResultsId) {
    let selectedOptionIndex = -1;
    const inputLiveSearch = document.getElementById(inputLiveSearchId);
    const searchResults = document.getElementById(searchResultsId);

    inputLiveSearch.addEventListener('focus', () => {
        searchResults.style.display = 'block';
    });
    inputLiveSearch.addEventListener('blur', () => {
        setTimeout(() => {
            searchResults.style.display = 'none';
        }, 200);
    });
    inputLiveSearch.addEventListener('keydown', (event) => {
        const options = searchResults.querySelectorAll('.search-option');

        if (event.key === 'ArrowUp') {
            event.preventDefault();
            if (selectedOptionIndex > 0) {
                options[selectedOptionIndex].classList.remove('selected-option');
                selectedOptionIndex--;
                options[selectedOptionIndex].classList.add('selected-option');
            }
        } else if (event.key === 'ArrowDown') {
            event.preventDefault();
            if (selectedOptionIndex < options.length - 1) {
                if (selectedOptionIndex >= 0) {
                    options[selectedOptionIndex].classList.remove('selected-option');
                }
                selectedOptionIndex++;
                options[selectedOptionIndex].classList.add('selected-option');
            }
        }
        if (event.key === 'Enter' || event.key === 'Return') {
            if (options.length == 1) {
                htmx.trigger(options[0], 'click');
                inputLiveSearch.blur()
            } else if (selectedOptionIndex >= 0) {
                htmx.trigger(options[selectedOptionIndex], 'click');
                inputLiveSearch.blur()
            }
        }
        // Scroll the selected option into view
        if (options[selectedOptionIndex]) {
            options[selectedOptionIndex].scrollIntoView({
                behavior: 'smooth',
                block: 'nearest',
                inline: 'nearest'
            });
        }
    });

}
