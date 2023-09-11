from django import forms

class Register(forms.Form):
    email = forms.EmailField()
    password1 = forms.PasswordInput()
    password2 = forms.PasswordInput()