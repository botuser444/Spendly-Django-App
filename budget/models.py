from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from django.conf import settings


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    full_name = models.CharField(max_length=100, blank=True)
    monthly_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    phone_number = models.CharField(max_length=15, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def get_full_name(self):
        return self.full_name if self.full_name else self.user.get_full_name()


class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('Food', 'Food'),
        ('Transport', 'Transport'),
        ('Shopping', 'Shopping'),
        ('Bills', 'Bills'),
        ('Entertainment', 'Entertainment'),
        ('Healthcare', 'Healthcare'),
        ('Education', 'Education'),
        ('Other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    date = models.DateTimeField(default=timezone.now)
    month_year = models.CharField(max_length=7, help_text="Format: YYYY-MM")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        symbol = getattr(settings, 'DEFAULT_CURRENCY_SYMBOL', '₨')
        return f"{self.category} - {symbol}{format(self.amount, '.2f')} ({self.date.strftime('%Y-%m-%d')})"

    def save(self, *args, **kwargs):
        # Set month_year when saving
        self.month_year = self.date.strftime('%Y-%m')
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-date']


class Investment(models.Model):
    INVESTMENT_TYPE_CHOICES = [
        ('Stocks', 'Stocks'),
        ('Mutual Funds', 'Mutual Funds'),
        ('Real Estate', 'Real Estate'),
        ('Savings', 'Savings'),
        ('Crypto', 'Crypto'),
        ('Other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    investment_type = models.CharField(max_length=20, choices=INVESTMENT_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    date = models.DateTimeField(default=timezone.now)
    month_year = models.CharField(max_length=7, help_text="Format: YYYY-MM")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        symbol = getattr(settings, 'DEFAULT_CURRENCY_SYMBOL', '₨')
        return f"{self.investment_type} - {symbol}{format(self.amount, '.2f')} ({self.date.strftime('%Y-%m-%d')})"

    def save(self, *args, **kwargs):
        # Set month_year when saving
        self.month_year = self.date.strftime('%Y-%m')
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-date']


class Budget(models.Model):
    CATEGORY_CHOICES = [
        ('Food', 'Food'),
        ('Transport', 'Transport'),
        ('Shopping', 'Shopping'),
        ('Bills', 'Bills'),
        ('Entertainment', 'Entertainment'),
        ('Healthcare', 'Healthcare'),
        ('Education', 'Education'),
        ('Other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    allocated_amount = models.DecimalField(max_digits=10, decimal_places=2)
    month_year = models.CharField(max_length=7, help_text="Format: YYYY-MM")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        symbol = getattr(settings, 'DEFAULT_CURRENCY_SYMBOL', '₨')
        return f"{self.category} Budget - {symbol}{format(self.allocated_amount, '.2f')} ({self.month_year})"

    def get_spent_amount(self):
        """Calculate actual amount spent in this category for the month"""
        expenses = Expense.objects.filter(
            user=self.user,
            category=self.category,
            month_year=self.month_year
        )
        return sum(expense.amount for expense in expenses)

    def get_remaining_budget(self):
        """Calculate remaining budget"""
        spent = self.get_spent_amount()
        return self.allocated_amount - spent

    def get_percentage_used(self):
        """Calculate percentage of budget used"""
        if self.allocated_amount == 0:
            return 0
        spent = self.get_spent_amount()
        return (spent / self.allocated_amount) * 100

    class Meta:
        unique_together = ['user', 'category', 'month_year']
        ordering = ['category']


class MonthlyReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    month_year = models.CharField(max_length=7, help_text="Format: YYYY-MM")
    total_income = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_expenses = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_investments = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_savings = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    report_generated_date = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='reports/', blank=True, null=True)

    def __str__(self):
        return f"Monthly Report - {self.month_year} ({self.user.username})"

    def calculate_savings(self):
        """Calculate savings as income - expenses - investments"""
        return self.total_income - self.total_expenses - self.total_investments

    class Meta:
        unique_together = ['user', 'month_year']
        ordering = ['-month_year']