import six
from django.template import TemplateSyntaxError
from django.template.loader import render_to_string

from ttag import core, args


class TemplateTagOptions(core.Options):

    def __init__(self, meta, *args, **kwargs):
        super(TemplateTagOptions, self).__init__(meta=meta, *args, **kwargs)
        self.template_name = getattr(meta, 'template_name', 'using')

    def post_process(self):
        super(TemplateTagOptions, self).post_process()
        non_keyword_args = [name for name, arg in self.named_args.items()
                            if not arg.keyword]
        if (self.template_name in non_keyword_args and
                self.template_name not in self.parent_args):
            raise TemplateSyntaxError(
                "%s can not explicitly define a named argument called %r" %
                (self.name, self.template_name))

        arg = args.Arg(required=False, named=True)
        arg.name = self.template_name
        self.named_args[self.template_name] = arg


class TemplateTagMetaclass(core.DeclarativeArgsMetaclass):
    options_class = TemplateTagOptions


@six.add_metaclass(TemplateTagMetaclass)
class TemplateTag(core.BaseTag):

    def render(self, context):
        data = self.resolve(context)
        template_name = data.get(self._meta.template_name, self.using(data))
        if not template_name:
            raise TemplateSyntaxError(
                "%s wasn't given a template to render with" % self._meta.name)
        extra_context = {
            'data': data,
            'output': self.output(data),
        }
        return render_to_string(template_name, extra_context, context)

    def using(self, data):
        """
        TemplateTag subclasses must implement this method if
        not templates are given as the argument, e.g.::

        class RenderTag(TemplateTag):

            def using(context):
                return 'templatetags/%s.html' % self._meta.name.lower()
        """
        return None
