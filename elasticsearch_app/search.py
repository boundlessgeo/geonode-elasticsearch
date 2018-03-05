from elasticsearch_dsl import (
    DocType,
    Integer,
    Keyword,
    Boolean,
    Date,
    Float,
    Text,
    Field,
    connections,
    field,
    analyzer
)
from django.conf import settings
from geonode.layers.models import Layer
from geonode.maps.models import Map
from geonode.documents.models import Document
from guardian.shortcuts import get_objects_for_user
from avatar.templatetags.avatar_tags import avatar_url

connections.create_connection(hosts=[settings.ES_URL])

pattern_analyzer = analyzer(
  'pattern_analyzer',
  type='pattern',
  pattern="\\W|_",
  lowercase=True
)

class LayerIndex(DocType):
    id = Integer()
    abstract = Text(
        fields={
            'pattern': field.Text(analyzer=pattern_analyzer),
            'english': field.Text(analyzer='english')
        }
    )
    category__gn_description = Text()
    csw_type = Keyword()
    csw_wkt_geometry = Keyword()
    detail_url = Keyword()
    owner__username = Keyword(
        fields={
            'text': field.Text()
        }
    )
    owner__first_name = Text()
    owner__last_name = Text()
    is_published = Boolean()
    featured = Boolean()
    popular_count = Integer()
    share_count = Integer()
    rating = Integer()
    srid = Keyword()
    supplemental_information = Text()
    source_host = Keyword(
        fields={
            'text': field.Text()
        }
    )
    thumbnail_url = Keyword()
    uuid = Keyword()
    title = Text(
        fields={
            'pattern': field.Text(analyzer=pattern_analyzer),
            'english': field.Text(analyzer='english')
        }
    )
    date = Date()
    type = Keyword(
        fields={
            'text': field.Text(),
            'english': field.Text(analyzer='english')
        }
    )
    subtype = Keyword(
        fields={
            'text': field.Text()
        }
    )
    typename = Keyword()
    title_sortable = Keyword()
    category = Keyword(
        fields={
            'text': field.Text(),
            'english': field.Text(analyzer='english')
        }
    )
    bbox_left = Float()
    bbox_right = Float()
    bbox_bottom = Float()
    bbox_top = Float()
    temporal_extent_start = Date()
    temporal_extent_end = Date()
    keywords = Keyword(
        fields={
            'text': field.Text(),
            'english': field.Text(analyzer='english')
        }
    )
    regions = Keyword(
        fields={
            'text': field.Text(),
            'english': field.Text(analyzer='english')
        }
    )
    references = Field(
        properties={
            'url': Text(),
            'name': Keyword(
                fields={
                    'text': field.Text()
                }
            ),
            'scheme': Keyword(
                fields={
                    'text': field.Text(),
                    'pattern': field.Text(analyzer=pattern_analyzer)
                }
            )
        }
    )
    num_ratings = Integer()
    num_comments = Integer()
    geogig_link = Keyword()
    has_time = Boolean()

    class Meta:
        index = 'layer-index'


class MapIndex(DocType):
    id = Integer()
    abstract = Text(
        fields={
            'pattern': field.Text(analyzer=pattern_analyzer),
            'english': field.Text(analyzer='english')
        }
    )
    category__gn_description = Text()
    csw_type = Keyword()
    csw_wkt_geometry = Keyword()
    detail_url = Keyword()
    owner__username = Keyword(
        fields={
            'text': field.Text()
        }
    )
    popular_count = Integer()
    share_count = Integer()
    rating = Integer()
    srid = Keyword()
    supplemental_information = Text()
    thumbnail_url = Keyword()
    uuid = Keyword()
    title = Text(
        fields={
            'pattern': field.Text(analyzer=pattern_analyzer),
            'english': field.Text(analyzer='english')
        }
    )
    date = Date()
    type = Keyword(
        fields={
            'text': field.Text(),
            'english': field.Text(analyzer='english')
        }
    )
    title_sortable = Keyword()
    category = Keyword(
        fields={
            'text': field.Text(),
            'english': field.Text(analyzer='english')
        }
    )
    bbox_left = Float()
    bbox_right = Float()
    bbox_bottom = Float()
    bbox_top = Float()
    temporal_extent_start = Date()
    temporal_extent_end = Date()
    keywords = Keyword(
        fields={
            'text': field.Text(),
            'english': field.Text(analyzer='english')
        }
    )
    regions = Keyword(
        fields={
            'text': field.Text(),
            'english': field.Text(analyzer='english')
        }
    )
    num_ratings = Integer()
    num_comments = Integer()

    class Meta:
        index = 'map-index'


class DocumentIndex(DocType):
    id = Integer()
    abstract = Text(
        fields={
            'pattern': field.Text(analyzer=pattern_analyzer),
            'english': field.Text(analyzer='english')
        }
    )
    category__gn_description = Text()
    csw_type = Keyword()
    csw_wkt_geometry = Keyword()
    detail_url = Keyword()
    owner__username = Keyword(
        fields={
            'text': field.Text()
        }
    )
    popular_count = Integer()
    share_count = Integer()
    rating = Integer()
    srid = Keyword()
    supplemental_information = Text()
    thumbnail_url = Keyword()
    uuid = Keyword()
    title = Text(
        fields={
            'pattern': field.Text(analyzer=pattern_analyzer),
            'english': field.Text(analyzer='english')
        }
    )
    date = Date()
    type = Keyword(
        fields={
            'text': field.Text(),
            'english': field.Text(analyzer='english')
        }
    )
    title_sortable = Keyword()
    category = Keyword(
        fields={
            'text': field.Text(),
            'english': field.Text(analyzer='english')
        }
    )
    bbox_left = Float()
    bbox_right = Float()
    bbox_bottom = Float()
    bbox_top = Float()
    temporal_extent_start = Date()
    temporal_extent_end = Date()
    keywords = Keyword(
        fields={
            'text': field.Text(),
            'english': field.Text(analyzer='english')
        }
    )
    regions = Keyword(
        fields={
            'text': field.Text(),
            'english': field.Text(analyzer='english')
        }
    )
    num_ratings = Integer()
    num_comments = Integer()

    class Meta:
        index = 'document-index'


class ProfileIndex(DocType):
    id = Integer()
    username = Text()
    first_name = Text()
    last_name = Text()
    profile = Keyword()
    organization = Text()
    position = Keyword()
    type = Keyword(
        fields={
            'text': field.Text(),
            'english': field.Text(analyzer='english')
        }
    )
    avatar_100 = Text()
    layers_count = Integer()
    maps_count = Integer()
    documents_count = Integer()

    class Meta:
        index = 'profile-index'

def create_profile_index(profile):
    # calculate counts and avatar
    layers_count = get_objects_for_user(
        profile,
        'base.view_resourcebase'
    ).instance_of(Layer).count()

    maps_count = get_objects_for_user(
        profile,
        'base.view_resourcebase'
    ).instance_of(Map).count()

    documents_count = get_objects_for_user(
        profile,
        'base.view_resourcebase'
    ).instance_of(Document).count()

    avatar_100 = avatar_url(profile, 240)

    obj = ProfileIndex(
        meta={'id': profile.id},
        id=profile.id,
        username=profile.username,
        first_name=profile.first_name,
        last_name=profile.last_name,
        profile=profile.profile,
        organization=profile.organization,
        position=profile.position,
        type='user',
        avatar_100=avatar_100,
        layers_count=layers_count,
        maps_count=maps_count,
        documents_count=documents_count
    )
    obj.save()
    return obj.to_dict(include_meta=True)


class GroupIndex(DocType):
    id = Integer()
    title = Text(
        fields={
            'pattern': field.Text(analyzer=pattern_analyzer),
            'english': field.Text(analyzer='english')
        }
    )
    title_sortable = Keyword()
    description = Text()
    json = Text()
    type = Keyword(
        fields={
            'text': field.Text(),
            'english': field.Text(analyzer='english')
        }
    )

    class Meta:
        index = 'group-index'




