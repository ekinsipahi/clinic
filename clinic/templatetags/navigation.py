from django import template

register = template.Library()

@register.simple_tag
def whyus_urls():
    return {
        "tr": "/neden-biz/",
        "en": "/en/why-us/",
        "de": "/de/warum-wir/",
        "nl": "/nl/waarom-wij/",
    }