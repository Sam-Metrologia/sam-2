from django import template

register = template.Library()


@register.filter
def cop(value):
    """
    Formatea un número como precio colombiano con puntos de miles.
    Ej: 200000 → $200.000 | 2000000 → $2.000.000
    """
    try:
        entero = int(value)
        return f"${entero:,}".replace(",", ".")
    except (ValueError, TypeError):
        return value

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

@register.filter
def abs_value(value):
    """Retorna el valor absoluto de un número"""
    try:
        return abs(int(value))
    except (ValueError, TypeError):
        return value