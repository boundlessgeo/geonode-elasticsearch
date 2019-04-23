from django.conf.urls import patterns, url
from elasticsearch_app.views import suggest_search, elastic_search

urlpatterns = patterns(
    '',
    url(r'^api/(?P<resourcetype>[^/]+)/search/$',
        elastic_search,
        name='elastic_search'),
    url(r'^autocomplete',
        suggest_search,
        name='autocomplete')
)
