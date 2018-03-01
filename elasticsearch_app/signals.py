from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from elasticsearch_app.utils import index_object

geonode_imported = True
try:
    from geonode.layers.models import Layer
    from geonode.maps.models import Map
    from geonode.documents.models import Document
    from geonode.people.models import Profile
    from geonode.groups.models import GroupProfile
    from geonode.services.models import Service
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

# To extend this app in your project, add
# import statements for the models you need from your
# project here



if geonode_imported:
    @receiver(post_save, sender=Layer)
    def layer_index_post(sender, instance, **kwargs):
        index_object(instance, LayerIndex)

    @receiver(post_save, sender=Service)
    def service_post_save(sender, **kwargs):
        service, created = kwargs["instance"], kwargs["created"]
        if not created:
            for instance in service.layer_set.all():
                index_object(instance, LayerIndex)    
        
    @receiver(post_delete, sender=Layer)
    def layer_index_delete(sender, instance, **kwargs):
        index_to_remove = LayerIndex.get(instance.id)
        if index_to_remove:
            index_to_remove.delete()


    @receiver(post_save, sender=Map)
    def map_index_post(sender, instance, **kwargs):
        index_object(instance, MapIndex)

    @receiver(post_delete, sender=Map)
    def map_index_delete(sender, instance, **kwargs):
        index_to_remove = MapIndex.get(instance.id)
        if index_to_remove:
            index_to_remove.delete()

    @receiver(post_save, sender=Document)
    def document_index_post(sender, instance, **kwargs):
        index_object(instance, DocumentIndex)

    @receiver(post_delete, sender=Document)
    def document_index_delete(sender, instance, **kwargs):
        index_to_remove = DocumentIndex.get(instance.id)
        if index_to_remove:
            index_to_remove.delete()

    @receiver(post_save, sender=Profile)
    def profile_index_post(sender, instance, **kwargs):
        index_object(instance, ProfileIndex)

    @receiver(post_delete, sender=Profile)
    def profile_index_delete(sender, instance, **kwargs):
        index_to_remove = ProfileIndex.get(instance.id)
        if index_to_remove:
            index_to_remove.delete()

    @receiver(post_save, sender=GroupProfile)
    def group_index_post(sender, instance, **kwargs):
        index_object(instance, GroupIndex)

    @receiver(post_delete, sender=GroupProfile)
    def group_index_delete(sender, instance, **kwargs):
        index_to_remove = GroupIndex.get(instance.id)
        if index_to_remove:
            index_to_remove.delete()

# To extend this app in your project, add a post_save
# signal for every model you wish to index.
# Be sure to update your model with any custom
# indexing for this model in the indexing() function.
# Otherwise, only the id will be indexed.
# <Model> = your model you wish to index
#
# @receiver(post_save, sender=<Model>)
# def <Model>_index_post(sender, instance, **kwargs):
#     index_object(instance)
