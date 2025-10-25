from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile, Expense, Investment, Budget


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['full_name', 'monthly_salary', 'phone_number', 'date_of_birth', 'address', 'profile_picture']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your full name'
            }),
            'monthly_salary': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your monthly salary',
                'step': '0.01',
                'min': '0'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your phone number'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter your address'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['category', 'amount', 'description', 'date']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter amount',
                'step': '0.01',
                'min': '0'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter description'
            }),
            'date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default date to now if not provided
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['date'].initial = timezone.now()


class InvestmentForm(forms.ModelForm):
    class Meta:
        model = Investment
        fields = ['investment_type', 'amount', 'description', 'date']
        widgets = {
            'investment_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter amount',
                'step': '0.01',
                'min': '0'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter description'
            }),
            'date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default date to now if not provided
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['date'].initial = timezone.now()


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['category', 'allocated_amount']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'allocated_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter allocated amount',
                'step': '0.01',
                'min': '0'
            })
        }


class BudgetManagementForm(forms.Form):
    """Form for managing multiple budgets at once"""
    def __init__(self, *args, **kwargs):
        categories = kwargs.pop('categories', [])
        super().__init__(*args, **kwargs)
        
        for category in categories:
            self.fields[f'budget_{category}'] = forms.DecimalField(
                max_digits=10,
                decimal_places=2,
                required=False,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control',
                    'placeholder': f'Enter budget for {category}',
                    'step': '0.01',
                    'min': '0'
                })
            )


class ExpenseFilterForm(forms.Form):
    category = forms.ChoiceField(
        choices=[('', 'All Categories')] + Expense.CATEGORY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search in descriptions'
        })
    )


class InvestmentFilterForm(forms.Form):
    investment_type = forms.ChoiceField(
        choices=[('', 'All Types')] + Investment.INVESTMENT_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search in descriptions'
        })
    )
