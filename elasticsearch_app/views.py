import logging
import re

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from elasticsearch import Elasticsearch
import elasticsearch_dsl
from guardian.shortcuts import get_objects_for_user
from six import iteritems

from geonode.base.models import TopicCategory

logger = logging.getLogger(__name__)


def empty_page(request):
    return HttpResponse('')


def edsl_base_init(self, _expand__to_dot=False, **params):
    # elasticsearch_dsl overwrites any double underscores with a .
    # this changes the default to not overwrite

    self._params = {}
    for pname, pvalue in iteritems(params):
        if '__' in pname and _expand__to_dot:
            pname = pname.replace('__', '.')
        self._setattr(pname, pvalue)


elasticsearch_dsl.utils.DslBase.__init__ = edsl_base_init
Q = elasticsearch_dsl.query.Q


def get_unified_search_result_objects(hits):
    # Reformat objects for use in the results.
    # The ES objects need some reformatting
    # in order to be useful for output to the client.

    objects = []
    for hit in hits:
        try:
            source = hit.get('_source')
        except:  # noqa -no specific exception
            pass
        result = {}
        result['index'] = hit.get('_index', None)
        for key, value in source.iteritems():
            if key == 'bbox':
                result['bbox_left'] = value[0]
                result['bbox_bottom'] = value[1]
                result['bbox_right'] = value[2]
                result['bbox_top'] = value[3]
                # flake8 F841
                # bbox_str = ','.join(map(str, value))
            else:
                result[key] = source.get(key, None)
        objects.append(result)

    return objects


def get_facet_lookup():
    categories = TopicCategory.objects.all()
    category_lookup = {}
    for c in categories:
        if c.is_choice:
            category_lookup[c.identifier] = {
                'display': c.description,
                'icon': c.fa_class
            }

    facet_lookups = {
        'category': category_lookup,
        'references.scheme': {
            'OGC:WMS': {'display': 'WMS'},
            'OGC:WFS': {'display': 'WFS'},
            'OGC:WCS': {'display': 'WCS'},
            'OGC:KML': {'display': 'KML'},
            'ESRI:ArcGIS:MapServer': {'display': 'MapServer'},
            'ESRI:ArcGIS:ImageServer': {'display': 'ImageServer'}
        }
    }

    return facet_lookups


def get_facet_settings():
    additional_facets = getattr(settings, 'ADDITIONAL_FACETS', {})

    # Allows settings that can be used by a client for display of the facets
    # 'open' is used by exchange client side to determine if a facet menu shows
    # up open or closed by default
    # flake8 F841
    # default_facet_settings = {'open': False, 'show': True}
    facet_settings = {
        'category': {'open': True, 'show': True},
        'source_host': {'open': True, 'display': 'Host'},
        'owner__username': {'open': True, 'display': 'Owner'},
        'type': {'open': True, 'display': 'Type'},
        'subtype': {'open': True, 'display': 'Data Type'},
        'keywords': {'show': True},
        'references.scheme': {'show': True, 'display': 'Service Type'}
    }

    if additional_facets:
        facet_settings.update(additional_facets)

    return facet_settings


def get_base_query(search):
    '''
    Build base query
    The base query only includes the overall types of documents to search.
    This provides the overall counts and all fields for faceting
    '''

    # only show documents, layers, stories, and maps
    q = Q({"match": {"type": "layer"}}) | Q(
        {"match": {"type": "document"}}) | Q(
        {"match": {"type": "map"}}) | Q(
        {"match": {"type": "user"}}) | Q(
        {"match": {"type": "group"}})

    return search.query(q)


def apply_base_filter(request, search):
    '''
    Filter results based on which objects geonode allows access to.
    '''

    if not settings.SKIP_PERMS_FILTER:
        # Get the list of objects the user has access to
        filter_set = get_objects_for_user(
            request.user,
            'base.view_resourcebase'
        )

        # Various resources do not have is_published,
        # which end up affecting results
        # if settings.RESOURCE_PUBLISHING:
        # filter_set = filter_set.filter(is_published=True)

        filter_set_ids = map(str, filter_set.values_list('id', flat=True))
        if len(filter_set_ids) > 0:
            search = search.filter(Q('terms', id=filter_set_ids))

        return search


def get_facet_fields():
    # This configuration controls what fields will be added to faceted search
    # there is some special exception code later that combines the subtype
    # search and facet with type
    additional_facets = getattr(settings, 'ADDITIONAL_FACETS', {})

    facet_fields = [
        'type',
        'subtype',
        'owner__username',
        'keywords',
        'category',
        'source_host',
        'references.scheme'
    ]

    if additional_facets:
        facet_fields.extend(additional_facets.keys())

    return facet_fields


def get_facet_filter(parameters):
    # add filters to facet_filters to be used *after* initial overall search
    facet_filters = []
    for fn in get_facet_fields():
        # if there is a filter set in the parameters for this facet
        # add to the filters
        fp = parameters.getlist(fn)
        if not fp:
            fp = parameters.getlist("{}__in".format(fn))
        if fp:
            fq = Q({'terms': {fn: fp}})
            facet_filters.append(fq)

    return facet_filters


def get_facet_results(aggregations, parameters):
    facet_results = {}
    facet_lookups = get_facet_lookup()
    facet_settings = get_facet_settings()

    for k in aggregations.to_dict():
        buckets = aggregations[k]['buckets']
        if len(buckets) > 0:
            lookup = None
            if k in facet_lookups:
                lookup = facet_lookups[k]
            fsettings = facet_settings['category'].copy()
            fsettings['display'] = k
            # Default display to the id of the facet in case none is set
            if k in facet_settings:
                fsettings.update(facet_settings[k])
            if parameters.getlist(k):
                # Make sure list starts open when a filter is set
                fsettings['open'] = True
            facet_results[k] = {'settings': fsettings, 'facets': {}}

            for bucket in buckets:
                bucket_key = bucket.key
                if bucket_key != '':
                    bucket_count = bucket.doc_count
                    bucket_dict = {
                        'global_count': bucket_count,
                        'count': 0,
                        'display': bucket.key
                    }
                    if lookup:
                        if bucket_key in lookup:
                            bucket_dict.update(lookup[bucket_key])
                    facet_results[k]['facets'][bucket_key] = bucket_dict

    return facet_results


def get_main_query(search, query):
    # Set base fields to search
    fields = [
        'username',
        'first_name',
        'last_name',
        'organization',
        'description',
        'description.english',
        'description.pattern',
        'abstract',
        'abstract.english',
        'abstract.pattern',
        'category.text',
        'category.english',
        'category__gn_description',
        'keywords.text',
        'keywords.english',
        'layer_identifier',
        'layer_originator',
        'owner__first_name',
        'owner__last_name',
        'owner__username.text',
        'title_alternate',
        'title_alternate.english',
        'title_alternate.pattern',
        'source_host.text',
        'source',
        'subtype.text',
        'subtype.pattern',
        'supplemental_information',
        'title',
        'title.pattern',
        'title.english',
        'typename',
        'type.text',
        'type.english',
        'references.scheme.text',
        'references.scheme.pattern'
    ]

    # Build main query to search in fields[]
    # Filter by Query Params
    if query:
        query = re.sub(":\s+", ":", query)

        if query.startswith('"') or query.startswith('\''):
            # Match exact phrase
            phrase = query.replace('"', '')
            search = search.query(
                "multi_match",
                type='phrase_prefix',
                query=phrase,
                fields=fields
            )
        else:
            word_query = None
            words = [w for w in query.split() if w]

            for i, search_word in enumerate(words):
                search_fields = fields

                if ":" in search_word:
                    search_fields, search_word = search_word.split(':')
                    search_fields = [search_fields]

                if i == 0:
                    word_query = Q(
                        "multi_match",
                        type='phrase_prefix',
                        query=search_word,
                        fields=search_fields
                    )
                elif search_word.upper() in ["AND", "OR", "NOT", "-", "+"]:
                    pass
                elif words[i - 1].upper() == "OR":
                    word_query = word_query | Q(
                        "multi_match",
                        type='phrase_prefix',
                        query=search_word,
                        fields=search_fields
                    )
                elif words[i - 1].upper() in ["NOT", "-"]:
                    search = search.exclude(
                        "multi_match",
                        type='phrase_prefix',
                        query=search_word,
                        fields=search_fields
                    )
                else:  # previous word AND this word
                    word_query = word_query & Q(
                        "multi_match",
                        type='phrase_prefix',
                        query=search_word,
                        fields=search_fields
                    )

            if word_query is not None:
                search = search.query(word_query)

    return search


def add_bbox_search(search, bbox):
    # Add in Bounding Box filter
    if bbox:
        left, bottom, right, top = bbox.split(',')
        leftq = Q({'range': {'bbox_left': {'gte': float(left)}}})
        bottomq = Q({'range': {'bbox_bottom': {'gte': float(bottom)}}})
        rightq = Q({'range': {'bbox_right': {'lte': float(right)}}})
        topq = Q({'range': {'bbox_top': {'lte': float(top)}}})
        q = leftq & bottomq & rightq & topq
        search = search.query(q)

    return search


def add_temporal_search(search, parameters):
    # Add in Range Queries
    # Publication date range (start,end)
    date_range = parameters.get("date__range", None)
    date_end = parameters.get("date__lte", None)
    date_start = parameters.get("date__gte", None)
    if date_range is not None:
        date_start, date_end = date_range.split(',')

    # Time Extent range (start, end)
    time_range = parameters.get("extent__range", None)
    time_range_end = parameters.get("extent__lte", None)
    time_range_start = parameters.get("extent__gte", None)
    if time_range is not None:
        time_range_start, time_range_end = time_range.split(',')

    # Add range filters to the search
    if date_start:
        q = Q({'range': {'date': {'gte': date_start}}})
        search = search.query(q)

    if date_end:
        q = Q({'range': {'date': {'lte': date_end}}})
        search = search.query(q)

    if time_range_start:
        q = Q(
            {'range': {'temporal_extent_end': {'gte': time_range_start}}})
        search = search.query(q)

    if time_range_end:
        q = Q(
            {'range': {'temporal_extent_start': {'lte': time_range_end}}})
        search = search.query(q)

    return search


def apply_sort(search, sort):
    if sort.lower() == "-date":
        search = search.sort(
            {"date": {
                "order": "desc",
                "missing": "_last",
                "unmapped_type": "date"
            }}
        )
    elif sort.lower() == "date":
        search = search.sort(
            {"date": {
                "order": "asc",
                "missing": "_last",
                "unmapped_type": "date"
            }}
        )
    elif sort.lower() == "title":
        search = search.sort('title_sortable')
    elif sort.lower() == "-title":
        search = search.sort('-title_sortable')
    elif sort.lower() == "-popular_count":
        search = search.sort('-popular_count')
    else:
        search = search.sort(
            {"date": {
                "order": "desc",
                "missing": "_last",
                "unmapped_type": "date"
            }}
        )

    return search


def filter_by_resource_type(search, resource_type):
    # filter by resourcetype
    if resource_type == 'documents':
        search = search.query("match", type="document")
    elif resource_type == 'layers':
        search = search.query("match", type="layer")
    elif resource_type == 'maps':
        search = search.query("match", type="map")
    elif resource_type in ['profiles', 'profile', 'people']:
        search = search.query("match", type="user")
    elif resource_type == 'groups':
        search = search.query("match", type="group")
    else:
        # Always include filter for types to show up in
        # global search
        q = Q({"match": {"type": "layer"}}) | Q(
            {"match": {"type": "document"}}) | Q(
            {"match": {"type": "map"}})
        search = search.query(q)

    return search


def filter_results_by_facets(aggregations, facet_results):
    # get facets based on search criteria, add to overall facets
    for k in aggregations.to_dict():
        buckets = aggregations[k]['buckets']
        if len(buckets) > 0:
            for bucket in buckets:
                bkey = bucket.key
                count = bucket.doc_count
                try:
                    if count > 0:
                        facet_results[k]['facets'][bkey]['count'] = count
                except Exception as e:
                    facet_results['errors'] = "key: {}, bucket_key: {} \
                        , error: {}".format(k, bkey, e)

    # Remove Empty Facets
    for item in facet_results.keys():
        try:
            facets = facet_results[item]['facets']
            if sum(facets[prop]['count'] for prop in facets) == 0:
                del facet_results[item]
        except Exception as e:
            logger.warn(e)

    return facet_results


def elastic_search(request, resourcetype='base'):
    parameters = request.GET
    es = Elasticsearch(settings.ES_URL)

    # exclude the profile and group indexes.
    # They aren't being used, and cause issues with faceting
    indices = es.indices.get_alias("*").keys()
    exclude_indexes = []
    [indices.remove(i) for i in exclude_indexes if i in indices]

    search = elasticsearch_dsl.Search(using=es, index=indices)
    # search = get_base_query(search)
    search = apply_base_filter(request, search)

    # Add facets to search
    for fn in get_facet_fields():
        search.aggs.bucket(
            fn,
            'terms',
            field=fn,
            order={"_count": "desc"},
            size=parameters.get("nfacets", 15)
        )

    # run search only filtered by what a particular user is able to see
    # this makes sure to get every item that is possible in the facets
    # in order for a UI to build the choices
    overall_results = search[0:0].execute()
    facet_results = get_facet_results(overall_results.aggregations, parameters)

    search = filter_by_resource_type(search, resourcetype)
    search = get_main_query(search, parameters.get('q', None))

    # Add the facet queries to the main search
    for fq in get_facet_filter(parameters):
        search = search.query(fq)

    # Add in has_time filter if set
    if parameters.get("has_time", False):
        search = search.query(Q({'match': {'has_time': True}}))

    search = add_bbox_search(search, parameters.get("extent", None))
    search = add_temporal_search(search, parameters)
    search = apply_sort(search, parameters.get("order_by", "relevance"))

    limit = int(parameters.get('limit', settings.API_LIMIT_PER_PAGE))
    offset = int(parameters.get('offset', '0'))

    # Run the search using the offset and limit
    search = search[offset:offset + limit]
    results = search.execute()

    logger.debug('search: {}, results: {}'.format(search, results))

    filtered_facet_results = filter_results_by_facets(
        results.aggregations,
        facet_results
    )
    # Get results
    objects = get_unified_search_result_objects(results.hits.hits)

    object_list = {
        "meta": {
            "limit": limit,
            "next": None,
            "offset": offset,
            "previous": None,
            "total_count": results.hits.total,
            "facets": filtered_facet_results,
        },
        "objects": objects,
    }

    return JsonResponse(object_list)
