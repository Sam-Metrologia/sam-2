from django import template
from django.utils.safestring import mark_safe

register = template.Library()


# Tags HTML permitidos para contenido de términos y condiciones (texto legal)
_TERMINOS_ALLOWED_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "br", "hr",
    "strong", "b", "em", "i", "u", "s", "del", "ins",
    "ul", "ol", "li",
    "table", "thead", "tbody", "tr", "th", "td",
    "blockquote", "pre", "code",
    "a", "span", "div", "section", "article",
    "sup", "sub",
}

# Atributos permitidos por tag (scripts y on* quedan fuera)
_TERMINOS_ALLOWED_ATTRS = {
    "a": {"href", "title", "target"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan", "scope"},
    "div": {"class"},
    "p": {"class"},
    "span": {"class"},
    "h1": {"class"}, "h2": {"class"}, "h3": {"class"},
    "h4": {"class"}, "h5": {"class"}, "h6": {"class"},
    "table": {"class"},
    "ul": {"class"}, "ol": {"class"}, "li": {"class"},
}


@register.filter
def sanitize_html(value):
    """
    Sanitiza HTML manteniendo etiquetas estructurales seguras pero eliminando
    <script>, event handlers (on*) y atributos peligrosos (javascript: hrefs).
    Usar en lugar de |safe para contenido HTML almacenado en BD.
    """
    if not value:
        return ""
    try:
        import nh3
        cleaned = nh3.clean(
            str(value),
            tags=_TERMINOS_ALLOWED_TAGS,
            attributes=_TERMINOS_ALLOWED_ATTRS,
            link_rel=None,  # no añadir rel="noopener" automático
        )
        return mark_safe(cleaned)
    except ImportError:
        # Si nh3 no está disponible, no renderizar HTML sin sanitizar
        from django.utils.html import escape
        return escape(str(value))


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