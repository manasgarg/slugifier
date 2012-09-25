Add slug field to your mongoengine based documents
===================================================

This package provides an easy way to add slugs to your mongoengine documents.
Built for flask but can be easily modified for other web frameworks like
django.

Features
========
* Auto-generation of slugs and handling of conflicts for the slug values.
* Support for case-insenstive slug values with a redirect (from the unintended
  one to the right one).
* Support for changing of slug value without breaking the old links. It adds a
  redirect from old slug to new slug.
* An easy to use SlugMixin to add to your Document classes to add slug support.
* And an easy to use decorator for your views to transparently convert slugs to
  objects.

How to use it
=============

First install the dependencies: flask, mongoengine & pymongo.

Let's say, you have the following document:

```
from mongoengine import *

class User( Document):
    name = StringField()
    email = StringField()
    password = StringField()
```

You want to add slug to this document. So, modify the code:

```
from mongoengine import *
from slugifier.slug import SlugMixin

class User( Document, SlugMixin):
    name = StringField()
    email = StringField()
    password = StringField()

    meta = { "indexes": ["slug"] }

    def slug_base_text( self):
        return self.name
```

Here, you add SlugMixin to your User class. This will add a "slug" field to all
your User documents.

Next, you add an index on slug so that we can do the look ups based on that.

Finally, you add a method "slug_base_text()" to tell the SlugMixin what text to
use to generate the slug.

Now, over to the views. Let's say, user profile is at the url:
/user/<user_slug>. To construct your views, you have two options:

```
@app.route( "/user/<slug>")
def view_user_profile( slug):
    user = User.objects.get( slug=slug)
    ...
```

Here, you directly lookup the user with the given slug.

Second option uses a decorator and is more feature rich.

```
from slugifier.slug import slug_to_obj_converter

@app.route("/user/<slug>")
@slug_to_obj_converter( User, "/user/%s")
def view_user_profile( user):
    ...
```

In this case, you use the slug_to_obj_converter decorator from the slugifier
package. It does a couple of things:

* First, it converts the slug to User object after doing a quick lookup and
  passes that User object.
* Also, if the slug doesn't exist, it will raise 404.
* Next, it will do a case-sensitive redirect. Let's say, user's name is "Ram
  Gupta" and hence the slug is "Ram-Gupta". Now, if someone tries to access
  "/user/ram-gupta", this decorator will just do a redirect to
  "/user/Ram-Gupta". Neat?
* Finally, it does a redirect from old slug to new slug. Let's say, your user
  gave the name as "Some Name". The slug will be "Some-Name". Now the user
  changes name to "Some Other Name". The slug will become "Some-Other-Name".
  What happens to the old urls? If some accesses "/user/Some-Name" now, the
  decorator will do a seamless redirect to the new url "/user/Some-Other-Name".
