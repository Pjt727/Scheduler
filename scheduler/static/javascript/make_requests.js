function successMessage(message) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('alert', 'alert-success', 'alert-dismissible', 'fade', 'show');
    messageDiv.setAttribute('role', 'alert');
    messageDiv.innerHTML = message +
        '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>';
    const messageContainer = document.getElementById('message');
    messageContainer.appendChild(messageDiv);
}

function errorMessage(message) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('alert', 'alert-danger', 'alert-dismissible', 'fade', 'show');
    messageDiv.setAttribute('role', 'alert');
    messageDiv.innerHTML = message +
        '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>';
    const messageContainer = document.getElementById('message');
    messageContainer.appendChild(messageDiv);
}

function changeSelectValue(formElement, selectName, newValue) {
    const selectElement = formElement.querySelector(`#id_${selectName}`);
    if (!selectElement.querySelector(`option[value="${newValue}"]`)) {
        const loadingOption = document.createElement('option');
        loadingOption.value = newValue;
        loadingOption.innerText = 'Loading...';
        selectElement.appendChild(loadingOption);
    }
    selectElement.value = newValue;
}


function addModalFormListeners() {
    const formElements = document.querySelectorAll('.form-modal-element');
    // Submit functionality
    formElements.forEach(formElement => {
        formElement.addEventListener('submit', (event) => {
            event.preventDefault();
            const form = event.target;
            form.querySelector('input[type="submit"]').disabled = true;
            const csrfToken = form.querySelector('input[name="csrfmiddlewaretoken"]').value;

            fetch(form.action, {
                    method: 'post',
                    headers: { 'X-CSRFToken': csrfToken },
                    body: new FormData(form)
                })
                .then(response => response.json())
                .then(data => {
                    const formId = form.id;
                    const modal = document.querySelector('#modal-' + formId);
                    // modal does not close properly for whatever reason
                    /*const myModal = new bootstrap.Modal(modal, {
                        keyboard: false
                      })

                    console.log(myModal)
                    */
                    // TODO make the modal close...

                    if (data.ok) {
                        form.reset();
                        const requestBundleValue = data.requestBundleValue;
                        successMessage(data.message);

                        // submit-request-bundle
                        const submitRequestBundleForm = document.querySelector('#submit-request-bundle');
                        changeSelectValue(submitRequestBundleForm, "request_bundle", requestBundleValue);
                        updateForm(submitRequestBundleForm);
                    } else {
                        errorMessage(data.errors);
                    }
                })
                .catch(error => {
                    console.error(error);
                })
                .finally(() => {
                    setTimeout(() => { form.querySelector('input[type="submit"]').disabled = false; }, 50);
                });
        });
    });
}

function addSubmitRequest() {
    const submitRequestBundleForm = document.querySelector('#submit-request-bundle');
    submitRequestBundleForm.addEventListener('submit', function(event) {
        event.preventDefault();
        submitRequestBundleForm.querySelector('input[type="submit"]').disabled = true;
        var csrf_token = submitRequestBundleForm.querySelector('input[name="csrfmiddlewaretoken"]').value;
        let submitType = event.submitter.dataset.value;
        fetch(submitRequestBundleForm.action, {
                method: submitRequestBundleForm.method,
                headers: { 'X-CSRFToken': csrf_token, 'button': submitType },
                body: new FormData(submitRequestBundleForm)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    successMessage(data.message);
                    updateForm(submitRequestBundleForm);
                } else {
                    errorMessage(data.errors);
                }
            })
            .finally(() => {
                setTimeout(() => { submitRequestBundleForm.querySelector('input[type="submit"]').disabled = false }, 50);
            });
    });
}

function updateForm(form) {
    const formId = form.id;
    const url = `/get_form/${formId}`;

    // Make a Fetch request to the update URL to get the updated form HTML
    fetch(url, {
            method: 'POST',
            body: new FormData(form),
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': form.querySelector('input[name="csrfmiddlewaretoken"]').value
            }
        })
        .then(response => response.json())
        .then(response => {
            // Check if the form has an inputs container
            const inputsContainer = document.querySelector(`#inputs-${formId}`);
            if (!inputsContainer) {
                console.error(
                    `${form} can not be updated because it does not have an inputs container which should be id'ed "#inputs-${formId}".`
                );
                return;
            }

            // Insert the updated form HTML into the form element
            inputsContainer.innerHTML = response.form_html;
        })
        .catch(error => console.error(error));
}

function submitBundleUpdates() {
    const submitRequestBundleForm = document.querySelector('#submit-request-bundle');
    const formElements = document.querySelectorAll('.form-modal-element');
    submitRequestBundleForm.addEventListener('change', (e) => {
        if (!(e.target.name === 'request_bundle')) { return };
        updateForm(submitRequestBundleForm);
        const requestBundleSelectVal = submitRequestBundleForm.querySelector("#id_request_bundle").value;
        const requestBundleSelects = document.querySelectorAll('#id_request_bundle');
        // update the request values
        requestBundleSelects.forEach(requestBundleSelect => { requestBundleSelect.value = requestBundleSelectVal });
        // refresh the forms
        formElements.forEach(form => { updateForm(form) });
    })
}

document.addEventListener('DOMContentLoaded', function() {
    // configure modal submit buttons for fetches 
    addModalFormListeners();

    // configure request bundle submit button for fetches
    addSubmitRequest();

    // update all the forms
    document.querySelectorAll('form').forEach(function(element) { updateForm(element) });

    //update all forms when the backdrop request bundle changes
    submitBundleUpdates();
});