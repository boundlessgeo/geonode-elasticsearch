# encoding: utf-8

from __future__ import absolute_import, division, print_function, unicode_literals

from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch_app.utils import index_object

geonode_imported = True
try:
    from geonode.layers.models import Layer
    from geonode.maps.models import Map
    from geonode.documents.models import Document
    from geonode.people.models import Profile
    from geonode.groups.models import GroupProfile
    from elasticsearch_app.search import (
        LayerIndex,
        MapIndex,
        DocumentIndex,
        ProfileIndex,
        GroupIndex
    )
    geonode_imported = True
except ImportError:
    geonode_imported = False


class Command(BaseCommand):
    help = "Freshens the index for the given app(s)."

    def handle(self, **options):
        '''
        Removes any extraneous data not matched in Django data.
        Repopulates the indices in elastic with current Django data.
        '''
        es = Elasticsearch(settings.ES_URL)

        # Any indices added in search.py should be initialized here
        if geonode_imported:
            LayerIndex.init()
            MapIndex.init()
            DocumentIndex.init()
            ProfileIndex.init()
            GroupIndex.init()

        body = {
            'analysis': {
                'analyzer': 'snowball'
            }
        }
        es.indices.put_settings(body, index='', ignore=400)

        def remove_extraneous_elements(index, model, doctype):
            '''
            Removes any items that exist in a GeoNode index which
            no longer exist in Django
            :param index: The string name of the index in elasticsearch
            :param model: The Django/GeoNode model
            :param doctype: The doctype corresponding to the index
            :return:
            '''
            indexed_items = es.search(index=index)

            for item in indexed_items['hits']['hits']:
                model_id = item['_id']
                try:
                    model.objects.get(id=model_id)
                except ObjectDoesNotExist:
                    doctype.get(id=model_id).delete()

        # Any indices containing extraneous data should be removed here
        if geonode_imported:
            remove_extraneous_elements('layer-index', Layer, LayerIndex)
            remove_extraneous_elements('map-index', Map, MapIndex)
            remove_extraneous_elements('document-index', Document, DocumentIndex)
            remove_extraneous_elements('profile-index', Profile, ProfileIndex)
            remove_extraneous_elements('group-index', GroupProfile, GroupIndex)

        # Any indices added in search.py should be indexed here
        if geonode_imported:
            bulk(client=es,
                 actions=(index_object(layer, LayerIndex)
                          for layer in Layer.objects.all().iterator()))
            bulk(client=es,
                 actions=(index_object(map_obj, MapIndex)
                          for map_obj in Map.objects.all().iterator()))
            bulk(client=es,
                 actions=(index_object(document, DocumentIndex)
                          for document in Document.objects.all().iterator()))
            bulk(client=es,
                 actions=(index_object(profile, ProfileIndex)
                          for profile in Profile.objects.all().iterator()))
            bulk(client=es,
                 actions=(index_object(group, GroupIndex)
                          for group in GroupProfile.objects.all().iterator()))
