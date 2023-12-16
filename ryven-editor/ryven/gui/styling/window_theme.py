from ...main.utils import abs_path_from_package_dir
from qdarkstyle import load_stylesheet, LightPalette
from enum import Enum

def hex_to_rgb(hex: str):
    if hex is None:
        return None
    else:
        return tuple(int(hex[i:i + 2], 16) for i in (1, 3, 5))


class WindowThemeType(Enum):
    PLAIN = 'plain'
    RYVEN_DARK = 'ryven-dark'
    RYVEN_LIGHT = 'ryven-light'
    QDARKSTYLE_DARK = 'qdarkstyle-dark'
    QDARKSTYLE_LIGHT = 'qdarkstyle-light'
     
     
class RyvenWindowTheme:
    """
    A class for a custom window theme. Should be combined with a corresponding
    WindowThemeType if the stylesheet is created from scratch. Otherwise, this
    is not needed.
    """
    
    name = ''
    colors = {}
    rules = {}

    def __init__(self):
        self.init_rules()

    def init_rules(self):
        self.rules = {
            # colors
            **self.colors,

            # rgb inline versions
            **{
                'rgb_inline_'+cname: str(hex_to_rgb(val))[1:-1]
                for cname, val in self.colors.items()
            },

            # additional rules
            'font_family': 'Roboto',
        }


class WindowTheme_Dark(RyvenWindowTheme):
    name = 'dark'
    colors = {
        'primaryColor': '#448aff',
        'primaryLightColor': '#83b9ff',
        'secondaryColor': '#1E242A',
        'secondaryLightColor': '#272d32',
        'secondaryDarkColor': '#0C1116',
        'primaryTextColor': '#E9E9E9',
        'secondaryTextColor': '#9F9F9F',
        'danger': '#dc3545',
        'warning': '#ffc107',
        'success': '#17a2b8',
    }


class WindowTheme_Light(RyvenWindowTheme):
    name = 'light'
    colors = {
        'primaryColor': '#448aff',
        'primaryLightColor': '#508AD8',
        'secondaryColor': '#FFFFFF',
        'secondaryLightColor': '#E8EAEC',
        'secondaryDarkColor': '#ECEDEF',
        'primaryTextColor': '#1A1A1A',
        'secondaryTextColor': '#6E6E6E',
        'danger': '#dc3545',
        'warning': '#ffc107',
        'success': '#17a2b8',
    }


class WindowTheme_Plain(RyvenWindowTheme):
    name = 'plain'
    colors = {
        'primaryColor': None,
        'primaryLightColor': None,
        'secondaryColor': None,
        'secondaryLightColor': None,
        'secondaryDarkColor': None,
        'primaryTextColor': None,
        'secondaryTextColor': None,
        'danger': None,
        'warning': None,
        'success': None,
    }
    
def apply_stylesheet(style: str):
    from qtpy.QtWidgets import QApplication
    
    # set to None if not used
    icons_dir = abs_path_from_package_dir('resources/stylesheets/icons')
    if icons_dir is not None:
        from qtpy.QtCore import QDir
        d = QDir()
        d.setSearchPaths('icon', [icons_dir])

    if not isinstance(style, WindowThemeType):
        try:
            style = WindowThemeType(style)
        except:
            style = None
    
    if style in (None, WindowThemeType.PLAIN):
        window_theme = WindowTheme_Plain()
        stylesheet = None
    
    # ryven originals
    elif style in (WindowThemeType.RYVEN_DARK, WindowThemeType.RYVEN_LIGHT):
        if style == WindowThemeType.RYVEN_DARK:
            window_theme = WindowTheme_Dark()
        elif style == WindowThemeType.RYVEN_LIGHT:
            window_theme = WindowTheme_Light()
        else:
            raise ValueError(
                f'Unknown window theme. '
                f'Got: {style}')

        from jinja2 import Template
        # path to the template stylesheet file
        template_file = abs_path_from_package_dir('resources/stylesheets/style_template.css')
        with open(template_file) as f:
            jinja_template = Template(f.read())

        stylesheet = jinja_template.render(window_theme.rules)
    
    # qdarkstyle
    else:
        if style == WindowThemeType.QDARKSTYLE_DARK:
            stylesheet = load_stylesheet()
            window_theme = WindowTheme_Dark()
        elif style == WindowThemeType.QDARKSTYLE_LIGHT:
            stylesheet = load_stylesheet(palette=LightPalette)
            window_theme = WindowTheme_Light()
            
    app = QApplication.instance()
    app.setStyleSheet(stylesheet)
    
    return (style, window_theme)
