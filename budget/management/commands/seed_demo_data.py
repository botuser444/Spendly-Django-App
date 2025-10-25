from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import datetime
from budget.models import UserProfile, Expense, Investment, Budget, MonthlyReport


class Command(BaseCommand):
    help = 'Seed demo user and demo financial data (expenses, investments, budgets, reports)'

    def handle(self, *args, **options):
        now = timezone.now()
        username = 'demo'
        email = 'demo@example.com'
        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        if created:
            user.set_password('demo1234')
            user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.full_name = profile.full_name or 'Demo User'
        profile.monthly_salary = profile.monthly_salary or Decimal('5200.00')
        profile.save()

        categories = [c[0] for c in Expense.CATEGORY_CHOICES]
        inv_types = [c[0] for c in Investment.INVESTMENT_TYPE_CHOICES]

        # Create expenses for last 12 months
        expense_count = 0
        investment_count = 0
        budget_count = 0
        report_count = 0

        for m in range(12):
            # compute month start date
            month_date = datetime(now.year, now.month, 1)
            # shift months back
            month_index = month_date.month - m - 1
            year = month_date.year
            while month_index < 0:
                month_index += 12
                year -= 1

            d = datetime(year, month_index + 1, 15, 12, 0)
            month_str = d.strftime('%Y-%m')

            # create 5 expenses per month with deterministic values
            for i, cat in enumerate(categories[:5]):
                amt = Decimal(str(50 + (i * 20) + (m * 5)))
                Expense.objects.create(
                    user=user,
                    category=cat,
                    amount=amt,
                    description=f'Demo {cat} expense for {month_str}',
                    date=timezone.make_aware(datetime(year, month_index + 1, 5 + i)),
                )
                expense_count += 1

            # create 2 investments every other month
            if m % 2 == 0:
                for j in range(2):
                    itype = inv_types[j % len(inv_types)]
                    amt = Decimal(str(100 + (j * 150) + (m * 10)))
                    Investment.objects.create(
                        user=user,
                        investment_type=itype,
                        amount=amt,
                        description=f'Demo {itype} investment for {month_str}',
                        date=timezone.make_aware(datetime(year, month_index + 1, 10 + j)),
                    )
                    investment_count += 1

            # create budgets for current month only
            if m == 0:
                for cat in categories[:6]:
                    Budget.objects.update_or_create(
                        user=user,
                        category=cat,
                        month_year=month_str,
                        defaults={'allocated_amount': Decimal('500.00')},
                    )
                    budget_count += 1

            # create monthly report entry for each month
            from django.db.models import Sum
            total_expenses_val = Expense.objects.filter(user=user, month_year=month_str).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            total_investments_val = Investment.objects.filter(user=user, month_year=month_str).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            MonthlyReport.objects.update_or_create(
                user=user,
                month_year=month_str,
                defaults={
                    'total_income': profile.monthly_salary,
                    'total_expenses': total_expenses_val,
                    'total_investments': total_investments_val,
                    'total_savings': profile.monthly_salary - (total_expenses_val or Decimal('0.00')) - (total_investments_val or Decimal('0.00')),
                }
            )
            report_count += 1

        self.stdout.write(self.style.SUCCESS(f'User: {user.username} (created={created})'))
        self.stdout.write(self.style.SUCCESS(f'Profile salary: {profile.monthly_salary}'))
        self.stdout.write(self.style.SUCCESS(f'Expenses created (approx): {expense_count}'))
        self.stdout.write(self.style.SUCCESS(f'Investments created (approx): {investment_count}'))
        self.stdout.write(self.style.SUCCESS(f'Budgets set for current month: {budget_count}'))
        self.stdout.write(self.style.SUCCESS(f'Monthly reports entries ensured: {report_count}'))
