# -*- coding: utf-8 -*-

from jinja2.ext import Extension
from jinja2.exceptions import TemplateSyntaxError
from jinja2 import nodes
from jinja2 import Markup

import re
from jinja2.ext import Extension
from jinja2.lexer import Token, describe_token
from jinja2 import TemplateSyntaxError
from django.middleware.csrf import get_token

from django.utils.safestring import mark_safe
from django.conf import settings
import traceback
from django_bolts.utils import get_current_request


class CsrfExtension(Extension):
    tags = set(['csrf_token'])

    def __init__(self, environment):
        self.environment = environment

    def parse(self, parser):
        try:
            token = parser.stream.next()
            call_res = self.call_method('_render', [nodes.Name('csrf_token','load')])
            return nodes.Output([call_res]).set_lineno(token.lineno)
        except Exception:
            traceback.print_exc()

    def _render(self, csrf_token):
#        if not csrf_token:
#            request = get_current_request()
#            if request:
#                csrf_token = get_token(request)
#                 
        if csrf_token:            
            if csrf_token == 'NOTPROVIDED':
                return mark_safe(u"")

            return Markup(u"<div style='display:none'><input type='hidden'"
                          u" name='csrfmiddlewaretoken' value='%s' /></div>" % (csrf_token))

        if settings.DEBUG:
            
            raise Exception("A {% csrf_token %} was used in a template, but the context"
                          "did not provide the value.  This is usually caused by not "
                          "using RequestContext.")
        return u''

        

class URLExtension(Extension):
    """Returns an absolute URL matching given view with its parameters.

This is a way to define links that aren't tied to a particular URL
configuration::

{% url path.to.some_view arg1,arg2,name1=value1 %}

Known differences to Django's url-Tag:

- In Django, the view name may contain any non-space character.
Since Jinja's lexer does not identify whitespace to us, only
characters that make up valid identifers, plus dots and hyphens
are allowed. Note that identifers in Jinja 2 may not contain
non-ascii characters.

As an alternative, you may specifify the view as a string,
which bypasses all these restrictions. It further allows you
to apply filters:

{% url "ghg.some-view"|afilter %}
"""

    tags = set(['url'])

    def parse(self, parser):
        stream = parser.stream

        tag = stream.next()

        # get view name
        if stream.current.test('string'):
            # Need to work around Jinja2 syntax here. Jinja by default acts
            # like Python and concats subsequent strings. In this case
            # though, we want {% url "app.views.post" "1" %} to be treated
            # as view + argument, while still supporting
            # {% url "app.views.post"|filter %}. Essentially, what we do is
            # rather than let ``parser.parse_primary()`` deal with a "string"
            # token, we do so ourselves, and let parse_expression() handle all
            # other cases.
            if stream.look().test('string'):
                token = stream.next()
                viewname = nodes.Const(token.value, lineno=token.lineno)
            else:
                viewname = parser.parse_expression()
        else:
            # parse valid tokens and manually build a string from them
            bits = []
            name_allowed = True
            while True:
                if stream.current.test_any('dot', 'sub', 'colon'):
                    bits.append(stream.next())
                    name_allowed = True
                elif stream.current.test('name') and name_allowed:
                    bits.append(stream.next())
                    name_allowed = False
                else:
                    break
            viewname = nodes.Const("".join([b.value for b in bits]))
            if not bits:
                raise TemplateSyntaxError("'%s' requires path to view" %
                    tag.value, tag.lineno)

        # get arguments
        args = []
        kwargs = []
        while not stream.current.test_any('block_end', 'name:as'):
            if args or kwargs:
                stream.expect('comma')
            if stream.current.test('name') and stream.look().test('assign'):
                key = nodes.Const(stream.next().value)
                stream.skip()
                value = parser.parse_expression()
                kwargs.append(nodes.Pair(key, value, lineno=key.lineno))
            else:
                args.append(parser.parse_expression())

        def make_call_node(*kw):
            return self.call_method('_reverse', args=[
                viewname,
                nodes.List(args),
                nodes.Dict(kwargs),
                nodes.Name('_current_app', 'load'),
            ], kwargs=kw)

        # if an as-clause is specified, write the result to context...
        if stream.next_if('name:as'):
            var = nodes.Name(stream.expect('name').value, 'store')
            call_node = make_call_node(nodes.Keyword('fail',
                nodes.Const(False)))
            return nodes.Assign(var, call_node)
        # ...otherwise print it out.
        else:
            return nodes.Output([make_call_node()]).set_lineno(tag.lineno)

    @classmethod
    def _reverse(self, viewname, args, kwargs, current_app=None, fail=True):
        from django.core.urlresolvers import reverse, NoReverseMatch

        # Try to look up the URL twice: once given the view name,
        # and again relative to what we guess is the "main" app.
        url = ''
        try:
            url = reverse(viewname, args=args, kwargs=kwargs,
                current_app=current_app)
        except NoReverseMatch:
            projectname = settings.SETTINGS_MODULE.split('.')[0]
            try:
                url = reverse(projectname + '.' + viewname,
                              args=args, kwargs=kwargs)
            except NoReverseMatch:
                if fail:
                    raise
                else:
                    return ''

        return url        


_tag_re = re.compile(r'(?:<(/?)([a-zA-Z0-9_-]+)\s*|(>\s*))(?s)')
_ws_normalize_re = re.compile(r'[ \t\r\n]+')


class StreamProcessContext(object):

    def __init__(self, stream):
        self.stream = stream
        self.token = None
        self.stack = []

    def fail(self, message):
        raise TemplateSyntaxError(message, self.token.lineno,
                                  self.stream.name, self.stream.filename)


def _make_dict_from_listing(listing):
    rv = {}
    for keys, value in listing:
        for key in keys:
            rv[key] = value
    return rv


class HTMLCompress(Extension):
    """
        jinja2htmlcompress
        ~~~~~~~~~~~~~~~~~~
    
        A Jinja2 extension that eliminates useless whitespace at template
        compilation time without extra overhead.
    
        :copyright: (c) 2011 by Armin Ronacher.
        :license: BSD, see LICENSE for more details.
    """
    
    isolated_elements = set(['script', 'style', 'noscript', 'textarea'])
    void_elements = set(['br', 'img', 'area', 'hr', 'param', 'input',
                         'embed', 'col'])
    block_elements = set(['div', 'p', 'form', 'ul', 'ol', 'li', 'table', 'tr',
                          'tbody', 'thead', 'tfoot', 'tr', 'td', 'th', 'dl',
                          'dt', 'dd', 'blockquote', 'h1', 'h2', 'h3', 'h4',
                          'h5', 'h6', 'pre'])
    breaking_rules = _make_dict_from_listing([
        (['p'], set(['#block'])),
        (['li'], set(['li'])),
        (['td', 'th'], set(['td', 'th', 'tr', 'tbody', 'thead', 'tfoot'])),
        (['tr'], set(['tr', 'tbody', 'thead', 'tfoot'])),
        (['thead', 'tbody', 'tfoot'], set(['thead', 'tbody', 'tfoot'])),
        (['dd', 'dt'], set(['dl', 'dt', 'dd']))
    ])

    def is_isolated(self, stack):
        for tag in reversed(stack):
            if tag in self.isolated_elements:
                return True
        return False

    def is_breaking(self, tag, other_tag):
        breaking = self.breaking_rules.get(other_tag)
        return breaking and (tag in breaking or
            ('#block' in breaking and tag in self.block_elements))

    def enter_tag(self, tag, ctx):
        while ctx.stack and self.is_breaking(tag, ctx.stack[-1]):
            self.leave_tag(ctx.stack[-1], ctx)
        if tag not in self.void_elements:
            ctx.stack.append(tag)

    def leave_tag(self, tag, ctx):
        if not ctx.stack:
            ctx.fail('Tried to leave "%s" but something closed '
                     'it already' % tag)
        if tag == ctx.stack[-1]:
            ctx.stack.pop()
            return
        for idx, other_tag in enumerate(reversed(ctx.stack)):
            if other_tag == tag:
                for num in xrange(idx + 1):
                    ctx.stack.pop()
            elif not self.breaking_rules.get(other_tag):
                break

    def normalize(self, ctx):
        pos = 0
        buffer = []
        def write_data(value):
            if not self.is_isolated(ctx.stack):
                value = _ws_normalize_re.sub(' ', value.strip())
            buffer.append(value)

        for match in _tag_re.finditer(ctx.token.value):
            closes, tag, sole = match.groups()
            preamble = ctx.token.value[pos:match.start()]
            write_data(preamble)
            if sole:
                write_data(sole)
            else:
                buffer.append(match.group())
                (closes and self.leave_tag or self.enter_tag)(tag, ctx)
            pos = match.end()

        write_data(ctx.token.value[pos:])
        return u''.join(buffer)

    def filter_stream(self, stream):
        ctx = StreamProcessContext(stream)
        for token in stream:
            if token.type != 'data':
                yield token
                continue
            ctx.token = token
            value = self.normalize(ctx)
            yield Token(token.lineno, 'data', value)


class SelectiveHTMLCompress(HTMLCompress):

    def filter_stream(self, stream):
        ctx = StreamProcessContext(stream)
        strip_depth = 0
        while 1:
            if stream.current.type == 'block_begin':
                if stream.look().test('name:strip') or \
                   stream.look().test('name:endstrip'):
                    stream.skip()
                    if stream.current.value == 'strip':
                        strip_depth += 1
                    else:
                        strip_depth -= 1
                        if strip_depth < 0:
                            ctx.fail('Unexpected tag endstrip')
                    stream.skip()
                    if stream.current.type != 'block_end':
                        ctx.fail('expected end of block, got %s' %
                                 describe_token(stream.current))
                    stream.skip()
            if strip_depth > 0 and stream.current.type == 'data':
                ctx.token = stream.current
                value = self.normalize(ctx)
                yield Token(stream.current.lineno, 'data', value)
            else:
                yield stream.current
            stream.next()


def test():
    from jinja2 import Environment
    env = Environment(extensions=[HTMLCompress])
    tmpl = env.from_string('''
        <html>
          <head>
            <title>{{ title }}</title>
          </head>
          <script type=text/javascript>
            if (foo < 42) {
              document.write('Foo < Bar');
            }
          </script>
          <body>
            <li><a href="{{ href }}">{{ title }}</a><br>Test   Foo
            <li><a href="{{ href }}">{{ title }}</a><img src=test.png>
          </body>
        </html>
    ''')
    print tmpl.render(title=42, href='index.html')

    env = Environment(extensions=[SelectiveHTMLCompress])
    tmpl = env.from_string('''
        Normal   <span>  unchanged </span> stuff
        {% strip %}Stripped <span class=foo  >   test   </span>
        <a href="foo">  test </a> {{ foo }}
        Normal <stuff>   again {{ foo }}  </stuff>
        <p>
          Foo<br>Bar
          Baz
        <p>
          Moep    <span>Test</span>    Moep
        </p>
        {% endstrip %}
    ''')
    print tmpl.render(foo=42)


if __name__ == '__main__':
    test()
        
#class LoadExtension(Extension):
#    """Changes auto escape rules for a scope."""
#    tags = set(['load'])
#
#    def parse(self, parser):
#        node = nodes.ExprStmt(lineno=next(parser.stream).lineno)
#
#        modules = []
#        while parser.stream.current.type != 'block_end':
#            lineno = parser.stream.current.lineno
#            if modules:
#                parser.stream.expect('comma')
#            expr = parser.parse_expression()
#            module = expr.as_const()
#            modules.append(module)
#
#        assignments = []
#        from djinja.template.defaultfunctions import Load
#        for m in modules:
#            target = nodes.Name(m,'store')
#            func = nodes.Call(nodes.Name('load', 'load'), [nodes.Const(m)],
#                              [], None, None)
#            assignments.append(nodes.Assign(target, func, lineno=lineno))
#                
#            for i in Load(m).globals.keys():
#                target = nodes.Name(i,'store')
#                f = nodes.Getattr(nodes.Name(m,'load'), i, 'load')
#            
#                assignments.append(nodes.Assign(target, f, lineno=lineno))
#
#        return assignments
