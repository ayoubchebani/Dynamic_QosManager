from django import forms
from .models import *


class AddApplicationForm(forms.ModelForm):
    # begin_time=forms.CharField(required=False)
    class Meta:
        model = Application
        widgets = {
            'business_type': forms.Select(attrs={'class': 'form-control'}),
            'business_app': forms.Select(attrs={'class': 'form-control'}),
            'mark': forms.Select(attrs={'class': 'form-control'}),
            'begin_time': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'hh:mm',
                                                 'pattern': '^(0[0-9]|1[0-9]|2[0-3]|[0-9]):[0-5][0-9]$'}),
            'end_time': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'hh:mm',
                                               'pattern': '^(0[0-9]|1[0-9]|2[0-3]|[0-9]):[0-5][0-9]$'}),
            'source': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'a.b.c.d/mask',
                                             'pattern': '^any|^((\d){1,3}\.){3}(\d){1,3}\/(\d){1,3}'}),
            'destination': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'a.b.c.d/mask',
                                                  'pattern': '^any|^((\d){1,3}\.){3}(\d){1,3}\/(\d){1,3}'}),
        }

        fields = (
            'business_type', 'business_app', 'begin_time', 'end_time', 'source',
            'destination', 'mark')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["business_app"].queryset = BusinessApp.objects.none()
        self.fields["begin_time"].required = False
        self.fields["end_time"].required = False
        self.fields["source"].required = False
        self.fields["destination"].required = False

        if 'BusinessType' in self.data:
            try:
                business_type_id = int(self.data.get('BusinessType'))
                self.fields['business_app'].queryset = BusinessApp.objects.filter(
                    business_type_id=business_type_id).order_by('name')
            except (ValueError, TypeError):
                pass  # invalid input from the client; ignore and fallback to empty City queryset
        elif self.instance.pk:
            self.fields['business_app'].queryset = self.instance.BusinessType.BusinessApp_set.order_by('name')


class AddPolicyForm(forms.ModelForm):
    class Meta:
        model = Policy
        fields = ('name', 'description')

    # topologies = forms.ChoiceField(choices=[(Topology.id, Topology.name) for Topology in Topology.objects.all()])
    name = forms.CharField(max_length=45, widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Enter the policy name', 'type': 'text'}))
    description = forms.CharField(max_length=150, widget=forms.Textarea(
        attrs={'class': 'form-control', 'placeholder': 'describe you policy here ...', 'rows': '2'}))
    topologies = forms.ModelChoiceField(
        queryset=Topology.objects.all(), widget=forms.Select(attrs={
            'class': 'form-control',
            'style': 'margin-bottom: 12px;'
        }))


class AddCustomApplicationForm(forms.ModelForm):
    # begin_time = forms.CharField(required=False)

    # end_time = forms.CharField(required=False)
    # source = forms.CharField(required=False)
    # destination = forms.CharField(required=False)

    class Meta:
        model = Application
        widgets = {
            'custom_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'application name'}),
            'protocol_type': forms.Select(attrs={'class': 'form-control'}),
            'port_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'port from 1024 to 49151',
                                                  'pattern': '(102[4-9]|10[3-9][0-9]|1[1-9][0-9]{2}|[2-9][0-9]{3}|[1-3][0-9]{4}|4[0-8][0-9]{3}|490[0-9]{2}|491[0-4][0-9]|4915[01])'}),
            'begin_time': forms.TimeInput(attrs={'class': 'form-control', 'placeholder': 'hh:mm',
                                                 'pattern': '^(0[0-9]|1[0-9]|2[0-3]|[0-9]):[0-5][0-9]$'}),
            'end_time': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'hh:mm',
                                               'pattern': '^(0[0-9]|1[0-9]|2[0-3]|[0-9]):[0-5][0-9]$'}),
            'source': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'a.b.c.d/mask',
                       'pattern': '^any|^((\d){1,3}\.){3}(\d){1,3}\/(\d){1,3}'}),
            'destination': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'a.b.c.d/mask',
                                                  'pattern': '^any|^((\d){1,3}\.){3}(\d){1,3}\/(\d){1,3}'}),
            'mark': forms.Select(attrs={'class': 'form-control'}),
        }
        fields = ('custom_name', 'protocol_type', 'port_number', 'begin_time', 'end_time', 'source', 'destination',
                  'mark')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["begin_time"].required = False
        self.fields["end_time"].required = False
        self.fields["source"].required = False
        self.fields["destination"].required = False


class DiscoveryForm(forms.Form):
    start = forms.DateTimeField(
        input_formats=['%Y/%m/%d %H:%M'],
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control datetimepicker-input',
            'data-target': '#datetimepicker1'
        })
    )
    end = forms.DateTimeField(
        input_formats=['%Y/%m/%d %H:%M'],
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control datetimepicker-input',
            'data-target': '#datetimepicker2'
        })
    )


class AllInForm(forms.Form):
    name = forms.CharField(max_length=45, widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Enter the policy name', 'type': 'text'}))
    description = forms.CharField(max_length=150, widget=forms.Textarea(
        attrs={'class': 'form-control', 'placeholder': 'describe you policy here ...', 'rows': '2'}))
    topologies = forms.ModelChoiceField(
        queryset=Topology.objects.all(), widget=forms.Select(attrs={
            'class': 'form-control',
            'style': 'margin-bottom: 12px;'
        }))
    start = forms.DateTimeField(
        input_formats=['%Y/%m/%d %H:%M'],
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control datetimepicker-input',
            'data-target': '#datetimepicker1'
        })
    )
