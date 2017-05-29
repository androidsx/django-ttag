=========
Reference
=========


Overview
========

TTag replaces the normal method of creating custom template tags.  It
uses a custom template ``Node`` subclass called ``Tag`` which handles all of
the relevant aspects of a tag: defining and parsing arguments, handling
validation, resolving variables from the context, and rendering output.


Tag
===

.. currentmodule:: ttag

.. class:: Tag

    A representation of a template tag. For example::

	    class Welcome(ttag.Tag):

	        def output(self, data):
	            return "Hi there!"

Meta options
------------

.. class:: Tag.Meta

    A ``Tag`` takes options via a ``Meta`` inner class::

        class Welcome(ttag.Tag):

            class Meta:
                name = "hi"

    .. attribute:: name

        Explicitly choose a name for the tag. If not given, the tag's name will be
    	created by taking the class's name and converting it from CamelCase to
    	under_score format. For example, ``AmazingStuff`` would turn into
    	``{% amazing_stuff %}``.

    .. attribute:: register

        Register the tag in a tag library.

        Alternatively, a tag can still be rendered the standard way:
        ``some_library.tag(ThisTag)``.

    .. attribute:: block

        Retrieve subsequent template nodes until ``{% end[tagname] %}``, adding
        them to ``self.nodelists``.

    .. attribute:: end_block

        An alternative ending block node. Defaults to ``'end%(name)s'``.

output
------

If your tag does not modify the output, override this method to change the
output of this tag.

.. method:: Tag.output(data)

    :param data: A dictionary of data built from the arguments this tag uses,
    	usually built by the :meth:`resolve` method.

render
------

As an alternative to overriding the ``output`` method, a ``TemplateTag``
subclass may directly override the ``render`` method. This is useful for
when you want to alter the context.

.. method:: Tag.render(context)

    :param context: The current template context.

    ``render`` must return a unicode string.

    If your tag doesn't return anything (e.g., it only manipulates the
    context), ``render`` should simply return an empty string.

To retrieve the values of the tag's arguments, if any, use the following method
inside ``render``:

.. method:: Tag.resolve(context)

	Retrieve the values of the tag's arguments.

	:param context: The current template context.
	:returns: A data dictionary containing the values of the tag's arguments.


Arguments
=========

Arguments can be either positional or named. They are specified as properties
of the tag class, in a similar way to Django's forms and models.

If the property name clashes with a append a trailing slash - it will be
removed from the argument's ``name``. For example, pay attention to the ``as_``
argument in the tag below::

    class Set(ttag.Tag):
        value = ttag.Arg()
        as_ = ttag.BasicArg()

        def render(self, context):
            data = self.resolve(context)
            as_var = data['as']
            context[as_var] = data['value']
            return ''

Positional arguments
--------------------

By default, an argument is considered positional::

    class Positional(ttag.Tag):
        first = ttag.Arg()
        second = ttag.Arg()

This would result in a tag named ``positional`` which took two required
arguments, which would be assigned to ``'first'`` and ``'second'`` items
of the data dictionary returned by the ``resolve`` method.

Use the :class:`ConstantArg` for simple required string-based arguments which
assist readability::

    class Measure(ttag.Tag):
        start = ttag.Arg()
        to = ttag.ConstantArg()
        finish = ttag.Arg()

Named arguments
---------------

Named arguments can appear in any order in a tag's arguments, after the
positional arguments.

The standard type of named argument uses space separation::

    class Named(ttag.Tag):
        limit = ttag.Arg(named=True)
        offset = ttag.Arg(named=True)

This would create a tag named ``named`` which took two named arguments,
``limit`` and ``offset``.  They could be specified in any order::

    {% named limit 15 offset 42 %}

    {% named offset 4 limit 12 %}

Alternatively, named arguments can use "keyword" style named arguments::
you can use the ``keyword`` parameter::

    class Named(ttag.Tag):
        limit = ttag.Arg(keyword=True)
        offset = ttag.Arg(keyword=True)

Which would be used by:
    {% named offset 4 limit 12 %}

If an optional argument is not specified in the template, it will not be
added to the data dictionary. Alternately, use ``default`` to have a default
value added to the data dictionary if an argument is not provided::

    class NamedTag(ttag.Tag):
        limit = ttag.Arg(default=100)
        offset = ttag.Arg(required=False)


Argument Types
==============

``Arg`` and its subclasses provide various other levels of parsing and
validation.


Arg
---

.. class:: Arg(required=True, default=None, null=False, keyword=False, named=False)

    A standard argument in a :class:`Tag`. Used as a base class for all other
    argument classes.

    :param required:
        Whether the argument is required as part of the tag definition in the
        template. Required positional arguments can not occur after optional
        ones.

        Defaults to ``True``.

    :param default:
        The default value for this argument if it is not specified.

        If ``None`` and the field is required, an exception will be raised when
        the template is parsed.

        Defaults to ``None``.

    :param null:
        Determines whether a value of ``None`` is an acceptable value for the
        argument resolution.

        When set to ``False``, a value of ``None`` or a missing context
        variable will cause a ``TemplateTagValidationError`` when this argument
        is cleaned.

        Defaults to ``False``.

    :param keyword:
        Make this a named argument, using an equals to separate the value
        from the argument name, for example, ``{% tag limit=10 %}``.

        Defaults to ``False``.

    :param named:
        Make this a named argument, using an space to separate the argument
        name from its value, for example, ``{% tag limit 10 %}``.

        Defaults to ``False``.

    The ``named`` and ``keyword`` parameters can not both be set to ``True``.


Casting Arguments
-----------------

.. class:: IntegerArg

    Tries to cast the argument value to an integer, throwing a template error
    if this fails.


.. class:: StringArg

    Tries to cast the argument value to unicode, throwing a template error if
    this fails.


Validation Arguments
--------------------

.. class:: IsInstanceArg(..., cls, cls_name)

    Validates that the argument is an instance of the provided class (``cls``),
    otherwise throws a a template error, using the ``cls_name`` in the error
    message.

    For example::

    	date = IsInstanceArg(cls=datetime.date, cls_name=_('Date'))


.. class:: DateTimeArg

    Validates that the argument is a ``datetime`` instance, otherwise throws a
    template error.


.. class:: DateArg

    Validates that the argument is a ``date`` instance, otherwise throws a
    template error.


.. class:: TimeArg

    Validates that the argument is a ``time`` instance, otherwise throws a
    template error.


.. class:: ModelInstanceArg(..., model)

    Validates that the passed in value is an instance of the specified
    ``Model`` class.  It requires a single additional named argument.

    :param model:
        The ``Model`` class you want to validate against.


Other Arguments
---------------

.. class:: BooleanArg

    A "flag" argument which doesn't consume any additional tokens.

    If it is not defined in the tag, the argument value will not exist in the
    resolved data dictionary.

    For example::

        class Cool(ttag.Tag)
            cool = ttag.BooleanArg()

            def output(self, data):
                if 'cool' in data:
                    return "That's cool!"
                else:
                    return "Uncool."


.. class:: BasicArg

    A simpler argument which doesn't compile its value as a
    ``FilterExpression``.

    Example usage::

        class GetUsers(ttag.Tag):
            as_ = ttag.BasicArg()

            def render(self, context):
                data = self.resolve(data)
                context[data['as']] = Users.objects.all()
                return ''


.. class:: ConstantArg

    An argument which expects it's value to be a constant (non-compiled) value,
    usually used to enhance tag readability.

    Cannot be a named or keyword argument.

    Example usage::

        class Range(ttag.Tag):
            start = ttag.IntegerArg()
            to_ = ttag.ConstantArg()
            finish = ttag.IntegerArg()

            def output(self, data):
                start = data['start']
                finish = data['finish'] + 1
                return ', '.join([str(num) for num in range(start, finish)])


.. class:: MultiArg

    Greedily parses all remaining positional arguments.

    Stops when all the tag tokens tokens are consumed or named keyword argument
    is hit. For example::

        class DotConcat(ttag.Tag):
            bits = ttag.MultiArg()
            default = ttag.Arg(named=True, required=False)

            def output(self, data):
                bits = []
                default = data.get('default', '')
                for bit in data['bits']:
                    bits.append([force_text(bit) or default])
                return '.'.join(bits)

    This tag could be used like this::

        {% dot_concat "a" "" "c" default "X" %}

    Resulting in ``a.X.c``.


.. class:: KeywordsArg(..., compact=True, verbose=False, compile_values=True)

    Parses one or more additional tokens as keywords.

    :param compact:
        Use compact format. For example::

            {% compact with foo=1 bar=2 %}

    :param verbose:
        Use verbose format::

        	{% verbose with 1 as foo and 2 as bar %}

        In verbose mode, the ``and`` is required for multiple arguments unless
        ``compact`` is also set to ``True`` (in which case the ``and`` is
        optional).

    :param compile_values:
        Compile keyword values as template variables (defaults to ``True``).

    If ``verbose`` and ``compact`` are set to ``True``, then either (or
    even both) formats are allowed. This is usually only used for backwards
    compatibility::

        {% mixed with foo=1 bar=2 %}
        {% mixed with 1 as foo and 2 as bar %}
        {% mixed with foo=1 and 2 as bar %}
