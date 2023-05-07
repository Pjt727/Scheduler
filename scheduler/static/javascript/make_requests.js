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


function addModelFormListeners() {
    const formElements = document.querySelectorAll('.form-modal-element');

    formElements.forEach(formElement => {
        formElement.addEventListener('submit', (event) => {
            event.preventDefault();

            const form = event.target;
            form.querySelector('input[type="submit"]').disabled = true;
            const csrfToken = form.querySelector('input[name="csrfmiddlewaretoken"]').value;

            fetch(form.action, {
                    method: form.method,
                    headers: { 'X-CSRFToken': csrfToken },
                    body: new FormData(form)
                })
                .then(response => response.json())
                .then(data => {
                    const formId = form.id;
                    const modal = document.querySelector('#modal-' + formId);
                    modal.modal('hide');

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

function updateForm(form) {
    const formId = form.id;
    const url = `/get_form/${formId}`;

    // Make a Fetch request to the update URL to get the updated form HTML
    fetch(url, {
            method: 'GET',
            body: new FormData(form),
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCookie('csrftoken')
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



document.addEventListener('DOMContentLoaded', function() {
    addModelFormListeners();
});