"""oc_search URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.conf.urls import include
from search.views import SearchView, RecordView, ExportView, MoreLikeThisView, HomeView, DefaultView


urlpatterns = [
    path('search/admin/', admin.site.urls),
]

# Enable Rosetta for translation
if 'rosetta' in settings.INSTALLED_APPS:
    import rosetta
    urlpatterns += [
        path('search/rosetta/', include('rosetta.urls'))
    ]

if settings.SEARCH_LANG_USE_PATH:
    urlpatterns += [
        path('', DefaultView.as_view(), name="HomePage"),
        path('search/', DefaultView.as_view(), name="HomePage"),
        path('search/<str:lang>/', HomeView.as_view(), name="HomePage"),
        path('search/<str:lang>/<str:search_type>/', SearchView.as_view(), name="SearchForm"),
        path('rechercher/<str:lang>/<str:search_type>/', SearchView.as_view(), name="SearchForm"),
        path('search/<str:lang>/<str:search_type>/record/<str:record_id>', RecordView.as_view(), name='RecordForm'),
        path('search/<str:lang>/<str:search_type>/export/', ExportView.as_view(), name='ExportForm'),
        path('search/<str:lang>/<str:search_type>/similar/<str:record_id>', MoreLikeThisView.as_view(), name='MLTForm'),
        path('search/<str:lang>/<str:search_type>/similaire/<str:record_id>', MoreLikeThisView.as_view(), name='MLTForm'),
    ]
else:
    urlpatterns += [
        path('search/', DefaultView.as_view(), name="HomePage"),
        path('search/<str:search_type>/', SearchView.as_view(), name="SearchForm"),
        path('search/record/<str:search_type>/<str:record_id>', name='RecordForm'),
        path('search/<str:search_type>/record/<str:record_id>', RecordView.as_view(), name='RecordForm'),
        path('search/<str:search_type>/export/', ExportView.as_view(), name='RecordForm'),
        path('search/<str:search_type>/similar/<str:record_id>', MoreLikeThisView.as_view(), name='MLTForm'),
        path('search/<str:search_type>/similaire/<str:record_id>', MoreLikeThisView.as_view(), name='MLTForm'),
    ]
