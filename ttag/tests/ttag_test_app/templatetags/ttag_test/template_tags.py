import datetime
import ttag


class SelfReferentialTag(ttag.helpers.TemplateTag):

    def using(self, data):
        return 'ttag/%s/%s.html' % (
            self.__class__.__module__.split('.')[-1].lower(),
            self._meta.name.lower()
        )


class Do(SelfReferentialTag):

    class Meta:
        template_name = 'it'

    def output(self, data):
        return 'done'


class Go(ttag.helpers.TemplateTag):

    def output(self, data):
        return 'home'


class Ask(SelfReferentialTag):
    value = ttag.Arg()

    def output(self, data):
        if "date" in data['value']:
            return datetime.datetime.today()

