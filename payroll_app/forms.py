from django import forms


class OrganizationRegistrationForm(forms.Form):
    name = forms.CharField(max_length=255)
    email = forms.EmailField()
    address = forms.CharField(widget=forms.Textarea, required=False)


class OrgAdminCreationForm(forms.Form):
    email = forms.EmailField()
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password1")
        p2 = cleaned_data.get("password2")

        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data



class CustomLoginForm(forms.Form):
    organization_id = forms.UUIDField()
    username = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    role = forms.ChoiceField(
        choices=[
            ('OrgAdmin', 'Organization Admin'),
            ('HR', 'HR Personnel'),
            ('Employee', 'Employee'),
        ]
    )


class NotificationForm(forms.Form):
    RECIPIENT_CHOICES = [
        ('All', 'All Users'),
        ('HR', 'HR Personnel'),
        ('Employee', 'Regular Employees'),
    ]
    title = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4})
    )
    recipient_type = forms.ChoiceField(
        choices=RECIPIENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
