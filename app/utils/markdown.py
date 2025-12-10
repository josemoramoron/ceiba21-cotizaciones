"""
Utilidades para formateo de Markdown V2 de Telegram.
"""
import re


def escape_markdown_v2(text: str, entities: bool = False) -> str:
    """
    Escapar caracteres especiales para Telegram Markdown V2.
    
    Args:
        text: Texto a escapar
        entities: Si True, escapa para usar dentro de entidades (links, code)
        
    Returns:
        Texto escapado
        
    Caracteres especiales en MarkdownV2:
    _ * [ ] ( ) ~ ` > # + - = | { } . !
    """
    if not text:
        return text
    
    # Caracteres que necesitan escape
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    
    # Escapar cada carácter especial
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    
    return text


def bold(text: str) -> str:
    """Formatear texto en negrita para Markdown V2"""
    return f'*{escape_markdown_v2(text)}*'


def italic(text: str) -> str:
    """Formatear texto en cursiva para Markdown V2"""
    return f'_{escape_markdown_v2(text)}_'


def code(text: str) -> str:
    """Formatear texto como código para Markdown V2"""
    return f'`{text}`'


def link(text: str, url: str) -> str:
    """Crear link en Markdown V2"""
    return f'[{escape_markdown_v2(text)}]({url})'
