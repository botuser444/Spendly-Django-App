from django.urls import path
from . import views

urlpatterns = [
    # Authentication URLs
    path('', views.home, name='home'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Main dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Profile management
    path('profile/', views.profile_view, name='profile'),
    
    # Expense management
    path('expenses/add/', views.add_expense, name='add_expense'),
    path('expenses/', views.expense_list, name='expense_list'),
    path('expenses/edit/<int:expense_id>/', views.edit_expense, name='edit_expense'),
    path('expenses/delete/<int:expense_id>/', views.delete_expense, name='delete_expense'),
    
    # Investment management
    path('investments/add/', views.add_investment, name='add_investment'),
    path('investments/', views.investment_list, name='investment_list'),
    path('investments/edit/<int:investment_id>/', views.edit_investment, name='edit_investment'),
    path('investments/delete/<int:investment_id>/', views.delete_investment, name='delete_investment'),
    
    # Budget management
    path('budget/', views.budget_management, name='budget_management'),
    
    # Analytics
    path('analytics/', views.analytics, name='analytics'),
    
    # Month reset and report generation
    path('reset-month/', views.reset_month, name='reset_month'),
    path('download-report/', views.download_report, name='download_report'),
]
