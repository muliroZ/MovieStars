"""Normalização de textos para busca e ordenação sem diferenciar acentos e maiúsculas."""

import unicodedata


def normalize_title(text: str) -> str:
    """Título para busca e ordenação: sem acentos e sem diferença de maiúsculas.

    Ex.: "À La Recherche" → "a la recherche". Aspas, espaços e outros símbolos
    ficam como estão.
    """

    # NFKD separa letra e acento ("À" → "A" + "̀"); os acentos são descartados.
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return without_accents.casefold()
