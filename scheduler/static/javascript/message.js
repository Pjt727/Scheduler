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