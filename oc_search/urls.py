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
from search.views import SearchView, RecordView, ExportView, MoreLikeThisView, HomeView, DefaultView, ExportStatusView, DownloadSearchResultsView
from ramp.views import RampView


urlpatterns = [
    path('search/admin/', include('smuggler.urls')),  # before admin url patterns!
    path('search/admin/doc/', include('django.contrib.admindocs.urls')),
    path('search/admin/', admin.site.urls),
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
        path('search/<str:lang>/<str:search_type>/download/<str:task_id>', DownloadSearchResultsView.as_view(), name='DownloadForm'),
        path('rechercher/<str:lang>/<str:search_type>/telecharger/<str:task_id>', DownloadSearchResultsView.as_view(), name='DownloadForm'),
        path('search/<str:lang>/<str:search_type>/similar/<str:record_id>', MoreLikeThisView.as_view(), name='MLTForm'),
        path('search/<str:lang>/<str:search_type>/similaire/<str:record_id>', MoreLikeThisView.as_view(),
             name='MLTForm'),
        path('rechercher/<str:lang>/<str:search_type>/similaire/<str:record_id>', MoreLikeThisView.as_view(), name='MLTForm'),
        path('search/search-results/<str:lang>/<str:search_type>/<str:task_id>', ExportStatusView.as_view(), name='SearchResultsForm'),
        path('rechercher/rapport-de-recherche/<str:lang>/<str:search_type>/<str:task_id>', ExportStatusView.as_view(), name='SearchResultsForm'),
    ]
    if 'ramp' in settings.INSTALLED_APPS:
        urlpatterns += [
            path('openmap/<str:lang>/', RampView.as_view(), name='RampForm'),
            path('openmap/<str:lang>/<str:keys>', RampView.as_view(), name='RampForm'),
            path('carteouverte/<str:lang>/', RampView.as_view(), name='RampForm'),
            path('carteouverte/<str:lang>/<str:keys>', RampView.as_view(), name='RampForm'),
        ]
else:
    urlpatterns += [
        path(settings.SEARCH_HOST_PATH, DefaultView.as_view(), name="HomePage"),
        path(settings.SEARCH_HOST_PATH + '<str:search_type>/', SearchView.as_view(), name="SearchForm"),
        path(settings.SEARCH_HOST_PATH + 'record/<str:search_type>/<str:record_id>', RecordView.as_view(),
             name='RecordForm'),
        path(settings.SEARCH_HOST_PATH + '<str:search_type>/record/<str:record_id>', RecordView.as_view(),
             name='RecordForm'),
        path(settings.SEARCH_HOST_PATH + '<str:search_type>/export/', ExportView.as_view(), name='RecordForm'),
        path(settings.SEARCH_HOST_PATH + '<str:search_type>/download/<str:task_id>', DownloadSearchResultsView.as_view(), name='DownloadForm'),
        path(settings.SEARCH_HOST_PATH + '<str:search_type>/telecharger/<str:task_id>', DownloadSearchResultsView.as_view(), name='DownloadForm'),
        path(settings.SEARCH_HOST_PATH + '<str:search_type>/similar/<str:record_id>', MoreLikeThisView.as_view(),
             name='MLTForm'),
        path(settings.SEARCH_HOST_PATH + '<str:search_type>/similaire/<str:record_id>', MoreLikeThisView.as_view(),
             name='MLTForm'),
        path(settings.SEARCH_HOST_PATH + 'search-results/<str:lang>/<str:search_type>/<str:task_id>', ExportStatusView.as_view(),
             name='SearchResultsForm'),
        path(settings.SEARCH_HOST_PATH + 'rapport-de-recherche/<str:lang>/<str:search_type>/<str:task_id>', ExportStatusView.as_view(),
             name='SearchResultsForm'),
    ]
    if 'ramp' in settings.INSTALLED_APPS:
        urlpatterns += [
            path(settings.SEARCH_HOST_PATH + 'openmap/', RampView.as_view(), name='RampForm'),
            path(settings.SEARCH_HOST_PATH + 'openmap/<str:keys>', RampView.as_view(), name='RampForm'),
            path(settings.SEARCH_HOST_PATH + 'carteouverte/', RampView.as_view(), name='RampForm'),
            path(settings.SEARCH_HOST_PATH + 'carteouverte/<str:keys>', RampView.as_view(), name='RampForm'),
        ]

