"""A module to work with slug generation."""
from mongoengine import *
import bson.objectid

import unicodedata
import re
from hashlib import sha1

from flask import redirect, abort

class Slug( Document):
    """Represents a slug in the database. Fields are:
        * namespace - A namespace under which this slug falls (e.g. match, team, user etc)
        * slug - Actual slug.
        * slug_lower_hash - A hash of lower-case slug. This is useful for
        *   discovering the actual slug in case user changes the case in the URL.
        * new_slug - useful when the name of a resource is changed. The old
        * slug object will have new_slug populated. With this, the application
        * can do a 302 redirect to the new slug.
    """
    namespace = StringField()
    slug = StringField()
    slug_lower_hash = StringField()
    new_slug = StringField()            # In case slug was changed after a name change.

    meta = {
            "indexes": [ ("namespace", "slug"), ("namespace", "slug_lower_hash")]
    }

class SlugMixin(object):
    """Mixin to add slugs related functionality to your mongoengine documents.
        To use:
        a) Use this mixin in your mongoengine document classes.
        b) Override slug_base_text method if required. It should return the
           text from which slug should be generated. By default, it uses the name
           property of the class.
        c) Create an index on the slug field for your document.
    """
    slug = StringField()

    def slug_base_text( self):
        """This function returns the value based on which the slug will be
            generated. It defaults to the value of name property. Override it in
            your class.
        """
        return self.name

    def set_slug( self):
        self.slug = generate_slug( self.__class__.__name__, self.slug_base_text, old_slug_value=self.slug)
        
def generate_slug_value( base_text, max_length=80):
    """Generate a potential slug value."""
    base_text = unicode( base_text)
    value = unicodedata.normalize('NFKD', base_text).encode('ascii', 'ignore')[:max_length]
    value = unicode(re.sub('[^\w\s-]', '', value).strip())
    value = re.sub('[-\s]+', '-', value)

    return value

def generate_slug( namespace, base_text, max_length=80, old_slug_value=""):
    """Generate a slug. These are the arguments:
        * namespace - A namespace under which this slug should be unique.
        * base_text - Text for generating a slug.
        * max_length - 80 is enough.
        * old_slug_value - In case, a new slug is being generated for a
        * resource, this will be existing slug value. Used for generating a
        * redirect from old value to new value.
    """
    value = generate_slug_value( base_text, max_length)

    if( value == old_slug_value):
        return value

    orig_value = value

    collision_free = False
    counter = 0
    while not collision_free:
        s = Slug.objects( namespace=namespace, slug=value).first()
        if( not s):
            collision_free = True
        else:
            counter += 1
            value = orig_value + '-' + str(counter)

    s = Slug( namespace=namespace, slug=value, slug_lower_hash=sha1( value.lower()).hexdigest())
    s.save()

    if( old_slug_value):
        old = Slug.objects( namespace=namespace, slug=old_slug_value).first()
        if( old):
            old.new_slug = s.slug
            old.save()

    return value

def lookup_slug( namespace, value):
    """Find out if a case-insensitive match exists for the given slug value."""
    s = Slug.objects( namespace=namespace, slug_lower_hash=sha1( value.lower()).hexdigest()).first()
    if( not s):
        return None

    if( s.new_slug):
        return s.new_slug

    return s.slug

def slug_to_obj_converter( objclass, url_template):
    """A decorator converting a slug into the actual class object. In case the
    object is not found, it will raise 404.
    """
    def view_wrapper( view_func):
        def wrapper( slug, *args, **kwargs):
            obj = objclass.objects( slug=slug).first()
            if( not obj):
                alternate_slug = lookup_slug( objclass.__name__, slug)
                if( alternate_slug and alternate_slug != slug):
                    if( url_template):
                        return redirect( url_template % (alternate_slug), 301)
                    else:
                        obj = objclass.objects( slug=alternate_slug).first()

                if( not obj):
                    abort( 404)

                    # Useful for scenarios where object id based url should be
                    # redirected to slug based one. Not required as of now.
                    # 
                    # try:
                    #     obj_id = bson.objectid.ObjectId( slug)
                    # except bson.objectid.InvalidId:
                    #     abort( 404)

                    # obj = objclass.objects(id=obj_id).first()
                    # if obj:
                    #     return redirect( url_template % (obj.slug), 302)
                    # else:
                    #     abort( 404)

            return view_func( request, obj, *args, **kwargs)

        return wrapper

    return view_wrapper
