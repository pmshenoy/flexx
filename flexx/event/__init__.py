"""
The event module provides a system for properties and events,
to let different components of an application react to each-other and
to user input.

In short:

* The :class:`Component <flexx.event.Component>` class provides a base class
  which can be subclassed to create the different components of an app.
* Each component has :class:`properties <flexx.event.Property>` to reflect
  the state of the component.
* Properties can only be mutated by :class:`actions <flexx.event.action>`.
  Calling (i.e. invoking) an action will not apply the action at once; actions
  are processed in batches.
* When properties change, corresponding :class:`reactions <flexx.event.reaction>` 
  will be invoked. The reactions are processed when all pending actions
  are done. This means that during processing reactions, the state never changes.
* Reactions can also react to events generated by :func:`emitters <flexx.event.emitter>`.

.. image:: https://docs.google.com/drawings/d/e/2PACX-1vSHp4iha6CTgjsQ52x77gn0hqQP4lZD-bcaVeCfRKhyMVtaLeuX5wpbgUGaIE0Sce_kBT9mqrfEgQxB/pub?w=503


Event
-----

An event is something that has occurred at a certain moment in time,
such as the mouse being pressed down or a property changing its value.
In this framework events are represented with dictionary objects that
provide information about the event (such as what button was pressed,
or the old and new value of a property). A custom :class:`Dict <flexx.event.Dict>`
class is used that inherits from ``dict`` but allows attribute access,
e.g. ``ev.button`` as an alternative to ``ev['button']``.


The Component class
-------------------

The :class:`Component <flexx.event.Component>` class provides a base
class for objects that have properties, actions, reactions and emitters.
E.g. a ``flexx.ui.Widget`` inherits from ``flexx.app.Model``, which inherits
from ``flexx.event.Component``.

Events are emitted using the :func:`emit() <flexx.event.Component.emit>`
method, which accepts a name for the type of the event, and optionally a dict,
e.g. ``emitter.emit('mouse_down', dict(button=1, x=103, y=211))``.

The Component object will add two attributes to the event: ``source``,
a reference to the Component object itself, and ``type``, a string
indicating the type of the event.

As a user, you generally do not need to emit events explicitly; events are
automatically emitted, e.g. when setting a property.


Properties
----------

:class:`Properties <flexx.event.Property>` can be defined using one of the several property classes:

.. code-block:: python

    class MyObject(event.Component):
       
        foo = event.AnyProp(8, settable=True, doc='This prop can have any value')
        bar = event.IntProp()

Properties accept one positional arguments to set the default value. If not
given, a sensible default value is used that depends on the type of property.
The ``foo`` property above is marked as settable, so that the class will have
a ``set_foo()`` action. Docs for a property can be added too. Properties
are readonly: they can can only be mutated by actions.

Property values can be initialized when a component is created (also
for non-settable properties):

.. code-block:: python

    c = MyComponent(foo=42)

A similar pattern is to set the initial value to a function, as a way to create
an "implicit reaction" that sets the property. In the example below, the label
text will be automatically updated when the username property changes:

.. code-block:: python

    c = UiLabel(text=lambda: self.username)

An event is emitted every time that a property changes. This event has attributes
``old_value`` and ``new_value`` (except for in-place array mutations, as
explained below). The first event for a property will have the same value
for ``old_value`` and ``new_value``.


Actions
-------

:class:`Actions <flexx.event.action>` can be defined to mutate properties:

.. code-block:: python

    class MyObject(event.Component):
       
        foo = event.AnyProp(8, settable=True, doc='This prop can have any value')
        bar = event.IntProp()
        
        @event.action
        def increase_bar(self):
            self._mutate_bar(self.bar + 1)
            # shorthand for self._mutate('bar', self.bar + 1)

Actions can have any number of arguments. Note that calling an action will not
apply it immediatelt, unless it is called from another action.

Mutations are done via the ``_mutate()`` method, or by the auto-generated
``_mutate_xx()`` methods. Mutations can only be done from an action. Trying
to do so otherwise will result in an error.


Fine grained mutations
----------------------

The above shows the simple and most common use of mutations. However,
mutations can also be done in-place:

.. code-block:: python

    class MyObject(event.Component):
       
        items = event.ListProp()
        
        def add_item(self, item):
            self._mutate_items([item], 'insert', len(self.items))

This allows more fine-grained control over state updates, which can also
be handled by reactions in much more efficient ways. The types of mutations are
'set' (the default), 'insert', 'replace', and 'remove'. In the latter, the
provided value is the number of elements to remove. For the others it must
be a list of elements to set/insert/replace at the specified index.


Emitters
--------

:func:`Emitters <flexx.event.emitter>` make it easy to generate events.
Similar to actions, they are created with a decorator.

.. code-block:: python

    class MyObject(event.Component):
    
        @event.emitter
        def mouse_down(self, js_event):
            ''' Event emitted when the mouse is pressed down.
            '''
            return dict(button=js_event.button)

Emitters can have any number of arguments and should return a dictionary,
which will get emitted as an event, with the event type matching the name
of the emitter.

Note that stricly speaking emitters are not necessary as ``Component.emit()``
can be used to generate an event. However, they provide a mechanism to 
generate an event based on certain input data and to document events.


Reactions
---------

:func:`Reactions <flexx.event.reaction>` are used to react to events and
changes in properties, using an underlying handler function:


.. code-block:: python

    class MyObject(event.Component):
       
        first_name = event.StringProp(settable=True)
        last_name = event.StringProp(settable=True)
        
        @event.reaction('first_name', last_name)
        def greet(self, *events):
            print('hi', self.first_name, self.last_name)
        
        @event.reaction('!foo')
        def handle_foo(self, *events):
            for ev in events:
                print(ev)


This example demonstrates a few concepts. Firstly, the reactions are
connected via *connection-strings* that specifies the types of the
event; in this case the ``greeter`` reaction is connected to "first_name" and
"last_name", and ``handler_foo`` is connected to the event-type "foo" of the
object. This connection-string can also be a path, e.g.
"sub.subsub.event_type". This allows for some powerful mechanics, as
discussed in the section on dynamism.

One can also see that the handler function accepts ``*events`` argument.
This is because handlers can be passed zero or more events. If a handler
is called manually (e.g. ``ob.handle_foo()``) it will have zero events.
When called by the event system, it will have at least 1 event. When
e.g. a property is set twice, the handler function will be called
just once, with multiple events. It is up to the programmer to determine
what to do. If all events need to be processed individually,
use ``for ev in events: ...``.

In most cases, you will connect to events that are known beforehand,
like those corresponding to properties and emitters. 
If you connect to an event that is not known (as ``handle_foo`` in the example
above) Flexx will display a warning. Use `'!foo'` as a connection string
(i.e. prepend an exclamation mark) to suppress such warnings.

Another useful feature of the event system is that a reaction can connect to
multiple events at once, as the ``greet`` reaction does.

To create a reaction from a normal function, use the
:func:`Component.reacion() <flexx.event.Component.reaction>` method:

.. code-block:: python

    c = MyComponent()
    
    # Using a decorator
    @c.reaction('foo', 'bar')
    def handle_func1(self, *events):
        print(events)
    
    # Explicit notation
    def handle_func2(self, *events):
        print(events)
    c.reaction(handle_func2, 'foo', 'bar')  # the func can be the first or last argument


Implicit reactions
==================

One can also create reactions without specifying connection strings. Flexx
will then figure out what properties are being accessed and will call the
reaction whenever one of these change. This is a convenient feature, but
should be avoided when a lot (say hundreds) of properties are accessed.

.. code-block:: python

    class MyObject(event.Component):
       
        first_name = event.StringProp(settable=True)
        last_name = event.StringProp(settable=True)
        
        @event.reaction
        def greet(self):
            print('hi', self.first_name, self.last_name)

A similar useful feature is to assign a property (at initialization) using a
function. In such a case, the function is turned into an implicit reaction.
This can be convenient to easily connect different parts of an app.

.. code-block:: python

    class MyObject(event.Component):
       
        first_name = event.StringProp(settable=True)
        last_name = event.StringProp(settable=True)
    
    person = MyObject()
    label = UiLabel(text=lambda: person.first_name)


Reacting to in-place mutations
==============================

In-place mutations to lists or arrays can be reacted to by processing
the events one by one:

.. code-block:: python
    
    class MyComponent(event.Component):
    
        @event.reaction('other.data')
        def track_data(self, *events):
            for ev in events:
                if ev.mutation == 'set':
                    self.data[:] = ev.objects
                elif ev.mutation == 'insert':
                    self.data[ev.index:ev.index] = ev.objects
                elif ev.mutation == 'remove':
                    self.data[ev.index:ev.index+ev.objects] = []  # objects is int here
                elif ev.mutation == 'replace':
                    self.data[ev.index:ev.index+len(ev.objects)] = ev.objects
                else:
                    assert False, 'we cover all mutations'

For convenience, the mutation can also be "replicated" using the
``event.mutate_array()`` function.


Connection string syntax
========================

The strings used to connect events follow a few simple syntax rules:

* Connection strings consist of parts separated by dots, thus forming a path.
  If an element on the path is a property, the connection will automatically
  reset when that property changes (a.k.a. dynamism, more on this below).
* Each part can end with one star ('*'), indicating that the part is a list
  and that a connection should be made for each item in the list. 
* With two stars, the connection is made *recursively*, e.g. "children**"
  connects to "children" and the children's children, etc.
* Stripped of '*', each part must be a valid identifier (ASCII).
* The total string optionally has a label suffix separated by a colon. The
  label itself may consist of any chars.
* The string can have a "!" at the very start to suppress warnings for
  connections to event types that Flexx is not aware of at initialization
  time (i.e. not corresponding to a property or emitter).

An extreme example could be ``"!foo.children**.text:mylabel"``, which connects
to the "text" event of the children (and their children, and their children's
children etc.) of the ``foo`` attribute. The "!" is common in cases like
this to suppress warnings if not all children have a ``text`` event/property.

Labels are a feature that makes it possible to infuence the order by
which event handlers are called, and provide a means to disconnect
specific (groups of) handlers. The label is part of the connection
string: 'foo.bar:label'.

.. code-block:: python
    
    class MyObject(event.Component):
    
        @event.reaction('foo')
        def given_foo_handler(*events):
                ...
        
        @event.reaction('foo:aa')
        def my_foo_handler(*events):
            # This one is called first: 'aa' < 'given_f...'
            ...

When an event is emitted, the event is added to the pending events of
the handlers in the order of a key, which is the label if present, and
otherwise the name of the handler. Note that this does not guarantee
the order in case a handler has multiple connections: a handler can be
scheduled to handle its events due to another event, and a handler
always handles all its pending events at once.

The label can also be used in the
:func:`disconnect() <flexx.event.Component.disconnect>` method:

.. code-block:: python

    @h.reaction('foo:mylabel')
    def handle_foo(*events):
        ...
    
    ...
    
    h.disconnect('foo:mylabel')  # don't need reference to handle_foo


Dynamism
========

Dynamism is a concept that allows one to connect to events for which
the source can change. For the following example, assume that ``Node``
is a ``Component`` subclass that has properties ``parent`` and
``children``.

.. code-block:: python
    
    main = Node()
    main.parent = Node()
    main.children = Node(), Node()
    
    @main.reaction('parent.foo')
    def parent_foo_handler(*events):
        ...
    
    @main.reaction('children*.foo')
    def children_foo_handler(*events):
        ...

The ``parent_foo_handler`` gets invoked when the "foo" event gets
emitted on the parent of main. Similarly, the ``children_foo_handler``
gets invoked when any of the children emits its "foo" event. Note that
in some cases you might also want to connect to changes of the ``parent``
or ``children`` property itself.

The event system automatically reconnects reactions when necessary. This
concept makes it very easy to connect to the right events without the
need for a lot of boilerplate code.

Note that the above example would also work if ``parent`` would be a
regular attribute instead of a property, but the reaction would not be
automatically reconnected when it changed.


Patterns
--------

This event system is quite flexible and designed to cover the needs
of a variety of event/messaging mechanisms. This section discusses
how this system relates to some common patterns, and how these can be
implemented.

Observer pattern
================

The idea of the observer pattern is that observers keep track (the state
of) of an object, and that object is agnostic about what it's tracked by.
For example, in a music player, instead of writing code to update the
window-title inside the function that starts a song, there would be a
concept of a "current song", and the window would listen for changes to
the current song to update the title when it changes.

In ``flexx.event``, a ``Component`` object keeps track of its observers
(reactions) and notifies them when there are changes. In our music player
example, there would be a property "current_song", and a reaction to
take action when it changes.

As is common in the observer pattern, the reactions keep track of the
reactions that they observe. Therefore both ``Reaction`` and ``Component``
objects have a ``dispose()`` method for cleaning up.

Signals and slots
=================

The Qt GUI toolkit makes use of a mechanism called "signals and slots" as
an easy way to connect different components of an application. In
``flexx.event`` signals translate to properties and assoctate setter actions,
and slots to the reactions that connect to them.

Overloadable event handlers
===========================

In Qt, the "event system" consists of methods that handles an event, which
can be overloaded in subclasses to handle an event differently. In
``flexx.event``, reactions can similarly be re-implemented in subclasses,
and these can call the original handler using ``super()`` if needed.

Publish-subscribe pattern
==========================

In pub-sub, publishers generate messages identified by a 'topic', and
subscribers can subscribe to such topics. There can be zero or more publishers
and zero or more subscribers to any topic. 

In ``flexx.event`` a `Component` object can play the role of a broker.
Publishers can simply emit events. The event type represents the message
topic. Subscribers are represented by handlers.

"""

import logging
logger = logging.getLogger(__name__)
del logging

# flake8: noqa
from ._dict import Dict
from ._loop import loop
from ._action import Action, action
from ._reaction import Reaction, reaction
from ._emitter import emitter
from ._attribute import Attribute
from ._property import *
from ._component import Component, mutate_array

# from ._component import new_type, with_metaclass
