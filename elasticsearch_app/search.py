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
from django.contrib.contenttypes.models import ContentType
from agon_ratings.models import OverallRating
from dialogos.models import Comment
from django.db.models import Avg
from django.core.exceptions import ObjectDoesNotExist
from geonode.services.enumerations import INDEXED
from six.moves.urllib_parse import urlparse

connections.create_connection(hosts=[settings.ES_URL])

pattern_analyzer = analyzer(
  'pattern_analyzer',
  type='pattern',
  pattern="\\W|_",
  lowercase=True
)


# Functions used to prepare columns for index
def float_or_none(val):
    try:
        return float(val)
    except TypeError:
        return None


def prepare_bbox(resource):
    minx = float_or_none(resource.bbox_x0)
    maxx = float_or_none(resource.bbox_x1)
    miny = float_or_none(resource.bbox_y0)
    maxy = float_or_none(resource.bbox_y1)
    if (minx and maxx and miny and maxy and
            minx < maxx and miny < maxy):
        return minx, maxx, miny, maxy
    return None, None, None, None


def prepare_rating(resource):
    ct = ContentType.objects.get_for_model(resource)
    try:
        rating = OverallRating.objects.filter(
            object_id=resource.pk,
            content_type=ct
        ).aggregate(r=Avg("rating"))["r"]
        return float(str(rating or "0"))
    except OverallRating.DoesNotExist:
        return 0.0


def prepare_num_ratings(resource):
    ct = ContentType.objects.get_for_model(resource)
    try:
        return OverallRating.objects.filter(
            object_id=resource.pk,
            content_type=ct
        ).all().count()
    except OverallRating.DoesNotExist:
        return 0


def prepare_num_comments(resource):
    ct = ContentType.objects.get_for_model(resource)
    try:
        return Comment.objects.filter(
            object_id=resource.pk,
            content_type=ct
        ).all().count()
    except Comment.DoesNotExist:
        return 0


def prepare_title_sortable(resource):
    return prepare_title(resource).lower()


def prepare_category(resource):
    if resource.category:
        return resource.category.identifier
    else:
        return None


def prepare_category_gn_description(resource):
    if resource.category:
        return resource.category.gn_description
    else:
        return None


def prepare_supplemental_information(resource):
    # For some reason this isn't a string
    return str(resource.supplemental_information)


def prepare_owner(resource):
    if resource.owner:
        return resource.owner.username
    else:
        return None


def prepare_owner_first(resource):
    if resource.owner.first_name:
        return resource.owner.first_name
    else:
        return None


def prepare_owner_last(resource):
    if resource.owner.last_name:
        return resource.owner.last_name
    else:
        return None


def prepare_source_host(resource):
    if resource.service is not None and resource.service.method == INDEXED:
        return urlparse(resource.service.base_url).netloc
    else:
        return None


def prepare_title(resource):
    return resource.title


def prepare_references(resource):
    return [{
        'name': link.name,
        'scheme': link.link_type,
        'url': link.url
    } for link in resource.link_set.ows()]


def prepare_subtype(resource):
    if resource.storeType == "dataStore":
        return "vector"
    elif resource.storeType == "coverageStore":
        return "raster"
    elif resource.storeType == "remoteStore":
        return "remote"
    else:
        return None


# Check to see if either time extent is set on the object,
# if so, then it is time enabled.
def prepare_has_time(resource):
    try:
        # if either time field is set to a value then time is enabled.
        if (resource.temporal_extent_start is not None or
                resource.temporal_extent_end is not None):
            return True
    except AttributeError:
        # when in doubt, it's false.
        return False


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


def create_layer_index(layer):
    bbox_left, bbox_right, bbox_bottom, bbox_top = prepare_bbox(layer)
    obj = LayerIndex(
        meta={'id': layer.id},
        id=layer.id,
        abstract=layer.abstract,
        category__gn_description=prepare_category_gn_description(layer),
        csw_type=layer.csw_type,
        csw_wkt_geometry=layer.csw_wkt_geometry,
        detail_url=layer.get_absolute_url(),
        owner__username=prepare_owner(layer),
        owner__first_name=prepare_owner_first(layer),
        owner__last_name=prepare_owner_last(layer),
        is_published=layer.is_published,
        featured=layer.featured,
        popular_count=layer.popular_count,
        share_count=layer.share_count,
        rating=prepare_rating(layer),
        srid=layer.srid,
        supplemental_information=prepare_supplemental_information(layer),
        thumbnail_url=layer.thumbnail_url,
        uuid=layer.uuid,
        title=prepare_title(layer),
        date=layer.date,
        type="layer",
        subtype=prepare_subtype(layer),
        typename=layer.service_typename,
        title_sortable=prepare_title_sortable(layer),
        category=prepare_category(layer),
        bbox_left=bbox_left,
        bbox_right=bbox_right,
        bbox_bottom=bbox_bottom,
        bbox_top=bbox_top,
        temporal_extent_start=layer.temporal_extent_start,
        temporal_extent_end=layer.temporal_extent_end,
        keywords=layer.keyword_slug_list(),
        regions=layer.region_name_list(),
        num_ratings=prepare_num_ratings(layer),
        num_comments=prepare_num_comments(layer),
        geogig_link=layer.geogig_link,
        has_time=prepare_has_time(layer),
        references=prepare_references(layer),
        source_host=prepare_source_host(layer)
    )
    obj.save()
    return obj.to_dict(include_meta=True)


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


def create_map_index(map):
    bbox_left, bbox_right, bbox_bottom, bbox_top = prepare_bbox(map)
    obj = MapIndex(
        meta={'id': map.id},
        id=map.id,
        abstract=map.abstract,
        category__gn_description=prepare_category_gn_description(map),
        csw_type=map.csw_type,
        csw_wkt_geometry=map.csw_wkt_geometry,
        detail_url=map.get_absolute_url(),
        owner__username=prepare_owner(map),
        popular_count=map.popular_count,
        share_count=map.share_count,
        rating=prepare_rating(map),
        srid=map.srid,
        supplemental_information=prepare_supplemental_information(map),
        thumbnail_url=map.thumbnail_url,
        uuid=map.uuid,
        title=map.title,
        date=map.date,
        type='map',
        title_sortable=prepare_title_sortable(map),
        category=prepare_category(map),
        bbox_left=bbox_left,
        bbox_right=bbox_right,
        bbox_bottom=bbox_bottom,
        bbox_top=bbox_top,
        temporal_extent_start=map.temporal_extent_start,
        temporal_extent_end=map.temporal_extent_end,
        keywords=map.keyword_slug_list(),
        regions=map.region_name_list(),
        num_ratings=prepare_num_ratings(map),
        num_comments=prepare_num_comments(map),
    )
    obj.save()
    return obj.to_dict(include_meta=True)


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


def create_document_index(document):
    bbox_left, bbox_right, bbox_bottom, bbox_top = prepare_bbox(document)
    obj = DocumentIndex(
        meta={'id': document.id},
        id=document.id,
        abstract=document.abstract,
        category__gn_description=prepare_category_gn_description(document),
        csw_type=document.csw_type,
        csw_wkt_geometry=document.csw_wkt_geometry,
        detail_url=document.get_absolute_url(),
        owner__username=prepare_owner(document),
        popular_count=document.popular_count,
        share_count=document.share_count,
        rating=prepare_rating(document),
        srid=document.srid,
        supplemental_information=prepare_supplemental_information(document),
        thumbnail_url=document.thumbnail_url,
        uuid=document.uuid,
        title=document.title,
        date=document.date,
        type="document",
        title_sortable=document.title.lower(),
        category=prepare_category(document),
        bbox_left=bbox_left,
        bbox_right=bbox_right,
        bbox_bottom=bbox_bottom,
        bbox_top=bbox_top,
        temporal_extent_start=document.temporal_extent_start,
        temporal_extent_end=document.temporal_extent_end,
        keywords=document.keyword_slug_list(),
        regions=document.region_name_list(),
        num_ratings=prepare_num_ratings(document),
        num_comments=prepare_num_comments(document),
    )
    obj.save()
    return obj.to_dict(include_meta=True)


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
    profile_detail_url = Text()

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
        documents_count=documents_count,
        profile_detail_url="/people/profile/{username}/".format(
            username=profile.username
        )
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
    detail_url = Text()

    class Meta:
        index = 'group-index'


def create_group_index(group):
    obj = GroupIndex(
        meta={'id': group.id},
        id=group.id,
        title=group.title,
        title_sortable=group.title.lower(),
        description=group.description,
        type="group",
        detail_url="/groups/group/{title}".format(
            title=group.title
        )
    )
    obj.save()
    return obj.to_dict(include_meta=True)
