from django.conf import settings


def lang_direction(request):
    """
    Sets lang_direction context variable to whether the language is RTL or LTR
    """
    if lang_direction.rtl_langs is None:
        lang_direction.rtl_langs = getattr(settings, "RTL_LANGUAGES", set())

    return {"lang_direction": "rtl" if request.LANGUAGE_CODE in lang_direction.rtl_langs else "ltr"}


lang_direction.rtl_langs = None
