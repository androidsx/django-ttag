import six
from django import template

from ttag import utils, args


class Options(object):

    def __init__(self, meta, *args, **kwargs):
        super(Options, self).__init__(*args, **kwargs)
        self.positional_args = []
        self.named_args = {}
        # A list of argument names that are inherited from bases
        self.parent_args = []
        self.name = getattr(meta, 'name', None)
        self.block = getattr(meta, 'block', False)
        self.end_block = getattr(meta, 'end_block', 'end%(name)s')

    @property
    def args(self):
        if not hasattr(self, '_args'):
            args = dict([(arg.name, arg) for arg in self.positional_args])
            args.update(self.named_args)
            self._args = args
        return self._args

    def reset_args(self):
        if hasattr(self, '_args'):
            del self._args

    def post_process(self):
        pass

    def _get_end_block(self):
        return self._end_block % {'name': self.name}

    def _set_end_block(self, value):
        self._end_block = value

    end_block = property(_get_end_block, _set_end_block)


class DeclarativeArgsMetaclass(type):
    options_class = Options

    def __new__(cls, name, bases, attrs):
        super_new = super(DeclarativeArgsMetaclass, cls).__new__
        parents = [b for b in bases if isinstance(b, DeclarativeArgsMetaclass)]
        if not parents:
            return super_new(cls, name, bases, attrs)

        try:
            meta = attrs.pop('Meta')
        except KeyError:
            meta = None
        opts = cls.options_class(meta)

        library = getattr(meta, 'library', None)
        if library:
            if not isinstance(library, template.Library):
                raise TypeError("A valid library is required.")

        # Generate the tag name if it wasn't explicitly provided.
        if not opts.name:
            opts.name = utils.get_default_name(name)

        # Set the class name to the name defined, ensuring the defined name
        # will be used when registering the tag with a Django tag library.
        name = opts.name

        all_args = [(arg_name.rstrip('_'), attrs.pop(arg_name))
                    for arg_name, obj in list(attrs.items())
                    if isinstance(obj, args.Arg)]
        all_args.sort(key=lambda x: x[1].creation_counter)

        # Put the positional and named arguments in their respective places.
        optional_positional = False
        for arg_name, arg in all_args:
            arg.name = arg_name
            if arg.positional:
                if arg.required:
                    if optional_positional:
                        raise template.TemplateSyntaxError(
                            "Required '%s' positional argument of '%s' cannot "
                            "exist after optional positional arguments." % (
                                arg.name,
                                opts.name,
                            )
                        )
                else:
                    optional_positional = True
                opts.positional_args.append(arg)
            else:
                opts.named_args[arg_name] = arg

        # If this class is subclassing another Tag, add that tag's positional
        # arguments before ones declared here. The bases are looped in reverse
        # to preserve the correct order of positional arguments and correctly
        # override named arguments.
        for base in bases[::-1]:
            base_opts = getattr(base, '_meta', None)
            if hasattr(base_opts, 'positional_args'):
                opts.positional_args = base_opts.positional_args + \
                                                    opts.positional_args
            if hasattr(base_opts, 'named_args'):
                for arg_name, arg in six.iteritems(base_opts.named_args):
                    if arg_name not in opts.named_args:
                        opts.named_args[arg_name] = arg
                        opts.parent_args.append(arg_name)

        attrs['_meta'] = opts

        opts.post_process()

        # Create the new class.
        new_class = super_new(cls, name, bases, attrs)

        # Register the tag if a tag library was provided.
        if library:
            library.tag(opts.name, new_class)

        return new_class


class BaseTag(template.Node):
    """
    A template tag.
    """

    def __init__(self, parser, token):
        self._vars = {}
        tokens = list(utils.smarter_split(token.contents))[1:]
        self._process_positional_args(parser, tokens)
        self._process_named_args(parser, tokens)
        if self._meta.block:
            nodelists = {}
            block_names = [self._meta.end_block]
            other_blocks = isinstance(self._meta.block, dict) and \
                                                self._meta.block or {}
            block_names.extend(other_blocks)
            current = ''
            while True:
                attr = 'nodelist%s' % (current and '_%s' % current or '')
                nodelists[attr] = parser.parse(block_names)
                current = parser.next_token().contents
                if current == self._meta.end_block:
                    break
            for name, required in six.iteritems(other_blocks):
                if name in nodelists:
                    continue
                if required:
                    raise template.TemplateSyntaxError('Expected {%% %s %%}' %
                                                       name)
                nodelists[name] = template.NodeList()
            self.child_nodelists = list(nodelists)
            for attr, nodelist in six.iteritems(nodelists):
                setattr(self, attr, nodelist)

    def _valid_named_args(self):
        """
        Return a list of named arguments. Keyword arguments are appended with a
        ``=`` so they can be checked for in :meth:`Arg.is_token_named_arg`.
        """
        return [arg.keyword and '%s=' % name or name
                for name, arg in six.iteritems(self._meta.named_args)]

    def _process_positional_args(self, parser, tokens):
        named_args = self._valid_named_args()
        for arg in self._meta.positional_args:
            value = arg.consume(parser, tokens, named_args)
            if value is None:
                if arg.default is not None:
                    self._vars[arg.name] = arg.default
                elif arg.required:
                    raise template.TemplateSyntaxError(
                        "'%s' positional argument to '%s' is required" % (
                            arg.name,
                            self._meta.name,
                        )
                    )
            else:
                self._vars[arg.name] = value

    def _process_named_args(self, parser, tokens):
        named_args = self._valid_named_args()
        while tokens:
            arg_name = tokens[0]
            keyword = '=' in arg_name
            if keyword:
                arg_name, tokens[0] = arg_name.split('=', 1)
            else:
                del tokens[0]
            try:
                arg = self._meta.named_args[arg_name]
            except KeyError:
                raise template.TemplateSyntaxError(
                    "'%s' does not take argument '%s'" % (self._meta.name,
                                                          arg_name)
                )
            if not keyword and arg.keyword:
                raise template.TemplateSyntaxError(
                    "'%s' expected '%s=...'" % (self._meta.name, arg_name)
                )
            if keyword and not arg.keyword:
                raise template.TemplateSyntaxError(
                    "'%s' didn't expect an '=' after '%s'" % (self._meta.name,
                                                              arg_name)
                )

            value = arg.consume(parser, tokens, named_args)
            self._vars[arg.name] = value

        # Handle missing items: required, default.
        for arg_name, arg in six.iteritems(self._meta.named_args):
            if arg.name in self._vars:
                continue
            if arg.default is not None:
                self._vars[arg.name] = arg.default
            elif arg.required:
                raise template.TemplateSyntaxError(
                    "'%s' argument to '%s' is required" % (arg_name,
                                                           self._meta.name)
                )

    def clean(self, data, context):
        """
        Additional tag-wide argument cleaning after each individual Arg's
        ``clean`` has been called.
        """
        return data

    def render(self, context):
        """
        Render the tag.
        """
        data = self.resolve(context)
        return self.output(data)

    def output(self, data):
        raise NotImplementedError("Tag subclasses must implement this method.")

    def resolve(self, context):
        """
        Resolve variables and run clean methods, returning a dictionary
        containing the cleaned data.

        Cleaning happens after variable/filter resolution.

        Cleaning order is similar to forms:

        1) The argument's ``.clean()`` method.
        2) The tag's ``clean_ARGNAME()`` method, if any.
        3) The tag's ``.clean()`` method.
        """
        data = {}
        for name, value in six.iteritems(self._vars):
            arg = self._meta.args[name]
            value = arg.resolve(value, context)
            value = arg.clean(value)
            try:
                tag_arg_clean = getattr(self, 'clean_%s' % arg.name)
            except AttributeError:
                pass
            else:
                value = tag_arg_clean(value)
            data[name] = value
        try:
            data = self.clean(data, context)
        except TypeError:
            # Before version 2.0, clean accepted only the data parameter, keep
            # supporting that.
            data = self.clean(data)
        return data


@six.add_metaclass(DeclarativeArgsMetaclass)
class Tag(BaseTag):
    # This is a separate class from BaseTag in order to abstract the way
    # arguments are specified. This class (Tag) is the one that does the
    # fancy metaclass stuff purely for the semantic sugar -- it allows one
    # to define a tag using declarative syntax.
    # BaseTag itself has no way of designating arguments.
    pass
