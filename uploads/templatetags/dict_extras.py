from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Look up ``key`` in ``dictionary`` from within a Django template.

    Templates can't do ``row[col]`` when ``col`` is a variable, so this
    filter makes ``{{ row|get_item:col }}`` work for the job-detail
    data preview table.
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key, "")
    return ""