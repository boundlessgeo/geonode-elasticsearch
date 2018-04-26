from django.conf.urls import patterns, url
from elasticsearch_app.views import empty_page, elastic_search

urlpatterns = patterns(
    '',
    url(r'^api/(?P<resourcetype>[^/]+)/search/$',
        elastic_search,
        name='elastic_search'),
    url(r'^autocomplete',
        empty_page,
        name='autocomplete_override')
)
