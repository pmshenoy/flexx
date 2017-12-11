"""
The HVLayout and its subclasses provide a simple mechanism to horizontally
or vertically stack child widgets.


.. UIExample:: 250
    
    from flexx import ui
    
    class Example(ui.Widget):
    
        def init(self):
            
            with ui.VBox():
                
                ui.Label(text='Flex 0 0 0')
                with ui.HBox(flex=0):
                    self.b1 = ui.Button(text='Hola', flex=0)
                    self.b2 = ui.Button(text='Hello world', flex=0)
                    self.b3 = ui.Button(text='Foo bar', flex=0)
                
                ui.Label(text='Flex 1 0 3')
                with ui.HBox(flex=0):
                    self.b1 = ui.Button(text='Hola', flex=1)
                    self.b2 = ui.Button(text='Hello world', flex=0)
                    self.b3 = ui.Button(text='Foo bar', flex=3)
                
                ui.Label(text='padding 15 (around layout)')
                with ui.HBox(flex=0, padding=15):
                    self.b1 = ui.Button(text='Hola', flex=1)
                    self.b2 = ui.Button(text='Hello world', flex=1)
                    self.b3 = ui.Button(text='Foo bar', flex=1)
                
                ui.Label(text='spacing 15 (inter-widget)')
                with ui.HBox(flex=0, spacing=15):
                    self.b1 = ui.Button(text='Hola', flex=1)
                    self.b2 = ui.Button(text='Hello world', flex=1)
                    self.b3 = ui.Button(text='Foo bar', flex=1)
                
                ui.Widget(flex=1)
                ui.Label(text='Note the spacer Widget above')


A similar example using a Split / Fix layout:

.. UIExample:: 250
    
    from flexx import ui
    
    class Example(ui.Widget):
        def init(self):
            with ui.VSplit():
                
                ui.Label(text='Flex 0 0 0', style='')
                with ui.HFix(flex=0):
                    self.b1 = ui.Button(text='Hola', flex=0)
                    self.b2 = ui.Button(text='Hello world', flex=0)
                    self.b3 = ui.Button(text='Foo bar', flex=0)
                
                ui.Label(text='Flex 1 0 3')
                with ui.HFix(flex=0):
                    self.b1 = ui.Button(text='Hola', flex=1)
                    self.b2 = ui.Button(text='Hello world', flex=0)
                    self.b3 = ui.Button(text='Foo bar', flex=3)
                
                ui.Label(text='spacing 10 (inter-widget)')
                with ui.HFix(flex=0, spacing=20):
                    self.b1 = ui.Button(text='Hola', flex=1)
                    self.b2 = ui.Button(text='Hello world', flex=1)
                    self.b3 = ui.Button(text='Foo bar', flex=1)
                
                ui.Widget(flex=1)


Interactive Box layout example:

.. UIExample:: 200
    
    from flexx import ui, event
    
    class Example(ui.HBox):
        def init(self):
            self.b1 = ui.Button(text='Horizontal', flex=0)
            self.b2 = ui.Button(text='Vertical', flex=1)
            self.b3 = ui.Button(text='Horizontal reversed', flex=2)
            self.b4 = ui.Button(text='Vertical reversed', flex=3)
        
        class JS:
            
            @event.connect('b1.mouse_down')
            def _to_horizontal(self, *events):
                self.orientation = 'h'
            
            @event.connect('b2.mouse_down')
            def _to_vertical(self, *events):
                self.orientation = 'v'
            
            @event.connect('b3.mouse_down')
            def _to_horizontal_rev(self, *events):
                self.orientation = 'hr'
            
            @event.connect('b4.mouse_down')
            def _to_vertical_r(self, *events):
                self.orientation = 'vr'


A classic high level layout:


.. UIExample:: 300

    from flexx import ui
    
    
    class Content(ui.Widget):
        def init(self):
                # Here we use Box layout, because we care about natural size
                
                with ui.HBox():
                    ui.Widget(flex=1)  # spacer
                    ui.Button(text='hello')
                    ui.Widget(flex=1)  # spacer
    
    
    class SideWidget(ui.Label):
        CSS = '.flx-SideWidget {background: #aaf; border: 2px solid black;}'
    
    
    class Example(ui.Widget):
    
        def init(self):
            # Here we use Split layout, because we define high-level layout
            
            with ui.VSplit():
                SideWidget(text='Header', flex=0, base_size=100)
                with ui.HSplit(flex=1):
                    SideWidget(text='Left', flex=0, base_size=100)
                    Content(flex=1)
                    SideWidget(text='Right', flex=0, base_size=100)
                SideWidget(text='Bottom', flex=0, base_size=100)

"""

from ... import event
from ...pyscript import RawJS
from . import Layout


# _phosphor_boxpanel = RawJS("flexx.require('phosphor/lib/ui/boxpanel')")


class OrientationProp(event.Property):
    """ A property that represents a pair of float values, which can also be
    set using a scalar.
    """
    
    _default = 'h'
    
    def _validate(self, v):
        if isinstance(v, str):
            v = v.lower().replace('-', '')
        v = {'horizontal': 'h', 0: 'h', 'lefttoright': 'h',
             'vertical': 'v', 1: 'v', 'toptobottom': 'v',
             'righttoleft': 'hr', 'bottomtotop': 'vr'}.get(v, v)
        if v not in ('h', 'v', 'hr', 'vr'):
            raise ValueError('%s.orientation got unknown value %r' % (self.id, v))
        return v


class HVLayout(Layout):
    """ Layout to distribute space for widgets horizontally or vertically. 
    
    This is a versatile layout class which can operate in different
    orientations (horizontal, vertical, reversed), and in different modes:
    
    In 'fix' mode, all available space is simply distributed corresponding
    to the children's flex values. This can be convenient to e.g. split
    a layout in two halves.
    
    In 'box' mode, each widget gets at least its natural size (if available),
    and any *additional* space is distributed corresponding to the children's
    flex values. This is convenient for low-level layout of widgets, e.g. to
    align  one or more buttons. It is common to use an empty ``Widget`` with a
    flex of 1 to fill up any remaining space. This mode is based on CSS flexbox.
    
    In 'split' mode, all available space is initially distributed corresponding
    to the children's flex values. The splitters between the child widgets
    can be dragged by the user, and positioned via an action. This is useful
    to give the user more control over the (high-level) layout.
    
    In all modes, the layout is constrained by the minimum and maximum size
    of the child widgets (as set via style/CSS).
    
    Also see the convenience classes: HFix, VFix, HBox, VBox, HSplit, VSplit.
    """
    
    _DEFAULT_ORIENTATION = 'h'
    _DEFAULT_MODE = 'box'
    
    CSS = """
    
    /* === for box layout === */
    
    .flx-box {
        display: -webkit-flex;
        display: -ms-flexbox;  /* IE 10 */
        display: -ms-flex;     /* IE 11 */
        display: -moz-flex;
        display: flex;
        
        /* How space is divided when all flex-factors are 0:
           start, end, center, space-between, space-around */
        -webkit-justify-content: space-around;
        -ms-justify-content: space-around;
        -moz-justify-content: space-around;
        justify-content: space-around;
        
        /* How items are aligned in the other direction:
           center, stretch, baseline */
        -webkit-align-items: stretch;  
        -ms-align-items: stretch;
        -moz-align-items: stretch;
        align-items: stretch;
    }
    
    .flx-box.flx-horizontal {
        -webkit-flex-flow: row;
        -ms-flex-flow: row;
        -moz-flex-flow: row;
        flex-flow: row;
        width: 100%;
    }
    .flx-box.flx-vertical {
        -webkit-flex-flow: column;
        -ms-flex-flow: column;
        -moz-flex-flow: column;
        flex-flow: column;
        height: 100%; width: 100%;
    }
    .flx-box.flx-horizontal.flx-reversed {
        -webkit-flex-flow: row-reverse;
        -ms-flex-flow: row-reverse;
        -moz-flex-flow: row-reverse;
        flex-flow: row-reverse;
    }
    .flx-box.flx-vertical.flx-reversed {
        -webkit-flex-flow: column-reverse;
        -ms-flex-flow: column-reverse;
        -moz-flex-flow: column-reverse;
        flex-flow: column-reverse;
    }
    
    /* Make child widgets (and layouts) size correctly */
    .flx-box.flx-horizontal > .flx-Widget {
        height: auto;
        width: auto;
    }
    .flx-box.flx-vertical > .flx-Widget {
        width: auto;
        height: auto;
    }
    
    /* If a boxLayout is in a compound widget, we need to make that widget
       a flex container (done with JS in Widget class), and scale here */
    .flx-Widget > .flx-box {
        flex-grow: 1;
        flex-shrink: 1;
    }
    
    /* === For split and fix layout === */
    
    .flx-split > .flx-Widget {
        position: absolute;
    }
    
    .flx-split.flx-horizontal > .flx-split-sep {
        cursor: ew-resize;  
    }
    .flx-split.flx-vertical > .flx-split-sep {
        cursor: ns-resize;
    }
    .flx-split-sep {
        z-index: 2;
        position: absolute;
        -webkit-user-select: none;
        -moz-user-select: none;
        -ms-user-select: none;
        user-select: none;
        box-sizing: border-box;
        /*background: rgba(0, 0, 0, 0);*/
        background: #fff;  /* hide underlying widgets */
    }
    """
    
    mode = event.StringProp('box', settable=True, doc="""
        The mode in which this layout operates:
        
        * fix: all available space is distributed corresponding to the flex values.
        * box: each widget gets at least its natural size, and additional space
          is distributed corresponding to the flex values.
        * split: available space is initially distributed correspondong to the
          flex values, and can be modified by the user by dragging the splitters.
        """)
    
    orientation = OrientationProp(settable=True, doc="""
        The orientation of the child widgets. 'h' or 'v' for horizontal and
        vertical, or their reversed variants 'hr' and 'vr'. Settable with
        values: 0, 1, 'h', 'v', 'hr', 'vr', 'horizontal', 'vertical',
        'left-to-right', 'right-to-left', 'top-to-bottom', 'bottom-to-top'
        (insensitive to case and use of dashes).
        """)
    
    spacing = event.FloatProp(4, settable=True, doc="""
        The space between two child elements (in pixels).
        """)
    
    padding = event.FloatProp(1, settable=True, doc="""
        The empty space around the layout (in pixels).
        """)
    
    def __init__(self, *args, **kwargs):
        kwargs['mode'] = kwargs.get('mode', self._DEFAULT_MODE)
        kwargs['orientation'] = kwargs.get('orientation', self._DEFAULT_ORIENTATION)
        
        self._seps = []
        self._dragging = None
        
        super().__init__(*args, **kwargs)
        
        if 'Split' in self._id and 'spacing' not in kwargs:
            self.set_spacing(8)
    
    ## Actions
    
    @event.action
    def set_from_flex_values(self):
        """ Set the divider positions corresponding to the children's flex values.
        Only for split-mode.
        """
        if self.mode == 'box':
            return
        
        # Collect flexes
        sizes = []
        dim = 0 if 'h' in self.orientation else 1
        for widget in self.children:
            sizes.append(widget.flex[dim])
        
        # Normalize size, so that total is one
        if size_sum == 0:
            sizes = [1/len(sizes) for j in sizes]
        else:
            size_sum = sum(sizes)
            sizes = [j/size_sum for j in sizes]
        # todo: pyscript bug: if I use i here, it takes on value set above (0)
        
        # Turn sizes into positions
        total_size, available_size = self._get_available_size()
        positions = []
        pos = 0
        for i in range(len(sizes) - 1):
            pos = pos + sizes[i]
            abs_pos = max(0, min(1, pos)) * available_size  # Make absolute
            positions.append(abs_pos)
        
        # Apply (we want to be able to call this in fix-mode)
        self.emit('_rerender', dict(positions=positions))
    
    @event.action
    def set_divider_positions(self, *positions):
        """ Set relative divider posisions (values between 0 and 1).
        Only for split-mode.
        """
        if self.mode != 'split':
            return
        
        total_size, available_size = self._get_available_size()
        positions = [max(0, min(1, pos)) * available_size for pos in positions]
        self.emit('_rerender', dict(positions=positions))
    
    ## General reactions and hooks
    
    @event.reaction('mode')
    def __set_mode(self, *events):
        self._update_layout(self.children)  # pass children to reset their style
        
        if self.mode == 'box':
            self.outernode.classList.remove('flx-split')
            self.outernode.classList.add('flx-box')
            self._set_box_child_flexes()
            self._set_box_spacing()
        else:
            self.outernode.classList.remove('flx-box')
            self.outernode.classList.add('flx-split')
            self.set_from_flex_values()
    
    @event.reaction('orientation')
    def __set_orientation(self, *events):
        ori = self.orientation
        if 'h' in ori:
            self.outernode.classList.add('flx-horizontal')
            self.outernode.classList.remove('flx-vertical')
        else:
            self.outernode.classList.remove('flx-horizontal')
            self.outernode.classList.add('flx-vertical')
        if 'r' in ori:
            self.outernode.classList.add('flx-reversed')
        else:
            self.outernode.classList.remove('flx-reversed')
        
        for widget in self.children:
            widget.check_real_size()
        self._split_rerender()
    
    @event.reaction('padding')
    def __set_padding(self, *events):
        self.outernode.style['padding'] = self.padding + 'px'
        for widget in self.children:
            widget.check_real_size()
        self._split_rerender()
    
    def _update_layout(self, old_children, new_children=None):
        """ Can be overloaded in (Layout) subclasses.
        """
        children = self.children
        use_seps = self.mode == 'split'
        if self.mode == 'box':
            self._ensure_seps(0)
        else:
            self._ensure_seps(len(children) - 1)
        
        # Reset style of old children
        for child in old_children:
            for n in ['margin', 'left', 'width', 'top', 'height']:
                child.outernode.style[n] = ''
        
        # Remove any children
        while len(self.outernode.children) > 0:
            c =self.outernode.children[0]
            self.outernode.removeChild(c)
        
        # Add new children and maybe interleave with separater widgets
        for i in range(len(children)):
            self.outernode.appendChild(children[i].outernode)
            if use_seps and i < len(self._seps):
                self.outernode.appendChild(self._seps[i])
    
    def _ensure_seps(self, n):
        """ Ensure that we have exactly n seperators.
        """
        n = max(0, n)
        to_remove = self._seps[n:]
        self._seps = self._seps[:n]
        # hv = 'flx-horizontal' if 'h' in self.orientation else 'flx-vertical'
        while len(self._seps) < n:
            sep = window.document.createElement('div')
            self._seps.append(sep)
            sep.i = len(self._seps) - 1
            sep.classList.add('flx-split-sep')
            # sep.classList.add(hv)
            sep.rel_pos = 0
            sep.abs_pos = 0
    
    ## Reactions for box mode
    
    @event.reaction('orientation', 'children', 'children*.flex')
    def _set_box_child_flexes(self, *events):
        if self.mode != 'box':
            return
        ori = self.orientation
        i = 0 if ori in (0, 'h', 'hr') else 1
        for widget in self.children:
            _applyBoxStyle(widget.outernode, 'flex-grow', widget.flex[i])
            _applyBoxStyle(widget.outernode, 'flex-shrink', widget.flex[i] or 1)  # default value is 1
        for widget in self.children:
            widget.check_real_size()
    
    @event.reaction('spacing', 'orientation', 'children')
    def _set_box_spacing(self, *events):
        if self.mode != 'box':
            return 
        ori = self.orientation
        children_events = [ev for ev in events if ev.type == 'children']
        old_children = children_events[0].old_value if children_events else []
        children = self.children
        # Reset
        for child in children:
            child.outernode.style['margin-top'] = ''
            child.outernode.style['margin-left'] = ''
        for child in old_children:
            child.outernode.style['margin-top'] = ''
            child.outernode.style['margin-left'] = ''
        # Set
        margin = 'margin-top' if ori in (1, 'v', 'vr') else 'margin-left'
        if children.length:
            if ori in ('vr', 'hr'):
                children[-1].outernode.style[margin] = '0px'
                for child in children[:-1]:
                    child.outernode.style[margin] = self.spacing + 'px'
            else:
                children[0].outernode.style[margin] = '0px'
                for child in children[1:]:
                    child.outernode.style[margin] = self.spacing + 'px'
        for widget in children:
            widget.check_real_size()
    
    ## Reactions and machinerey for fix/split mode
    
    def _get_available_size(self):
        bar_size = self.spacing
        pad_size = self.padding
        if 'h' in self.orientation:
            total_size = self.outernode.clientWidth
        else:
            total_size = self.outernode.clientHeight
        return total_size, total_size - bar_size * len(self._seps) - 2 * pad_size
    
    @event.reaction('spacing')
    def __spacing_changed(self, *events):
        self._split_rerender()
    
    @event.reaction('children', 'children*.flex')
    def _set_split_from_flexes(self, *events):
        if self.mode != 'box':
            self.set_from_flex_values()
    
    def _split_rerender(self):
        """ Rerender, keeping the relative positions equal.
        """
        if self.mode == 'box':
            return
        total_size, available_size = self._get_available_size()
        positions = [sep.rel_pos * available_size for sep in self._seps]
        self.emit('_rerender', dict(positions=positions))
    
    @event.reaction('!_rerender')
    def __rerender(self, *events):
        """ Set the slider positions, subject to constraints.
        """
        if self.mode == 'box':
            return
        positions = events[-1].positions  # absolute positions
        children = self.children
        bar_size = self.spacing
        pad_size = self.padding
        total_size, available_size = self._get_available_size()
        ori = self.orientation
        
        if len(children) != len(self._seps) + 1:
            return
        
        # Make positions equally long
        while len(positions) < len(self._seps):
            positions.append(None)
        
        # Apply positions
        for i in range(len(self._seps)):
            pos = positions[i]
            if pos is not None:
                if pos < 0:
                    pos = available_size - pos
                pos = max(0, min(available_size, pos))
                self._seps[i].abs_pos = pos
                
                # Move seps on the left, as needed
                ref_pos = pos
                for j in reversed(range(0, i)):
                    if positions[j] is None:
                        cur = self._seps[j].abs_pos
                        mi, ma = _get_min_max(ori, available_size, children[j+1].outernode)
                        self._seps[j].abs_pos = ref_pos = max(ref_pos - ma, min(ref_pos - mi, cur))
                # Move seps on the right, as needed
                ref_pos = pos
                for j in range(i+1, len(self._seps)):
                    if positions[j] is None:
                        cur = self._seps[j].abs_pos
                        mi, ma = _get_min_max(ori, available_size, children[j].outernode)
                        self._seps[j].abs_pos = ref_pos = max(ref_pos + mi, min(ref_pos + ma, cur))
        
        # Correct seps from the right edge
        ref_pos = available_size
        for j in reversed(range(0, len(self._seps))):
            cur = self._seps[j].abs_pos
            mi, ma = _get_min_max(ori, available_size, children[j+1].outernode)
            self._seps[j].abs_pos = ref_pos = max(ref_pos - ma, min(ref_pos - mi, cur))
        
        # Correct seps from the left edge
        ref_pos = 0
        for j in range(0, len(self._seps)):
            cur = self._seps[j].abs_pos
            mi, ma = _get_min_max(ori, available_size, children[j].outernode)
            self._seps[j].abs_pos = ref_pos = max(ref_pos + mi, min(ref_pos + ma, cur))
        
        # Store relative posisions
        for j in range(0, len(self._seps)):
            self._seps[j].rel_pos = self._seps[j].abs_pos / available_size
        
        # Apply
        is_horizonal = 'h' in ori
        is_reversed = 'r' in ori
        offset = pad_size
        last_sep_pos = 0
        for i in range(len(children)):
            widget = children[i]
            ref_pos = self._seps[i].abs_pos if i < len(self._seps) else available_size
            size = ref_pos - last_sep_pos
            if True:
                # Position widget
                pos = last_sep_pos + offset
                if is_reversed is True:
                    pos = total_size - pos - size
                if is_horizonal is True:
                    widget.outernode.style.left = pos + 'px'
                    widget.outernode.style.width = size + 'px'
                    widget.outernode.style.top = pad_size + 'px'
                    widget.outernode.style.height = 'calc(100% - ' + 2*pad_size + 'px)'
                else:
                    widget.outernode.style.left = pad_size + 'px'
                    widget.outernode.style.width = 'calc(100% - ' + 2*pad_size + 'px)'
                    widget.outernode.style.top = pos + 'px'
                    widget.outernode.style.height = size + 'px'
            if i < len(self._seps):
                # Position divider
                sep = self._seps[i]
                pos = sep.abs_pos + offset
                if is_reversed is True:
                    pos = total_size - pos - bar_size
                if is_horizonal is True:
                    sep.style.left = pos + 'px'
                    sep.style.width = bar_size + 'px'
                    sep.style.top = '0'
                    sep.style.height = '100%'
                else:
                    sep.style.top = pos + 'px'
                    sep.style.height = bar_size + 'px'
                    sep.style.left = '0'
                    sep.style.width = '100%'
                offset += bar_size
                last_sep_pos = sep.abs_pos
    
    @event.emitter
    def mouse_down(self, e):
        if self.mode == 'split' and e.target.classList.contains("flx-split-sep"):
            e.stopPropagation()
            sep = e.target
            x_or_y1 = e.clientX if 'h' in self.orientation else e.clientY
            self._dragging = self.orientation, sep.i, sep.abs_pos, x_or_y1
        else:
            return super().mouse_down(e)
    
    @event.emitter
    def mouse_up(self, e):
        self._dragging = None
        return super().mouse_down(e)
        
    @event.emitter
    def mouse_move(self, e):
        if self._dragging is not None:
            e.stopPropagation()
            ori, i, ref_pos, x_or_y1 = self._dragging
            if ori == self.orientation:
                x_or_y2 = e.clientX if 'h' in self.orientation else e.clientY
                positions = [None for i in range(len(self._seps))]
                diff = (x_or_y1 - x_or_y2) if 'r' in ori else (x_or_y2 - x_or_y1)
                positions[i] = max(0, ref_pos + diff)
                self._seps[i].style['left' if 'h' in ori else 'top'] =( x_or_y2- 4) + 'px'
                self.emit('_rerender', dict(positions=positions))  # collect rerenders
                # self.__rerender(dict(positions=positions))  # more direct
        else:
            return super().mouse_move(e)


## Util funcs

def _applyBoxStyle(e, sty, value):
    for prefix in ['-webkit-', '-ms-', '-moz-', '']:
        e.style[prefix + sty] = value


def _get_min_max(orientation, available_size, node):
    mi = _get_min_size(available_size, node)
    ma = _get_max_size(available_size, node)
    if 'h' in orientation:
        return mi[0], ma[0]
    else:
        return mi[1], ma[1]
    # todo: can we reduce half the queries here, because half is unused?


def _get_min_size(available_size, node):
    """ Get minimum and maximum size of a node, expressed in pixels.
    """
    x = node.style.minWidth
    if x == '0' or len(x) == 0:
        x = 0
    elif x.endswith('px'):
        x = float(x[:-2])
    elif x.endswith('%'):
        x = float(x[:-1]) * available_size
    else:
        x = 0
    
    y = node.style.minHeight
    if y == '0' or len(y) == 0:
        y = 0
    elif y.endswith('px'):
        y = float(y[:-2])
    elif y.endswith('%'):
        y = float(y[:-1]) * available_size
    else:
        y = 0
    
    return x, y
    
    
def _get_max_size(available_size, node):
    
    x = node.style.maxWidth
    if x == '0':
        x = 0
    elif not x:
        x = 1e9
    elif x.endswith('px'):
        x = float(x[:-2])
    elif x.endswith('%'):
        x = float(x[:-1]) * available_size
    else:
        x = 1e9
   
    y = node.style.maxHeight
    if y == '0':
        y = 0
    elif not y:
        y = 1e9
    elif y.endswith('px'):
        y = float(y[:-2])
    elif y.endswith('%'):
        y = float(y[:-1]) * available_size
    else:
        y = 1e9
    
    return x, y


## Convenience subclasses

class HBox(HVLayout):
    """ Horizontal layout that tries to give each widget its natural size and
    distributes any remaining space corresponding to the widget's flex values.
    """
    _DEFAULT_ORIENTATION = 'h'
    _DEFAULT_MODE = 'box'


class VBox(HVLayout):
    """ Vertical layout that tries to give each widget its natural size and
    distributes any remaining space corresponding to the widget's flex values.
    """
    _DEFAULT_ORIENTATION = 'v'
    _DEFAULT_MODE = 'box'


class HFix(HVLayout):
    """ Horizontal layout that distributes the available space corresponding
    to the widget's flex values.
    """
    _DEFAULT_ORIENTATION = 'h'
    _DEFAULT_MODE = 'fix'


class VFix(HVLayout):
    """ Vertical layout that distributes the available space corresponding
    to the widget's flex values.
    """
    _DEFAULT_ORIENTATION = 'v'
    _DEFAULT_MODE = 'fix'


class HSplit(HVLayout):
    """ Horizontal layout that initially distributes the available space
    corresponding to the widget's flex values, and has draggable splitters.
    By default, this layout has a slightly larger spacing between the widgets.
    """
    _DEFAULT_ORIENTATION = 'h'
    _DEFAULT_MODE = 'split'


class VSplit(HVLayout):
    """ Vertical layout that initially distributes the available space
    corresponding to the widget's flex values, and has draggable splitters.
    By default, this layout has a slightly larger spacing between the widgets.
    """
    _DEFAULT_ORIENTATION = 'v'
    _DEFAULT_MODE = 'split'
