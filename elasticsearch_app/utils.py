from elasticsearch_app import search

def index_object(object, index=None):
    '''
    Indexes an object into its appropriate model index.
    Tries to use its indexing method if it exists.
    Otherwise, it will index it with just the id.
    :param object: The object you wish to index
    :param index: The search index to put the object in
    :return: A dict of the successfully indexed object
    '''
    classname = object.__class__.__name__
    if classname == 'Profile':
        return search.create_profile_index(object)
    elif hasattr(object, 'indexing'):
        return object.indexing()
    else:
        if index is not None:
            indexed_object = index(
                meta={'id': object.id},
                id=object.id
            )
            indexed_object.save()
            return index_object.to_dict(include_meta=True)
