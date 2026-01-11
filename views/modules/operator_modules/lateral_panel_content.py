from views.modules.operator_modules.news_panel_module import NewsPanelContent
from views.modules.operator_modules.breaks_panel_module import BreaksPanelContent



class LateralPanelContent():
    """Panel lateral que muestra varios módulos, como noticias, breaks, etc."""
    def __init__(self, parent, username, ui_factory, UI):
        self.parent = parent
        self.username = username
        self.ui_factory = ui_factory
        self.UI = UI
        self.modules = []

        self.render()
        


    def render(self):
        self.news_module = NewsPanelContent(
            parent=self.parent,
            username=self.username,
            ui_factory=self.ui_factory,
            UI=self.UI
        )
        self.modules.append(self.news_module)

        self.breaks_module = BreaksPanelContent(
            parent=self.parent,
            username=self.username,
            ui_factory=self.ui_factory,
            UI=self.UI
        )
        self.modules.append(self.breaks_module)

    