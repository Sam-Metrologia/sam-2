from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """Multiplica value por arg"""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def min_value(value, arg):
    """Retorna el menor valor entre value y arg"""
    try:
        return min(int(value), int(arg))
    except (ValueError, TypeError):
        return value

@register.filter
def make_list(value):
    """Convierte un número en una lista de números del 1 al value"""
    try:
        return list(range(1, int(value) + 1))
    except (ValueError, TypeError):
        return []

@register.filter
def add(value, arg):
    """Suma arg a value"""
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        return value