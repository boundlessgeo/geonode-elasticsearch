# geonode-elasticsearch

This application serves as an interface to elasticsearch in geonode via elasticsearch-dsl. Additionally provides some management commands for an easier upgrade from django-haystack.

To use, add following to settings:

``` python
# elasticsearch-dsl settings
# Elasticsearch-dsl Backend Configuration. To enable,
# Set ES_SEARCH to True
# Run "python manage.py clear_haystack" (if upgrading from haystack)
# Run "python manage.py rebuild_index"
ES_SEARCH = strtobool(os.getenv('ES_SEARCH', 'False'))

if ES_SEARCH:
    INSTALLED_APPS = (
        'elasticsearch_app',
    ) + INSTALLED_APPS
    ES_URL = os.getenv('ES_URL', 'http://127.0.0.1:9200/')
    # Disable Haystack
    HAYSTACK_SEARCH = False
    # Avoid permissions prefiltering
    SKIP_PERMS_FILTER = False
    # Update facet counts from Haystack
    HAYSTACK_FACET_COUNTS = False
```

This app will provide a search api at /api/<resourcetype>/search/

search.py contains definitions for the elasticsearch indices as well as functions to convert django models into form to go into elasticsearch.

views.py contains all the logic for running the search and providing facets