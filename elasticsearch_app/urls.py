from django.conf.urls import patterns, url
from elasticsearch_app import views

urlpatterns = patterns(
    '',
    url(r'^api/(?P<resourcetype>[^/]+)/search/$',
        views.elastic_search,
        name='elastic_search'),
    url(r'^autocomplete/groups',
        views.suggest_search_groups,
        name='autocomplete_groups'),
    url(r'^autocomplete/people',
        views.suggest_search_people,
        name='autocomplete_people'),
    url(r'^autocomplete',
        views.suggest_search,
        name='autocomplete')
)
