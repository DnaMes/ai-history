"""Professional theme system for ai-history web UI.

Themes based on semek.org color schemes:
- Catppuccin (default): Soft pastel dark theme
- Dracula: Purple/cyan/pink on dark gray
- Nord: Arctic ice blue nordic theme
- Monokai: Green/cyan/orange on dark olive
- GitHub Dark: GitHub's official dark theme
- Tokyo Night: Blue/purple Tokyo-inspired dark theme
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class Theme:
    """A color theme for the ai-history web UI."""

    name: str
    display_name: str

    # Base colors
    bg: str
    bg_alt: str
    bg_panel: str
    text: str
    text_muted: str
    border: str

    # Accent colors
    primary: str
    secondary: str
    accent: str

    # Message colors
    user_bg: str
    user_border: str
    user_text: str
    assistant_bg: str
    assistant_border: str
    assistant_text: str

    # Code block colors
    code_bg: str
    code_border: str
    code_text: str

    # Status colors
    success: str
    warning: str
    error: str
    info: str

    # Syntax highlighting (hljs)
    hljs_theme: str

    # Font settings
    font_family_base: str = '"Inter", "SF Pro", -apple-system, BlinkMacSystemFont, sans-serif'
    font_family_code: str = '"JetBrains Mono", "Fira Code", "SF Mono", Consolas, Monaco, monospace'
    font_size_base: str = "14px"
    font_size_code: str = "13px"
    line_height: str = "1.6"

    # Spacing
    border_radius: str = "8px"
    border_radius_lg: str = "12px"

    # Shadows
    shadow_sm: str = "0 1px 2px rgba(0,0,0,0.05)"
    shadow: str = "0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)"
    shadow_md: str = "0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06)"
    shadow_lg: str = "0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05)"


# Professional themes based on semek.org
THEMES: Dict[str, Theme] = {
    "catppuccin": Theme(
        name="catppuccin",
        display_name="Catppuccin Mocha",
        # Base
        bg="#1e1e2e",
        bg_alt="#313244",
        bg_panel="#181825",
        text="#cdd6f4",
        text_muted="#a6adc8",
        border="#45475a",
        # Accents
        primary="#b4befe",
        secondary="#89dceb",
        accent="#cba6f7",
        # Messages
        user_bg="#313244",
        user_border="#b4befe",
        user_text="#cdd6f4",
        assistant_bg="#1e1e2e",
        assistant_border="#89dceb",
        assistant_text="#cdd6f4",
        # Code
        code_bg="#0d1117",
        code_border="#30363d",
        code_text="#cdd6f4",
        # Status
        success="#a6e3a1",
        warning="#f9e2af",
        error="#f38ba8",
        info="#89dceb",
        # hljs
        hljs_theme="atom-one-dark",
    ),
    "dracula": Theme(
        name="dracula",
        display_name="Dracula",
        # Base
        bg="#282a36",
        bg_alt="#343746",
        bg_panel="#21222c",
        text="#f8f8f2",
        text_muted="#b2b2c6",
        border="#44475a",
        # Accents
        primary="#bd93f9",
        secondary="#8be9fd",
        accent="#ff79c6",
        # Messages
        user_bg="#44475a",
        user_border="#bd93f9",
        user_text="#f8f8f2",
        assistant_bg="#343746",
        assistant_border="#8be9fd",
        assistant_text="#f8f8f2",
        # Code
        code_bg="#282a36",
        code_border="#44475a",
        code_text="#f8f8f2",
        # Status
        success="#50fa7b",
        warning="#f1fa8c",
        error="#ff5555",
        info="#8be9fd",
        # hljs
        hljs_theme="dracula",
    ),
    "nord": Theme(
        name="nord",
        display_name="Nord",
        # Base
        bg="#2e3440",
        bg_alt="#3b4252",
        bg_panel="#242933",
        text="#e5e9f0",
        text_muted="#a3b1c6",
        border="#4c566a",
        # Accents
        primary="#88c0d0",
        secondary="#81a1c1",
        accent="#b48ead",
        # Messages
        user_bg="#3b4252",
        user_border="#88c0d0",
        user_text="#e5e9f0",
        assistant_bg="#2e3440",
        assistant_border="#81a1c1",
        assistant_text="#e5e9f0",
        # Code
        code_bg="#2e3440",
        code_border="#4c566a",
        code_text="#e5e9f0",
        # Status
        success="#a3be8c",
        warning="#ebcb8b",
        error="#bf616a",
        info="#88c0d0",
        # hljs
        hljs_theme="nord",
    ),
    "monokai": Theme(
        name="monokai",
        display_name="Monokai",
        # Base
        bg="#272822",
        bg_alt="#31332c",
        bg_panel="#1e1f1c",
        text="#f8f8f2",
        text_muted="#a59f85",
        border="#49483e",
        # Accents
        primary="#a6e22e",
        secondary="#66d9ef",
        accent="#fd971f",
        # Messages
        user_bg="#31332c",
        user_border="#a6e22e",
        user_text="#f8f8f2",
        assistant_bg="#272822",
        assistant_border="#66d9ef",
        assistant_text="#f8f8f2",
        # Code
        code_bg="#272822",
        code_border="#49483e",
        code_text="#f8f8f2",
        # Status
        success="#a6e22e",
        warning="#e6db74",
        error="#f92672",
        info="#66d9ef",
        # hljs
        hljs_theme="monokai",
    ),
    "github": Theme(
        name="github",
        display_name="GitHub Dark",
        # Base
        bg="#0d1117",
        bg_alt="#161b22",
        bg_panel="#010409",
        text="#c9d1d9",
        text_muted="#8b949e",
        border="#30363d",
        # Accents
        primary="#58a6ff",
        secondary="#79c0ff",
        accent="#d2a8ff",
        # Messages
        user_bg="#161b22",
        user_border="#58a6ff",
        user_text="#c9d1d9",
        assistant_bg="#0d1117",
        assistant_border="#79c0ff",
        assistant_text="#c9d1d9",
        # Code
        code_bg="#0d1117",
        code_border="#30363d",
        code_text="#c9d1d9",
        # Status
        success="#3fb950",
        warning="#d29922",
        error="#f85149",
        info="#58a6ff",
        # hljs
        hljs_theme="github-dark",
    ),
    "tokyo": Theme(
        name="tokyo",
        display_name="Tokyo Night",
        # Base
        bg="#1a1b26",
        bg_alt="#24283b",
        bg_panel="#16161e",
        text="#c0caf5",
        text_muted="#9aa5ce",
        border="#414868",
        # Accents
        primary="#7aa2f7",
        secondary="#7dcfff",
        accent="#bb9af7",
        # Messages
        user_bg="#24283b",
        user_border="#7aa2f7",
        user_text="#c0caf5",
        assistant_bg="#1a1b26",
        assistant_border="#7dcfff",
        assistant_text="#c0caf5",
        # Code
        code_bg="#1a1b26",
        code_border="#414868",
        code_text="#c0caf5",
        # Status
        success="#9ece6a",
        warning="#e0af68",
        error="#f7768e",
        info="#7dcfff",
        # hljs
        hljs_theme="atom-one-dark",
    ),
}


def get_theme(theme_name: str) -> Theme:
    """Get a theme by name.

    Args:
        theme_name: The theme identifier

    Returns:
        Theme object (defaults to catppuccin if not found)
    """
    return THEMES.get(theme_name, THEMES["catppuccin"])


def get_all_themes() -> Dict[str, Theme]:
    """Get all available themes."""
    return THEMES.copy()


def generate_css_variables(theme: Theme) -> str:
    """Generate CSS custom properties for a theme.

    Args:
        theme: The theme to convert to CSS

    Returns:
        CSS string with :root variables
    """
    css = f""":root {{
    /* Theme: {theme.display_name} */
    
    /* Base Colors */
    --bg: {theme.bg};
    --bg-alt: {theme.bg_alt};
    --bg-panel: {theme.bg_panel};
    --text: {theme.text};
    --text-muted: {theme.text_muted};
    --border: {theme.border};
    
    /* Accents */
    --primary: {theme.primary};
    --secondary: {theme.secondary};
    --accent: {theme.accent};
    
    /* User Messages */
    --user-bg: {theme.user_bg};
    --user-border: {theme.user_border};
    --user-text: {theme.user_text};
    
    /* Assistant Messages */
    --assistant-bg: {theme.assistant_bg};
    --assistant-border: {theme.assistant_border};
    --assistant-text: {theme.assistant_text};
    
    /* Code Blocks */
    --code-bg: {theme.code_bg};
    --code-border: {theme.code_border};
    --code-text: {theme.code_text};
    
    /* Status */
    --success: {theme.success};
    --warning: {theme.warning};
    --error: {theme.error};
    --info: {theme.info};
    
    /* Typography */
    --font-family-base: {theme.font_family_base};
    --font-family-code: {theme.font_family_code};
    --font-size-base: {theme.font_size_base};
    --font-size-code: {theme.font_size_code};
    --line-height: {theme.line_height};
    
    /* Spacing */
    --border-radius: {theme.border_radius};
    --border-radius-lg: {theme.border_radius_lg};
    
    /* Shadows */
    --shadow-sm: {theme.shadow_sm};
    --shadow: {theme.shadow};
    --shadow-md: {theme.shadow_md};
    --shadow-lg: {theme.shadow_lg};
}}
"""
    return css


def generate_theme_switcher_js() -> str:
    """Generate JavaScript for theme switching functionality."""
    return """
// Theme Switcher
(function() {
    const THEME_KEY = 'aihistory-theme';
    const DEFAULT_THEME = 'catppuccin';
    
    const THEMES = ['catppuccin', 'dracula', 'nord', 'monokai', 'github', 'tokyo'];
    
    function getStoredTheme() {
        try {
            return localStorage.getItem(THEME_KEY) || DEFAULT_THEME;
        } catch (e) {
            return DEFAULT_THEME;
        }
    }
    
    function setTheme(themeName) {
        if (!THEMES.includes(themeName)) {
            console.warn('Unknown theme:', themeName);
            return;
        }
        
        document.documentElement.setAttribute('data-theme', themeName);
        
        // Update hljs theme
        const hljsLink = document.querySelector('link[href*="highlight.js"]');
        if (hljsLink) {
            const themeMap = {
                'catppuccin': 'atom-one-dark',
                'dracula': 'dracula',
                'nord': 'nord',
                'monokai': 'monokai',
                'github': 'github-dark',
                'tokyo': 'atom-one-dark'
            };
            const newHref = `https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/${themeMap[themeName]}.min.css`;
            hljsLink.href = newHref;
        }
        
        try {
            localStorage.setItem(THEME_KEY, themeName);
        } catch (e) {
            console.warn('Could not save theme preference');
        }
        
        // Dispatch event for other components
        window.dispatchEvent(new CustomEvent('themechange', { detail: themeName }));
    }
    
    // Initialize on load
    const storedTheme = getStoredTheme();
    document.documentElement.setAttribute('data-theme', storedTheme);
    
    // Expose global functions
    window.aiHistoryTheme = {
        set: setTheme,
        get: getStoredTheme,
        list: THEMES
    };
})();
"""
