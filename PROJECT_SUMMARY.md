# Spendly — Project Summary

This is an automated project memo created to "memorize" key parts of the Spendly project so you (and I) can quickly recall structure, important files, data shapes, and run instructions.

## Short description

Spendly is a Django-based personal finance app (Django 5.2.7) that provides expense tracking, investment monitoring, monthly budgets, analytics, and monthly report generation. The main app is `budget` and the Django project package is `spendly_project`.

## Key files and purpose

- `manage.py` — project CLI entry (migrations, runserver, etc.).
- `spendly_project/settings.py` — settings (DEBUG=True, sqlite3 DB at `db.sqlite3`).
- `spendly_project/urls.py` — main urlconf (includes app routes).
- `budget/models.py` — data models (see Models section).
- `budget/views.py` — view functions (dashboard, add/edit/delete expense/investment, analytics, reset month/report generation).
- `budget/urls.py` — app URL patterns (authentication, dashboard, expenses, investments, budget, analytics, reset-month).
- `budget/forms.py` — Django forms used by views (not detailed here; referenced by views).
- `budget/templates/budget/` — HTML templates (list below).
- `media/` — uploads and generated reports (profile pictures under `media/profile_pics/`, reports under `media/reports/`).
- `requirements.txt` — Python dependencies (install before running).
- `README.md` — human-facing project README and quick-run instructions.

## Templates (found in `budget/templates/budget/`)

Files present in the template folder (copied from workspace view):
- `add_expense.html`
- `add_investment.html`
- `analytics.html`
- `base.html`
- `budget_management.html`
- `dashboard.html`
- `delete_expense.html`
- `delete_investment.html`
- `edit_expense.html`
- `edit_investment.html`
- `expense_list.html`
- `home.html`
- `investment_list.html`
- `login.html`
- `profile.html`
- `register.html`
- `reset_month.html`

## Models (high-level summaries from `budget/models.py`)

- `UserProfile`
  - OneToOne -> User
  - profile_picture (ImageField)
  - full_name, monthly_salary (DecimalField), phone_number, date_of_birth, address
  - created_at, updated_at

- `Expense`
  - ForeignKey -> User
  - category (choices like Food, Transport, Bills, ...)
  - amount (DecimalField), description (TextField), date (DateTimeField)
  - month_year (string YYYY-MM), created_at
  - `save()` ensures `month_year` is set from `date`

- `Investment`
  - ForeignKey -> User
  - investment_type (choices: Stocks, Mutual Funds, Real Estate, Savings, Crypto, ...)
  - amount, description, date, month_year, created_at
  - `save()` ensures `month_year` is set

- `Budget`
  - ForeignKey -> User
  - category (choices), allocated_amount (DecimalField), month_year
  - unique_together: (user, category, month_year)
  - helper methods: `get_spent_amount()`, `get_remaining_budget()`, `get_percentage_used()`

- `MonthlyReport`
  - ForeignKey -> User
  - month_year, total_income, total_expenses, total_investments, total_savings
  - pdf_file (FileField -> `media/reports/`)
  - unique_together: (user, month_year)

## Main views & behaviors (from `budget/views.py`)

- Authentication: `register_view`, `login_view`, `logout_view`.
- `dashboard` — financial overview using `UserProfile.monthly_salary`, Expense and Investment aggregates for current month, expense breakdown, budget vs actual, recent transactions, and spending trend.
- Profile management: `profile_view` (uses `UserProfileForm`).
- Expense CRUD: `add_expense`, `expense_list` (filtering, pagination), `edit_expense`, `delete_expense`.
- Investment CRUD: `add_investment`, `investment_list` (filters, pagination), `edit_investment`, `delete_investment`.
- Budget management: `budget_management` — create/update budgets per category for current month.
- Analytics: `analytics` — 12-month data series, breakdowns, and savings rate.
- Reset month / report generation: `reset_month` — generates a report file (PDF generation via ReportLab is currently disabled; code writes a `.txt` alternative) and creates a `MonthlyReport` entry.

Notes/observations from the code:
- The app currently writes a `.txt` report in `media/reports/` because ReportLab is commented out / temporarily disabled.
- Pagination uses 20 items per page for lists.
- Views rely on several forms from `budget/forms.py` (`ExpenseForm`, `InvestmentForm`, `UserRegistrationForm`, `UserProfileForm`, `ExpenseFilterForm`, etc.).

## URL endpoints (from `budget/urls.py`)

- `/` -> `home` (if authenticated redirects to `/dashboard/`)
- `/register/`, `/login/`, `/logout/`
- `/dashboard/`
- `/profile/`
- `/expenses/add/`, `/expenses/`, `/expenses/edit/<id>/`, `/expenses/delete/<id>/`
- `/investments/add/`, `/investments/`, `/investments/edit/<id>/`, `/investments/delete/<id>/`
- `/budget/` (budget management)
- `/analytics/`
- `/reset-month/` (generate report / reset month)

## Settings highlights

- `DEBUG = True` (development)
- Database: SQLite at project root `db.sqlite3`.
- `MEDIA`/`STATIC` behavior: `STATIC_URL = 'static/'`. Media storage used in code references `media/reports` and `media/profile_pics`.
- `INSTALLED_APPS` in `settings.py` currently lists only Django built-ins in the copy read; ensure `budget` is present in `INSTALLED_APPS` in your local settings if not already.

## How to run (quick)

1. Create & activate a virtualenv (Windows PowerShell):

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Run migrations (if needed):

```powershell
python manage.py migrate
```

4. Create a superuser (optional):

```powershell
python manage.py createsuperuser
```

5. Start server:

```powershell
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

## Known TODOs & suggestions

- Re-enable PDF generation (ReportLab code is present but commented out). Fix imports and ensure `reportlab` is in `requirements.txt` if you want real PDFs.
- Add unit tests for key model methods (`Budget.get_spent_amount`, `get_remaining_budget`) and view endpoints.
- Confirm `budget` appears in `INSTALLED_APPS` in `settings.py` — the read copy we captured only included Django defaults.
- Consider moving secret keys and DEBUG toggles into environment variables for production readiness.

## Files created/edited by this memo

- `PROJECT_SUMMARY.md` — (this file) a concise snapshot of the project structure and run notes so the project can be quickly recalled.

## Next steps (manual or I can do it for you)

- I can update `settings.py` to ensure `budget` is in `INSTALLED_APPS` if missing.
- I can re-enable PDF generation and add `reportlab` to `requirements.txt` and create a minimal test to validate report creation.
- I can add a few unit tests for model helpers and run them.

---

If you want, I can now:
- (A) add `budget` to `INSTALLED_APPS` if it's missing and run quick checks, or
- (B) re-enable ReportLab PDF generation and add tests, or
- (C) scan `requirements.txt` and ensure dependencies are consistent.

Tell me which of these (or something else) you'd like next and I'll act on it.