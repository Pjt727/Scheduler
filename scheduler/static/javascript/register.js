function getProfessor(){
    console.log('here')
    const email = document.getElementById("email").value;
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if(!emailPattern.test(email)){
        return
    }

    const url = new URL('get_professor/', window.location.origin);
    url.searchParams.set('email', email);

    fetch(url, {
        method: 'get',
        headers: {'Content-Type': 'application/json',}
    })
        .then(response => response.json())
        .then(data => {
            if(!data['ok']){
                const noProfToast = document.getElementById('noProf');
                const noProfToastBootstrap = bootstrap.Toast.getOrCreateInstance(noProfToast);
                noProfToastBootstrap.show();
                return;
            }

            const newUserProfToast = document.getElementById('newUserProf');
            const newUserProfToastBootstrap = bootstrap.Toast.getOrCreateInstance(newUserProfToast);
            const title = newUserProfToast.querySelector('#toast-title');
            title.innerText = `Hello ${data["last_name"]}, ${data["first_name"]}`;
            const firstName = document.getElementById("first_name");
            firstName.value = data["first_name"];
            const lastName = document.getElementById("last_name");
            lastName.value = data["last_name"];
            newUserProfToastBootstrap.show();
        });
}



document.addEventListener('DOMContentLoaded', () => {
    const email = document.getElementById("email");
    email.addEventListener('blur', getProfessor);
})