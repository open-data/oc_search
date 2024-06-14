from django.conf import settings
from urllib import parse


def search_path(search: str, lang: str, path: str = "") -> str:
    return_url = ""
    if settings.SEARCH_LANG_USE_PATH:
        if lang == 'fr':
            return_url = f"{settings.SEARCH_FR_HOSTNAME}/rechercher/fr/{search}{path}"
        else:
            return_url = f"{settings.SEARCH_EN_HOSTNAME}/search/en/{search}{path}"
    else:
        if lang == 'fr':
            return_url = parse.urljoin(settings.SEARCH_FR_HOSTNAME, settings.SEARCH_HOST_PATH, f'/{search}{path}')
        else:
            return_url = parse.urljoin(settings.SEARCH_EN_HOSTNAME, settings.SEARCH_HOST_PATH, f'{search}{path}')
    return return_url
