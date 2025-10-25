from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, FileResponse
from django.db.models import Sum, Q
from django.utils import timezone
from django.core.paginator import Paginator
from decimal import Decimal
import json
import os
from datetime import datetime, timedelta
from django.conf import settings
import traceback

# ReportLab imports for PDF generation with charts - wrapped so the app can start without ReportLab installed
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.graphics.shapes import Drawing, String
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics import renderPM
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

from .models import UserProfile, Expense, Investment, Budget, MonthlyReport
from .forms import (
    UserRegistrationForm, UserProfileForm, ExpenseForm, InvestmentForm, 
    BudgetForm, BudgetManagementForm, ExpenseFilterForm, InvestmentFilterForm
)


def home(request):
    """Landing page with login/signup options"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'budget/home.html')


def register_view(request):
    """User registration"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create user profile
            UserProfile.objects.create(user=user)
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'budget/register.html', {'form': form})


def login_view(request):
    """User login"""
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'budget/login.html')


def logout_view(request):
    """User logout"""
    logout(request)
    return redirect('home')


@login_required
def dashboard(request):
    """Main dashboard showing financial overview"""
    current_month = timezone.now().strftime('%Y-%m')
    
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Calculate current month totals
    total_income = float(profile.monthly_salary)
    total_expenses = float(Expense.objects.filter(
        user=request.user, 
        month_year=current_month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'))
    
    total_investments = float(Investment.objects.filter(
        user=request.user, 
        month_year=current_month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'))
    
    total_savings = total_income - total_expenses - total_investments
    
    # Get expense breakdown by category and convert to JSON-serializable list
    expense_qs = Expense.objects.filter(
        user=request.user,
        month_year=current_month
    ).values('category').annotate(total=Sum('amount')).order_by('-total')
    expense_breakdown = [
        {
            'category': item['category'],
            'total': float(item['total'] or 0)
        }
        for item in expense_qs
    ]
    
    # Get budget vs actual spending
    budgets = Budget.objects.filter(user=request.user, month_year=current_month)
    # If there are no budgets for the current month, fall back to the most recent month with budgets
    budget_month_used = current_month
    if not budgets.exists():
        latest = Budget.objects.filter(user=request.user).order_by('-month_year').first()
        if latest:
            budget_month_used = latest.month_year
            budgets = Budget.objects.filter(user=request.user, month_year=budget_month_used)
    budget_vs_actual = []
    for budget in budgets:
        actual_spent = budget.get_spent_amount()
        budget_vs_actual.append({
            'category': budget.category,
            'allocated': float(budget.allocated_amount),
            'actual': float(actual_spent),
            'remaining': float(budget.get_remaining_budget())
        })
    
    # Get spending trend for last 6 months
    spending_trend = []
    for i in range(6):
        month = (timezone.now() - timedelta(days=30*i)).strftime('%Y-%m')
        month_expenses = Expense.objects.filter(
            user=request.user,
            month_year=month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        spending_trend.append({
            'month': month,
            'amount': float(month_expenses)
        })
    spending_trend.reverse()
    
    # Get recent transactions
    recent_expenses = Expense.objects.filter(user=request.user)[:5]
    recent_investments = Investment.objects.filter(user=request.user)[:5]
    
    context = {
        'profile': profile,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'total_investments': total_investments,
        'total_savings': total_savings,
        'expense_breakdown': expense_breakdown,
        'budget_vs_actual': budget_vs_actual,
        'spending_trend': spending_trend,
        'recent_expenses': recent_expenses,
        'recent_investments': recent_investments,
        'current_month': current_month,
        'budget_month_used': budget_month_used,
    }

    # Show debug banner only to superusers when DEBUG is True
    context['show_debug_banner'] = getattr(settings, 'DEBUG', False) and request.user.is_superuser

    # Provide JSON-encoded versions for safe injection into JS in templates
    context['expense_breakdown_json'] = json.dumps(expense_breakdown)
    context['budget_vs_actual_json'] = json.dumps(budget_vs_actual)
    context['spending_trend_json'] = json.dumps(spending_trend)
    
    return render(request, 'budget/dashboard.html', context)


@login_required
def profile_view(request):
    """View and edit user profile"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=profile)
    
    return render(request, 'budget/profile.html', {'form': form, 'profile': profile})


@login_required
def add_expense(request):
    """Add new expense"""
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            messages.success(request, 'Expense added successfully!')
            return redirect('expense_list')
    else:
        form = ExpenseForm()
    
    return render(request, 'budget/add_expense.html', {'form': form})


@login_required
def expense_list(request):
    """List all expenses with filter options"""
    expenses = Expense.objects.filter(user=request.user).order_by('-date')
    
    # Apply filters
    filter_form = ExpenseFilterForm(request.GET)
    if filter_form.is_valid():
        if filter_form.cleaned_data['category']:
            expenses = expenses.filter(category=filter_form.cleaned_data['category'])
        if filter_form.cleaned_data['start_date']:
            expenses = expenses.filter(date__date__gte=filter_form.cleaned_data['start_date'])
        if filter_form.cleaned_data['end_date']:
            expenses = expenses.filter(date__date__lte=filter_form.cleaned_data['end_date'])
        if filter_form.cleaned_data['search']:
            expenses = expenses.filter(description__icontains=filter_form.cleaned_data['search'])
    
    # Pagination
    paginator = Paginator(expenses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate total
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'total_expenses': total_expenses,
    }
    
    return render(request, 'budget/expense_list.html', context)


@login_required
def edit_expense(request, expense_id):
    """Edit existing expense"""
    expense = get_object_or_404(Expense, id=expense_id, user=request.user)
    
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense updated successfully!')
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense)
    
    return render(request, 'budget/edit_expense.html', {'form': form, 'expense': expense})


@login_required
def delete_expense(request, expense_id):
    """Delete expense"""
    expense = get_object_or_404(Expense, id=expense_id, user=request.user)
    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Expense deleted successfully!')
        return redirect('expense_list')
    
    return render(request, 'budget/delete_expense.html', {'expense': expense})


@login_required
def add_investment(request):
    """Add new investment"""
    if request.method == 'POST':
        form = InvestmentForm(request.POST)
        if form.is_valid():
            investment = form.save(commit=False)
            investment.user = request.user
            investment.save()
            messages.success(request, 'Investment added successfully!')
            return redirect('investment_list')
    else:
        form = InvestmentForm()
    
    return render(request, 'budget/add_investment.html', {'form': form})


@login_required
def investment_list(request):
    """List all investments"""
    investments = Investment.objects.filter(user=request.user).order_by('-date')
    
    # Apply filters
    filter_form = InvestmentFilterForm(request.GET)
    if filter_form.is_valid():
        if filter_form.cleaned_data['investment_type']:
            investments = investments.filter(investment_type=filter_form.cleaned_data['investment_type'])
        if filter_form.cleaned_data['start_date']:
            investments = investments.filter(date__date__gte=filter_form.cleaned_data['start_date'])
        if filter_form.cleaned_data['end_date']:
            investments = investments.filter(date__date__lte=filter_form.cleaned_data['end_date'])
        if filter_form.cleaned_data['search']:
            investments = investments.filter(description__icontains=filter_form.cleaned_data['search'])
    
    # Pagination
    paginator = Paginator(investments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate total
    total_investments = investments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'total_investments': total_investments,
    }
    
    return render(request, 'budget/investment_list.html', context)


@login_required
def edit_investment(request, investment_id):
    """Edit existing investment"""
    investment = get_object_or_404(Investment, id=investment_id, user=request.user)
    
    if request.method == 'POST':
        form = InvestmentForm(request.POST, instance=investment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Investment updated successfully!')
            return redirect('investment_list')
    else:
        form = InvestmentForm(instance=investment)
    
    return render(request, 'budget/edit_investment.html', {'form': form, 'investment': investment})


@login_required
def delete_investment(request, investment_id):
    """Delete investment"""
    investment = get_object_or_404(Investment, id=investment_id, user=request.user)
    if request.method == 'POST':
        investment.delete()
        messages.success(request, 'Investment deleted successfully!')
        return redirect('investment_list')
    
    return render(request, 'budget/delete_investment.html', {'investment': investment})


@login_required
def budget_management(request):
    """Set/edit monthly budgets"""
    current_month = timezone.now().strftime('%Y-%m')
    categories = [choice[0] for choice in Expense.CATEGORY_CHOICES]
    
    if request.method == 'POST':
        # Handle budget updates
        for category in categories:
            budget_key = f'budget_{category}'
            amount = request.POST.get(budget_key)
            if amount and Decimal(amount) > 0:
                budget, created = Budget.objects.get_or_create(
                    user=request.user,
                    category=category,
                    month_year=current_month,
                    defaults={'allocated_amount': Decimal(amount)}
                )
                if not created:
                    budget.allocated_amount = Decimal(amount)
                    budget.save()
        
        messages.success(request, 'Budgets updated successfully!')
        return redirect('budget_management')
    
    # Get current budgets
    budgets = Budget.objects.filter(user=request.user, month_year=current_month)
    budget_dict = {budget.category: budget.allocated_amount for budget in budgets}
    # Build a list aligned with categories so templates can render input values reliably
    categories_with_values = []
    for category in categories:
        amt = budget_dict.get(category)
        categories_with_values.append({
            'category': category,
            'amount': float(amt) if amt is not None else ''
        })
    
    # Get budget vs actual data
    budget_vs_actual = []
    for category in categories:
        budget_amount = budget_dict.get(category, Decimal('0.00'))
        actual_spent = Expense.objects.filter(
            user=request.user,
            category=category,
            month_year=current_month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        # Compute percentage used safely (avoid division by zero)
        percent_used = 0.0
        try:
            if budget_amount != Decimal('0.00'):
                percent_used = float((actual_spent / budget_amount) * 100)
        except Exception:
            percent_used = 0.0

        remaining_val = float(budget_amount - actual_spent)
        budget_vs_actual.append({
            'category': category,
            'allocated': float(budget_amount),
            'actual': float(actual_spent),
            'remaining': remaining_val,
            'remaining_abs': abs(remaining_val),
            'percent_used': percent_used,
        })
    
    context = {
        'categories': categories,
        'budget_dict': budget_dict,
        'budget_vs_actual': budget_vs_actual,
        'current_month': current_month,
        'categories_with_values': categories_with_values,
    }
    
    return render(request, 'budget/budget_management.html', context)


@login_required
def analytics(request):
    """Detailed analytics page with multiple charts"""
    # Get data for last 12 months
    monthly_data = []
    for i in range(12):
        month = (timezone.now() - timedelta(days=30*i)).strftime('%Y-%m')
        month_expenses = Expense.objects.filter(
            user=request.user, 
            month_year=month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        month_investments = Investment.objects.filter(
            user=request.user, 
            month_year=month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        monthly_data.append({
            'month': month,
            'expenses': float(month_expenses),
            'investments': float(month_investments)
        })
    monthly_data.reverse()
    
    # Get expense breakdown by category (current month) and make JSON-serializable
    current_month = timezone.now().strftime('%Y-%m')
    expense_qs = Expense.objects.filter(
        user=request.user,
        month_year=current_month
    ).values('category').annotate(total=Sum('amount')).order_by('-total')
    expense_breakdown = [
        {'category': e['category'], 'total': float(e['total'] or 0)} for e in expense_qs
    ]

    # Get investment breakdown by type (current month) and make JSON-serializable
    investment_qs = Investment.objects.filter(
        user=request.user,
        month_year=current_month
    ).values('investment_type').annotate(total=Sum('amount')).order_by('-total')
    investment_breakdown = [
        {'investment_type': i['investment_type'], 'total': float(i['total'] or 0)} for i in investment_qs
    ]
    
    # Calculate savings rate
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    total_income = float(profile.monthly_salary)
    total_expenses = float(Expense.objects.filter(
        user=request.user, 
        month_year=current_month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'))
    
    savings_rate = 0
    if total_income > 0:
        savings_rate = ((total_income - total_expenses) / total_income) * 100
    
    context = {
        'monthly_data': monthly_data,
        'expense_breakdown': expense_breakdown,
        'investment_breakdown': investment_breakdown,
        'savings_rate': savings_rate,
        'total_income': total_income,
        'total_expenses': total_expenses,
    }
    
    return render(request, 'budget/analytics.html', context)


@login_required
def reset_month(request):
    """Generate PDF report and reset for new month"""
    # For safety: reset_month will perform the destructive "reset" of current month's transactions.
    # Report generation has been moved to a separate endpoint (`download_report`) so users can download
    # a report without immediately wiping data.
    if request.method == 'POST':
        current_month = timezone.now().strftime('%Y-%m')

        # Delete expenses and investments for the current month for this user
        expenses_qs = Expense.objects.filter(user=request.user, month_year=current_month)
        investments_qs = Investment.objects.filter(user=request.user, month_year=current_month)
        exp_count, _ = expenses_qs.delete()
        inv_count, _ = investments_qs.delete()

        messages.success(request, f'Reset complete: deleted {exp_count} expenses and {inv_count} investments for {current_month}.')
        return redirect('dashboard')

    return render(request, 'budget/reset_month.html')


@login_required
def download_report(request):
    """Generate the monthly report file and return it as an attachment (no destructive reset)."""
    if request.method != 'POST':
        # Forbid GET to avoid accidental report generation; require explicit POST with CSRF
        messages.error(request, 'Report download must be requested via the interface.')
        return redirect('dashboard')

    current_month = timezone.now().strftime('%Y-%m')
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    total_income = float(profile.monthly_salary)

    total_expenses = float(Expense.objects.filter(
        user=request.user, 
        month_year=current_month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'))

    total_investments = float(Investment.objects.filter(
        user=request.user, 
        month_year=current_month
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'))

    total_savings = total_income - total_expenses - total_investments

    pdf_filename = f"monthly_report_{request.user.username}_{current_month}.pdf"
    pdf_path = os.path.join('media', 'reports', pdf_filename)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    currency_symbol = getattr(settings, 'DEFAULT_CURRENCY_SYMBOL', '₨')
    txt_path = pdf_path.replace('.pdf', '.txt')
    # Try importing ReportLab dynamically so a running server picks up a newly-installed package
    try:
        from reportlab.lib.pagesizes import letter as RL_letter
        from reportlab.platypus import SimpleDocTemplate as RL_SimpleDocTemplate, Table as RL_Table, TableStyle as RL_TableStyle, Paragraph as RL_Paragraph, Spacer as RL_Spacer, Image as RL_Image
        from reportlab.lib.styles import getSampleStyleSheet as RL_getSampleStyleSheet, ParagraphStyle as RL_ParagraphStyle
        from reportlab.lib import colors as RL_colors
        from reportlab.lib.units import inch as RL_inch
        from reportlab.graphics.shapes import Drawing as RL_Drawing, String as RL_String
        from reportlab.graphics.charts.piecharts import Pie as RL_Pie
        from reportlab.graphics.charts.barcharts import VerticalBarChart as RL_VerticalBarChart
        from reportlab.graphics.charts.lineplots import LinePlot as RL_LinePlot
        from reportlab.graphics import renderPM as RL_renderPM
        local_reportlab = True
    except Exception:
        local_reportlab = False

    if not local_reportlab:
        # Fallback to text report
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"Spendly Monthly Report - {current_month}\n")
            f.write(f"User: {request.user.get_full_name() or request.user.username}\n")
            f.write(f"Email: {request.user.email}\n")
            f.write(f"Monthly Salary: {currency_symbol}{total_income:,.2f}\n")
            f.write(f"Total Expenses: {currency_symbol}{total_expenses:,.2f}\n")
            f.write(f"Total Investments: {currency_symbol}{total_investments:,.2f}\n")
            f.write(f"Total Savings: {currency_symbol}{total_savings:,.2f}\n")
            f.write(f"Report Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        monthly_report, created = MonthlyReport.objects.update_or_create(
            user=request.user,
            month_year=current_month,
            defaults={
                'total_income': total_income,
                'total_expenses': total_expenses,
                'total_investments': total_investments,
                'total_savings': total_savings,
                'pdf_file': txt_path,
            }
        )

        messages.warning(request, 'ReportLab not available — generated a plain text report instead. To enable PDF reports install reportlab and pillow and restart the server.')
        return FileResponse(open(os.path.abspath(txt_path), 'rb'), as_attachment=True, filename=os.path.basename(txt_path))

    # Build PDF report using ReportLab with charts
    try:
        # Recompute data for charts
        expense_qs = Expense.objects.filter(user=request.user, month_year=current_month).values('category').annotate(total=Sum('amount')).order_by('-total')
        expense_breakdown = [(e['category'], float(e['total'] or 0)) for e in expense_qs]

        budgets_qs = Budget.objects.filter(user=request.user, month_year=current_month)
        budget_vs_actual = []
        for b in budgets_qs:
            actual = Expense.objects.filter(user=request.user, category=b.category, month_year=b.month_year).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            budget_vs_actual.append((b.category, float(b.allocated_amount), float(actual)))

        trend_qs = []
        for i in range(6):
            month = (timezone.now() - timedelta(days=30*i)).strftime('%Y-%m')
            amt = Expense.objects.filter(user=request.user, month_year=month).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            trend_qs.append((month, float(amt)))
        trend_qs.reverse()

        # Create PDF with nicer styling
        doc = RL_SimpleDocTemplate(pdf_path, pagesize=RL_letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        styles = RL_getSampleStyleSheet()
        story = []

        # Custom styles
        title_style = ParagraphStyle('ReportTitle', parent=styles['Title'], fontSize=20, alignment=1, textColor=RL_colors.HexColor('#1F4E79'))
        normal = styles['Normal']
        heading = ParagraphStyle('Heading', parent=styles.get('Heading2', normal), fontSize=12, textColor=RL_colors.HexColor('#1F4E79'))
        small = ParagraphStyle('small', parent=normal, fontSize=9, textColor=RL_colors.HexColor('#374151'))
        muted = ParagraphStyle('muted', parent=small, textColor=RL_colors.HexColor('#6B7280'))

        # Use an ASCII-safe currency prefix for PDF rendering (fonts may not contain the '₨' glyph)
        pdf_currency = 'Rs'  # use 'Rs' to avoid missing-glyph boxes in PDF fonts

        # Header with subtle background
        header_table = RL_Table([[RL_Paragraph(f"Spendly", ParagraphStyle('brand', parent=styles['Title'], fontSize=22, textColor=RL_colors.white)), RL_Paragraph(f"Monthly Report — {current_month}", ParagraphStyle('sub', parent=styles['Title'], fontSize=12, textColor=RL_colors.white))]], colWidths=[300,200])
        header_table.setStyle(RL_TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), RL_colors.HexColor('#2563EB')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 12),
            ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ]))
        story.append(header_table)
        story.append(RL_Spacer(1, 8))

        # User info row
        user_info = [
            ['User', request.user.get_full_name() or request.user.username],
            ['Email', request.user.email],
            ['Generated', timezone.now().strftime('%Y-%m-%d %H:%M:%S')]
        ]
        t = RL_Table(user_info, colWidths=[80, 350])
        t.setStyle(RL_TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, RL_colors.HexColor('#E6EEF8')),
            ('INNERGRID', (0,0), (-1,-1), 0.25, RL_colors.HexColor('#E6EEF8')),
            ('BACKGROUND', (0,0), (-1,-1), RL_colors.white),
        ]))
        story.append(t)
        story.append(RL_Spacer(1, 10))

        # Summary boxes with color accents
        summary_data = [
            [RL_Paragraph(f"<b>Total Income</b><br/>{pdf_currency} {total_income:,.2f}", normal), RL_Paragraph(f"<b>Total Expenses</b><br/>{pdf_currency} {total_expenses:,.2f}", normal)],
            [RL_Paragraph(f"<b>Total Investments</b><br/>{pdf_currency} {total_investments:,.2f}", normal), RL_Paragraph(f"<b>Total Savings</b><br/>{pdf_currency} {total_savings:,.2f}", normal)]
        ]
        sum_table = RL_Table(summary_data, colWidths=[215, 215], rowHeights=[50, 50])
        sum_table.setStyle(RL_TableStyle([
            ('BACKGROUND', (0,0), (0,0), RL_colors.HexColor('#EEF2FF')),
            ('BACKGROUND', (1,0), (1,0), RL_colors.HexColor('#FFF7ED')),
            ('BACKGROUND', (0,1), (0,1), RL_colors.HexColor('#EFF6EE')),
            ('BACKGROUND', (1,1), (1,1), RL_colors.HexColor('#FEF3F2')),
            ('BOX', (0,0), (-1,-1), 0.5, RL_colors.HexColor('#E2E8F0')),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
        ]))
        story.append(sum_table)
        story.append(RL_Spacer(1, 12))

        # Charts row: expense pie, budget vs actual, trend
        chart_items = []
        expense_png = pdf_path.replace('.pdf', '_expense.png')
        chart_items.append(RL_Image(expense_png, width=180, height=120) if os.path.exists(expense_png) else RL_Paragraph('Expense chart unavailable', small))
        budget_png = pdf_path.replace('.pdf', '_budget.png')
        chart_items.append(RL_Image(budget_png, width=180, height=120) if os.path.exists(budget_png) else RL_Paragraph('Budget chart unavailable', small))
        trend_png = pdf_path.replace('.pdf', '_trend.png')
        chart_items.append(RL_Image(trend_png, width=180, height=120) if os.path.exists(trend_png) else RL_Paragraph('Trend chart unavailable', small))

        charts_table = RL_Table([chart_items], colWidths=[180, 180, 180])
        charts_table.setStyle(RL_TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('BOX', (0,0), (-1,-1), 0.25, RL_colors.HexColor('#E6EEF8')),
            ('BACKGROUND', (0,0), (-1,-1), RL_colors.white),
        ]))
        story.append(charts_table)
        story.append(RL_Spacer(1, 12))

        # Detailed transactions table (expenses + investments)
        story.append(RL_Paragraph('Transactions - Expenses', heading))
        expense_rows = [['Date','Category','Description','Amount']]
        expenses_all = Expense.objects.filter(user=request.user, month_year=current_month).order_by('-date')
        for e in expenses_all:
            expense_rows.append([e.date.strftime('%Y-%m-%d'), e.category, e.description or '', f"{pdf_currency} {float(e.amount):,.2f}"])
        if len(expense_rows) == 1:
            story.append(RL_Paragraph('No expenses for this month.', small))
        else:
            et = RL_Table(expense_rows, colWidths=[70,110,230,90])
            et.setStyle(RL_TableStyle([
                ('BACKGROUND', (0,0), (-1,0), RL_colors.HexColor('#eeeeee')),
                ('GRID', (0,0), (-1,-1), 0.25, RL_colors.grey),
                ('FONTSIZE', (0,0), (-1,-1), 8),
            ]))
            story.append(et)
        story.append(RL_Spacer(1, 12))

        story.append(RL_Paragraph('Transactions - Investments', heading))
        invest_rows = [['Date','Type','Description','Amount']]
        investments_all = Investment.objects.filter(user=request.user, month_year=current_month).order_by('-date')
        for iv in investments_all:
            invest_rows.append([iv.date.strftime('%Y-%m-%d'), iv.investment_type, iv.description or '', f"{pdf_currency} {float(iv.amount):,.2f}"])
        if len(invest_rows) == 1:
            story.append(RL_Paragraph('No investments for this month.', small))
        else:
            it = RL_Table(invest_rows, colWidths=[70,110,230,90])
            it.setStyle(RL_TableStyle([
                ('BACKGROUND', (0,0), (-1,0), RL_colors.HexColor('#eeeeee')),
                ('GRID', (0,0), (-1,-1), 0.25, RL_colors.grey),
                ('FONTSIZE', (0,0), (-1,-1), 8),
            ]))
            story.append(it)
        story.append(RL_Spacer(1, 12))

        # Budgets table
        story.append(RL_Paragraph('Budgets - Allocated vs Actual', heading))
        budgets_rows = [['Category','Allocated','Actual','Remaining','% Used']]
        for b in Budget.objects.filter(user=request.user, month_year=current_month):
            actual = Expense.objects.filter(user=request.user, category=b.category, month_year=b.month_year).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            remaining = float(b.allocated_amount - actual)
            percent = 0.0
            try:
                if b.allocated_amount > 0:
                    percent = float((actual / b.allocated_amount) * 100)
            except Exception:
                percent = 0.0
            budgets_rows.append([b.category, f"{pdf_currency} {float(b.allocated_amount):,.2f}", f"{pdf_currency} {float(actual):,.2f}", f"{pdf_currency} {remaining:,.2f}", f"{percent:.1f}%"])
        if len(budgets_rows) == 1:
            story.append(RL_Paragraph('No budgets set for this month.', small))
        else:
            bt = RL_Table(budgets_rows, colWidths=[120,90,90,90,70])
            bt.setStyle(RL_TableStyle([
                ('BACKGROUND', (0,0), (-1,0), RL_colors.HexColor('#eeeeee')),
                ('GRID', (0,0), (-1,-1), 0.25, RL_colors.grey),
                ('FONTSIZE', (0,0), (-1,-1), 8),
            ]))
            story.append(bt)
        story.append(RL_Spacer(1, 12))

        # Footer
        story.append(RL_Paragraph(f'Report Generated: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}', styles['Italic'] if 'Italic' in styles else normal))

        doc.build(story)

        # Create or update MonthlyReport entry pointing to the PDF
        monthly_report, created = MonthlyReport.objects.update_or_create(
            user=request.user,
            month_year=current_month,
            defaults={
                'total_income': total_income,
                'total_expenses': total_expenses,
                'total_investments': total_investments,
                'total_savings': total_savings,
                'pdf_file': pdf_path,
            }
        )

        return FileResponse(open(os.path.abspath(pdf_path), 'rb'), as_attachment=True, filename=os.path.basename(pdf_path))
    except Exception as e:
        # Fallback: write text file and inform user. Also include the traceback for debugging.
        tb = traceback.format_exc()
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"Spendly Monthly Report - {current_month}\n")
            f.write(f"User: {request.user.get_full_name() or request.user.username}\n")
            f.write(f"Email: {request.user.email}\n")
            f.write(f"Monthly Salary: {currency_symbol}{total_income:,.2f}\n")
            f.write(f"Total Expenses: {currency_symbol}{total_expenses:,.2f}\n")
            f.write(f"Total Investments: {currency_symbol}{total_investments:,.2f}\n")
            f.write(f"Total Savings: {currency_symbol}{total_savings:,.2f}\n")
            f.write(f"Report Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write('\n--- DEBUG TRACEBACK ---\n')
            f.write(tb)
        messages.error(request, f'PDF generation failed, fallback text report saved. Error: {e}')
        return FileResponse(open(os.path.abspath(txt_path), 'rb'), as_attachment=True, filename=os.path.basename(txt_path))