from django.db import models


class Link(models.Model):
    url = models.URLField()

    def __unicode__(self):
        return u'<%s>' % self.url
