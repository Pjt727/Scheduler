from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms

class RegisterUserForm(UserCreationForm):
    username = forms.EmailField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=50, widget=forms.TextInput(attrs={'class': 'form-control'}))
    credits = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control'}))
    id = "register-user-form"

    class Meta:
        model = User
        fields = (
            'username',
            'password1',
            'password2'
        ) 