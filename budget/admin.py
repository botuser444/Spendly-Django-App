from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, Expense, Investment, Budget, MonthlyReport


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ('full_name', 'monthly_salary', 'phone_number', 'date_of_birth', 'address', 'profile_picture')


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'amount', 'description', 'date', 'month_year')
    list_filter = ('category', 'month_year', 'date', 'user')
    search_fields = ('user__username', 'description', 'category')
    list_per_page = 25
    ordering = ('-date',)
    readonly_fields = ('created_at', 'month_year')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'investment_type', 'amount', 'description', 'date', 'month_year')
    list_filter = ('investment_type', 'month_year', 'date', 'user')
    search_fields = ('user__username', 'description', 'investment_type')
    list_per_page = 25
    ordering = ('-date',)
    readonly_fields = ('created_at', 'month_year')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'allocated_amount', 'month_year', 'get_spent_amount', 'get_remaining_budget')
    list_filter = ('category', 'month_year', 'user')
    search_fields = ('user__username', 'category')
    list_per_page = 25
    ordering = ('-month_year', 'category')
    readonly_fields = ('created_at', 'updated_at')

    def get_spent_amount(self, obj):
        return obj.get_spent_amount()
    get_spent_amount.short_description = 'Amount Spent'

    def get_remaining_budget(self, obj):
        return obj.get_remaining_budget()
    get_remaining_budget.short_description = 'Remaining Budget'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(MonthlyReport)
class MonthlyReportAdmin(admin.ModelAdmin):
    list_display = ('user', 'month_year', 'total_income', 'total_expenses', 'total_investments', 'total_savings', 'report_generated_date')
    list_filter = ('month_year', 'report_generated_date', 'user')
    search_fields = ('user__username', 'month_year')
    list_per_page = 25
    ordering = ('-month_year', '-report_generated_date')
    readonly_fields = ('report_generated_date',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Customize admin site
admin.site.site_header = "Spendly Administration"
admin.site.site_title = "Spendly Admin"
admin.site.index_title = "Welcome to Spendly Administration"