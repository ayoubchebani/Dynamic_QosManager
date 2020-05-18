from django import forms
from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class":"form-control","placeholder":"username","name":"email","type":"text"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class":"form-control","placeholder":"password","name":"password","type":"password","value":""}))

class GetJsonFile(forms.Form):
    Text = forms.CharField(max_length=10000,widget=forms.Textarea(attrs={"id":"mySavedModel","style":"width:100%;height:1px;"}))

class AddTopologyForm(forms.Form):
    Name = forms.CharField(max_length=45,widget=forms.TextInput(attrs={'class':'form-control','placeholder':'Enter the topology name','type':'text'}))
    TopologyDesc = forms.CharField(max_length=150,widget=forms.Textarea(attrs={'class':'form-control','placeholder':'describe you topology here ...','rows':'2'}))
