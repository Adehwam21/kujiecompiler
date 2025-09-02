import unicodedata

class Preprocessor:
    @staticmethod
    def preprocess_code(path: str) -> str:
        """
        Reads a source file and cleans it for the lexer.
        - Replaces non-breaking spaces with normal spaces
        - Converts all whitespace to ASCII spaces
        - Normalizes Unicode characters (NFKC)
        - Removes BOM if present
        """
        with open(path, "r", encoding="utf-8-sig") as f:
            src = f.read()

        # Normalize Unicode characters
        src = unicodedata.normalize("NFKC", src)

        # Replace non-breaking spaces and other weird whitespace with normal space
        src = "".join(" " if unicodedata.category(c) == "Zs" else c for c in src)

        # Replace tabs with normal space
        src = src.replace("\t", " ")
        src = src.replace("\n", " ")
        src = src.replace("\xa0", " ")

        return src
