"""
Implementation of flexx.event in JS via PyScript.

In this module we compile the flexx event system to JavaScript. Most
code is generated by transpiling methods from the Python classes. This
module implements a JS variant of some classes to overload certain
behavior in JS. E.g. the JS implementation of the Component class has
some boilerplate code to create actions, reactions, emitters and
properties.

By reusing as much code as possible, we reduce maintencance costs, and
make it easier to realize that the Python and JS implementation of this
event system have the same API and behavior.

"""

import re
import sys
import json

from flexx.pyscript import JSString, RawJS, py2js
from flexx.pyscript.parser2 import get_class_definition

from flexx.event._loop import Loop
from flexx.event._action import ActionDescriptor
from flexx.event._reaction import ReactionDescriptor, Reaction
from flexx.event._attribute import Attribute
from flexx.event._property import Property
from flexx.event._emitter import EmitterDescriptor
from flexx.event._component import Component, _mutate_array_js


Object = console = setTimeout = loop = logger = arguments = None  # fool pyflake
undefined = 'UNDEFINED'
reprs = json.dumps


class MetaCollector:
    
    def __init__(self):
        self.meta = {'vars_unknown': set(), 'vars_global': set(),
                     'std_functions': set(), 'std_methods': set(),
                     'linenr': 1e9}
    
    def py2js(self, *args, **kwargs):
        kwargs['inline_stdlib'] = False
        kwargs['docstrings'] = False
        code = py2js(*args, **kwargs)
        return self.update(code)
    
    def update(self, code):
        for key in self.meta:
            if key == 'linenr':
                self.meta[key] = min(self.meta[key], code.meta[key])
            else:
                self.meta[key].update(code.meta[key])
        return code
    
    def attach_meta(self, s):
        s = JSString(s)
        s.meta = self.meta
        return s


## The JS class variants


# Easiest to implement this directly in JS
JS_LOGGER = """
var Logger = function () {
    this.level = 25;
}
var $Logger = Logger.prototype;
$Logger.debug = function (msg) {
    if (this.level <= 10) { console.info(msg); }
};
$Logger.info = function (msg) {
    if (this.level <= 20) { console.info(msg); }
};
$Logger.warn = function (msg) {
    if (this.level <= 30) { console.warn(msg); }
};
$Logger.exception = function (msg) {
    console.error(msg);
};
$Logger.error = function (msg) {
    console.error(msg);
};
var logger = new Logger();
"""


class LoopJS:  # pragma: no cover
    """ JS variant of the Loop class.
    """
    
    # Hide a couple of methods
    integrate = undefined
    integrate_tornado = undefined
    integrate_pyqt4 = undefined
    integrate_pyside = undefined
    _integrate_qt = undefined
    _thread_match = undefined
    
    def __init__(self):
        self._active_components = []
        self.reset()
    
    def _call_soon_func(self, func):
        setTimeout(func, 0)


class ComponentJS:  # pragma: no cover
    """ JS variant of the Component class.
    """
    
    _IS_COMPONENT = True
    _COUNT = 0
    _REACTION_COUNT = 0
    
    def __init__(self, *init_args, **property_values):
        
        RawJS('Component.prototype._COUNT += 1')
        self._id = RawJS("this.__name__ + Component.prototype._COUNT")
        self._disposed = False
        
        # Init some internal variables
        self.__handlers = {}  # reactions connecting to this component
        self.__pending_events = {}
        self.__anonymous_reactions = []
        
        # Create actions
        for i in range(len(self.__actions__)):
            name = self.__actions__[i]
            self.__create_action(self[name], name)
        # Create emitters
        for i in range(len(self.__emitters__)):
            name = self.__emitters__[i]
            self.__handlers[name] = []
            self.__create_emitter(self[name], name)
        # Create properties
        for i in range(len(self.__properties__)):
            name = self.__properties__[i]
            self.__handlers[name] = []
            self.__create_property(name)
        # Create attributes
        for i in range(len(self.__attributes__)):
            name = self.__attributes__[i]
            self.__create_attribute(name)
        
        # Init the values of all properties.
        prop_events = self._comp_init_property_values(property_values)
        
        # Apply user-defined initialization
        with self:
            self.init(*init_args)
        
        # Connect reactions and fire initial events
        self._comp_init_reactions()
        self._comp_init_events(prop_events)
    
    def _comp_init_property_values(self, property_values):
        events = []
        # First process default property values
        for i in range(len(self.__properties__)):
            name = self.__properties__[i]
            value_name = '_' + name + '_value'
            value = self[value_name]
            value = self['_' + name + '_validate'](value)
            self[value_name] = value
            if name not in property_values:
                ev = dict(type=name, new_value=value, old_value=value, mutation='set')
                events.append(ev)
        # Then process property values given at init time
        for name, value in property_values.items():  # is sorted by occurance in py36
            if name not in self.__properties__:
                if name in self.__attributes__:
                    raise AttributeError('%s.%s is an attribute, not a property' %
                                         (self._id, name))
                else:
                    raise AttributeError('%s does not have property %s.' %
                                         (self._id, name))
            if callable(value):
                self._comp_make_implicit_setter(name, value)
                continue
            value = self['_' + name + '_validate'](value)
            self['_' + name + '_value'] = value
            ev = dict(type=name, new_value=value, old_value=value, mutation='set')
            events.append(ev)
        return events
    
    def _comp_make_implicit_setter(self, prop_name, func):
        setter_func = getattr(self, 'set_' + prop_name, None)
        if setter_func is None:
            t = '%s does not have a set_%s() action for property %s.'
            raise TypeError(t % (self._id, prop_name, prop_name)) 
        setter_reaction = lambda: setter_func(func())
        reaction = self.__create_reaction(setter_reaction, 'auto-' + prop_name, [])
        self.__anonymous_reactions.append(reaction)
    
    def _comp_init_reactions(self):
        # Create (and connect) reactions.
        # Implicit reactions need to be invoked to initialize connections.
        for i in range(len(self.__reactions__)):
            name = self.__reactions__[i]
            func = self[name]
            r = self.__create_reaction(func, name, func._connection_strings or ())
            if r.is_explicit() is False:
                ev = dict(source=self, type='', label='')
                loop.add_reaction_event(r, ev)
        # Also invoke the anonymouse implicit reactions
        for i in range(len(self.__anonymous_reactions)):
            r = self.__anonymous_reactions[i]
            if r.is_explicit() is False:
                ev = dict(source=self, type='', label='')
                loop.add_reaction_event(r, ev)
    
    def reaction(self, *connection_strings):
        # The JS version (no decorator functionality)
        
        if len(connection_strings) < 2:
            raise RuntimeError('Component.reaction() (js) needs a function and '
                               'one or more connection strings.')
        
        # Get callable
        if callable(connection_strings[0]):
            func = connection_strings[0]
            connection_strings = connection_strings[1:]
        elif callable(connection_strings[-1]):
            func = connection_strings[-1]
            connection_strings = connection_strings[:-1]
        else:
            raise TypeError('Component.reaction() requires a callable.')
        
        # Verify connection strings
        for i in range(len(connection_strings)):
            s = connection_strings[i]
            if not (isinstance(s, str) and len(s)):
                raise ValueError('Connection string must be nonempty strings.')
        
        # Get function name (Flexx sets __name__ on methods)
        name = RawJS("func.__name__ || func.name || 'anonymous'")
        # name = name.split(' ')[-1].split('flx_')[-1]
        nameparts = RawJS("name.split(' ')")
        nameparts = RawJS("nameparts[nameparts.length-1].split('flx_')")
        name = nameparts[-1]
        return self.__create_reaction_ob(func, name, connection_strings)
    
    def __create_action(self, action_func, name):
        # Keep a ref to the action func, which is a class attribute. The object
        # attribute with the same name will be overwritten with the property below.
        # Because the class attribute is the underlying function, super() works.
        def action():  # this func should return None, so super() works correct
            if loop.is_processing_actions() is True:
                res = action_func.apply(self, arguments)
                if res is not None:
                    logger.warn('Action (%s) is not supposed to return a value' % name)
            else:
                loop.add_action_invokation(action, arguments)
        def getter():
            return action
        def setter(x):
            raise AttributeError('Action %s is not settable' % name)
        opts = {'enumerable': True, 'configurable': True,  # i.e. overloadable
                'get': getter, 'set': setter}
        Object.defineProperty(self, name, opts)
    
    def __create_attribute(self, name):
        def getter():
            return self['_' + name]
        def setter(x):
            raise AttributeError('Cannot set attribute %r' % name)
        opts = {'enumerable': False, 'configurable': False,
                'get': getter, 'set': setter}
        Object.defineProperty(self, name, opts)
    
    def __create_property(self, name):
        private_name = '_' + name + '_value'
        def getter():
            loop.register_prop_access(self, name)
            return self[private_name]
        def setter(x):
            raise AttributeError('Cannot set property %r; properties can only '
                                 'be mutated by actions.' % name)
        opts = {'enumerable': True, 'configurable': True,  # i.e. overloadable
                'get': getter, 'set': setter}
        Object.defineProperty(self, name, opts)
    
    def __create_emitter(self, emitter_func, name):
        # Keep a ref to the emitter func, see comment in __create_action()
        def func():  # this func should return None, so super() works correct
            ev = emitter_func.apply(self, arguments)
            if ev is not None:
                self.emit(name, ev)
        def getter():
            return func
        def setter(x):
            raise AttributeError('Emitter %s is not settable' % name)
        opts = {'enumerable': True, 'configurable': True,  # i.e. overloadable
                'get': getter, 'set': setter}
        Object.defineProperty(self, name, opts)
    
    def __create_reaction(self, reaction_func, name, connection_strings):
        reaction = self.__create_reaction_ob(reaction_func, name, connection_strings)
        def getter():
            return reaction
        def setter(x):
            raise AttributeError('Reaction %s is not settable' % name)
        opts = {'enumerable': True, 'configurable': True,  # i.e. overloadable
                'get': getter, 'set': setter}
        Object.defineProperty(self, name, opts)
        return reaction
        
    def __create_reaction_ob(self, reaction_func, name, connection_strings):
        # Keep ref to the reaction function, see comment in create_action().
        
        # Create function that becomes our "reaction object"
        def reaction():
            return reaction_func.apply(self, arguments)  # arguments == events
        
        # Attach methods to the function object (this gets replaced)
        REACTION_METHODS_HOOK  # noqa
        
        # Init reaction
        that = self
        RawJS("Component.prototype._REACTION_COUNT += 1")
        reaction._id = RawJS("'r' + Component.prototype._REACTION_COUNT")
        reaction._name = name
        reaction._ob1 = lambda : that  # no weakref in JS
        reaction._init(connection_strings, self)
        
        return reaction


## Compile functions

OK_MAGICS = (# Specific to Flexx
             '__attributes__', '__properties__', '__actions__',
             '__emitters__', '__reactions__', '__jsmodule__',
             # Functions that make sense
             '__init__', '__enter__', '__exit__',
             )


def _create_js_class(PyClass, JSClass):
    """ Create the JS code for Loop, Reaction and Component based on their
    Python and JS variants.
    """
    mc = MetaCollector()
    cname = PyClass.__name__
    # Start with our special JS version
    jscode = [mc.py2js(JSClass, cname)]
    jscode[0] = jscode[0].replace('}\n',
                                  '}\nvar $%s = %s.prototype;\n' % (cname, cname),
                                  1
                        ).replace('%s.prototype.' % cname,
                                  '$%s.' % cname)
    # Add the Python class methods
    for name, val in sorted(PyClass.__dict__.items()):
        nameok = name in OK_MAGICS or not name.startswith('__')
        if nameok and not hasattr(JSClass, name):
            if callable(val):
                jscode.append(mc.py2js(val, '$' + cname + '.' + name))
            elif name in OK_MAGICS:
                jscode.append('$' + cname + '.' + name + ' = ' + json.dumps(val))
    # Compose
    jscode = '\n'.join(jscode)
    # Add the reaction methods to component
    if PyClass is Component:
        code = '\n'
        for name, val in sorted(Reaction.__dict__.items()):
            if not name.startswith('__') and callable(val):
                code += mc.py2js(val, 'reaction.' + name, indent=1)[4:] + '\n'
        jscode = jscode.replace('REACTION_METHODS_HOOK', code)
    # Optimizations, e.g. remove threading lock context in Loop
    if PyClass is Loop:
        p = r"this\._lock\.__enter.+?try {(.+?)} catch.+?else.+?exit__.+?}"
        jscode= re.sub(p, r'{/* with lock */\1}', jscode, 0,
                       re.MULTILINE | re.DOTALL)
        jscode= re.sub(r'\$Loop\..+? = undefined;\n', r'', jscode, 0,
                       re.MULTILINE | re.DOTALL)
        jscode = jscode.replace('this._ensure_thread_', '//this._ensure_thread_')
        jscode = jscode.replace('threading.get_ident()', '0')
        jscode = jscode.replace('._local.', '.')
        jscode = jscode.replace('this._thread_match(true);\n', '')
        jscode = jscode.replace('if (_pyfunc_truthy(this._thread_match(false)))', '')
    # Almost done
    jscode = jscode.replace('new Dict()', '{}').replace('new Dict(', '_pyfunc_dict(')
    mc.meta['std_functions'].add('dict')
    return mc.attach_meta(jscode)


def create_js_component_class(cls, cls_name, base_class='Component.prototype'):
    """ Create the JS equivalent of a subclass of the Component class.
    
    Given a Python class with actions, properties, emitters and reactions,
    this creates the code for the JS version of the class. It also supports
    class constants that are int/float/str, or a tuple/list thereof.
    The given class does not have to be a subclass of Component.
    
    This more or less does what ComponentMeta does, but for JS.
    """
    
    assert cls_name != 'Component'  # we need this special class above instead
    
    # Collect meta information of all code pieces that we collect
    mc = MetaCollector()
    
    total_code = []
    funcs_code = []  # functions and emitters go below class constants
    const_code = []
    err = ('Objects on JS Component classes can only be int, float, str, '
           'or a list/tuple thereof. Not %s -> %r.')
    
    total_code.append('\n'.join(get_class_definition(cls_name, base_class)).rstrip())
    prefix = '' if cls_name.count('.') else 'var '
    total_code[0] = prefix + total_code[0]
    prototype_prefix = '$' + cls_name.split('.')[-1] + '.'
    total_code.append('var %s = %s.prototype;' % (prototype_prefix[:-1], cls_name))
    
    # Process class items in original order or sorted by name if we cant
    class_items = cls.__dict__.items()
    if sys.version_info < (3, 6):  # pragma: no cover
        class_items = sorted(class_items)
    
    for name, val in class_items:

        if isinstance(val, ActionDescriptor):
            # Set underlying function as class attribute. This is overwritten
            # by the instance, but this way super() works.
            funcname = name
            # Add function def
            code = mc.py2js(val._func, prototype_prefix + funcname)
            code = code.replace('super()', base_class)  # fix super
            # Tweak if this was an autogenerated action
            # we use flx_ prefixes to indicate autogenerated functions
            if val._func.__name__.startswith('flx_'):
                subname = name[4:] if name.startswith('set_') else name
                code = code.replace("flx_name", "'%s'" % subname)
            funcs_code.append(code.rstrip())
            # Mark to not bind the func
            funcs_code.append(prototype_prefix + funcname + '.nobind = true;')
            funcs_code.append('')
        elif isinstance(val, ReactionDescriptor):
            funcname = name  # funcname is simply name, so that super() works
            # Add function def
            code = mc.py2js(val._func, prototype_prefix + funcname)
            code = code.replace('super()', base_class)  # fix super
            funcs_code.append(code.rstrip())
            # Mark to not bind the func
            funcs_code.append(prototype_prefix + funcname + '.nobind = true;')
            # Add connection strings, but not for implicit reactions
            if val._connection_strings:
                funcs_code.append(prototype_prefix + funcname +
                                  '._connection_strings = ' +
                                  reprs(val._connection_strings))
            funcs_code.append('')
        elif isinstance(val, EmitterDescriptor):
            funcname = name
            # Add function def
            code = mc.py2js(val._func, prototype_prefix + funcname)
            code = code.replace('super()', base_class)  # fix super
            funcs_code.append(code.rstrip())
            # Mark to not bind the func
            funcs_code.append(prototype_prefix + funcname + '.nobind = true;')
            funcs_code.append('')
        elif isinstance(val, Attribute):
            pass
        elif isinstance(val, Property):
            # Mutator and validator functions are picked up as normal functions.
            # Set default value on class.
            default_val = json.dumps(val._default)
            t = '%s_%s_value = %s;'
            const_code.append(t % (prototype_prefix, name, default_val))
        elif name.startswith('__') and name not in OK_MAGICS:
            # These are only magics, since class attributes with double-underscores
            # have already been mangled.
            pass
        elif callable(val):
            # Functions, including methods attached by the meta class
            code = mc.py2js(val, prototype_prefix + name)
            code = code.replace('super()', base_class)  # fix super
            if val.__name__.startswith('flx_'):
                subname = name[8:] if name.startswith('_mutate_') else name
                code = code.replace("flx_name", "'%s'" % subname)
            funcs_code.append(code.rstrip())
            funcs_code.append('')
        else:
            # Static simple (json serializable) attributes, e.g. __actions__ etc.
            try:
                serialized = json.dumps(val)
            except Exception as err:  # pragma: no cover
                raise ValueError('Attributes on JS Component class must be '
                                 'JSON compatible.\n%s' % str(err))
            const_code.append(prototype_prefix + name + ' = ' + serialized)
    
    if const_code:
        total_code.append('')
        total_code.extend(const_code)
    if funcs_code:
        total_code.append('')
        total_code.extend(funcs_code)
    total_code.append('')
    
    # Return string with meta info (similar to what py2js returns)
    mc.meta['vars_unknown'].discard('flx_name')
    return mc.attach_meta('\n'.join(total_code))


# Generate the code
mc = MetaCollector()
JS_FUNCS = mc.py2js(_mutate_array_js) + '\nvar mutate_array = _mutate_array_js;\n'
JS_LOOP = mc.update(_create_js_class(Loop, LoopJS)) + '\nvar loop = new Loop();\n'
JS_COMPONENT = mc.update(_create_js_class(Component, ComponentJS))
JS_EVENT = JS_FUNCS + JS_LOGGER + JS_LOOP + JS_COMPONENT
JS_EVENT = mc.attach_meta(JS_EVENT.replace('    ', '\t'))
del mc


if __name__ == '__main__':
    
    # Testing ...
    from flexx import event
    
    class Foo(Component):
        
        __x = 3
        foo = event.StringProp('asd', settable=True)
        
        @event.action
        def do_bar(self, v=0):
            print(v)
        
        @event.reaction
        def react2foo(self):
            print(self.foo)
        
        def __xx(self):
            pass
        
    
    toprint = JS_COMPONENT  # or JS_LOOP JS_COMPONENT JS_EVENT
    print('-' * 80)
    print(toprint)  
    print('-' * 80)
    print(len(toprint), 'of', len(JS_EVENT), 'bytes in total')  # 29546 before refactor
    print('-' * 80)
    
    print(create_js_component_class(Foo, 'Foo'))
