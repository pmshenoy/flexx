"""
Example:

.. UIExample:: 200
    
    from flexx import ui, app
    
    class Example(app.PyComponent):
    
        def init(self):
        
            with ui.PinboardLayout():
                self.b1 = ui.Button(text='Stuck at (20, 20)',
                                    style='left:20px; top:20px;')
                self.b2 = ui.Button(text='Dynamic at (30%, 30%)',
                                    style='left:30%; top:30%; height:100px;')
                self.b3 = ui.Button(text='Dynamic at (50%, 70%)',
                                    style='left:50%; top:70%;')

"""

from . import Layout


class PinboardLayout(Layout):
    """ Unconstrained absolute and relative positioning of child widgets.
    
    This simply places child widgets using CSS "position: absolute". Use
    CSS "left" and "top" to position the widget (using a "px" or "%" suffix).
    Optionally "width", "height", "right" and "bottom" can also be used.
    """
    
    CSS = """
    .flx-PinboardLayout > .flx-Widget {
        position: absolute;
    }
    """
