def currency(request):
    """Provide default currency symbol and code for templates.

    Returns:
        dict: currency_symbol (string), currency_code (string)
    """
    return {
        'currency_symbol': '₨',
        'currency_code': 'PKR',
    }
