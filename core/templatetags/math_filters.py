from django import template

register = template.Library()

@register.filter
def div(value, arg):
    """
    Divides the value by the arg. Handles division by zero.
    Usage: {{ value|div:arg }}
    """
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0.0 # Return 0.0 or handle as appropriate for your application

@register.filter
def mul(value, arg):
    """
    Multiplies the value by the arg.
    Usage: {{ value|mul:arg }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0.0 # Return 0.0 or handle as appropriate for your application

@register.filter
def abs_value(value):
    """
    Returns the absolute value of a number.
    Usage: {{ value|abs_value }}
    """
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return 0.0 # Return 0.0 or handle as appropriate for your application