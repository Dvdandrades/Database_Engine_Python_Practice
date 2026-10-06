import re
from typing import ClassVar


class Lexer:
    TOKENS: ClassVar[list[tuple[str, str]]] = [
        ("STRING", r"'[^']*'|\"[^\"]*\""),
        ("NUMBER", r"\d+(\.\d+)?"),
        (
            "KEYWORD",
            r"\b(SELECT|FROM|WHERE|INSERT|INTO|VALUES|UPDATE|SET|DELETE|CREATE|TABLE|INDEX|ON|AND|OR|BEGIN|COMMIT|ROLLBACK|ABORT)\b",
        ),
        ("OP", r"!=|>=|<=|=|<|>|\bLIKE\b"),
        ("IDENT", r"[a-zA-Z_][a-zA-Z0-9_]*"),
        ("PUNC", r"[\(\)\*,;]"),
        ("WS", r"\s+"),
    ]

    def __init__(self, text: str):
        self.text = text.strip()
        self.tok_regex = "|".join(
            f"(?P<{name}>{pattern})" for name, pattern in self.TOKENS
        )
        self.tokens = self._tokenize_all()
        self.token_idx = 0
        self.current_token = None
        self.advance()

    def _tokenize_all(self) -> list[tuple[str, str]]:
        tokens = []
        pos = 0
        regex = re.compile(self.tok_regex, re.IGNORECASE)

        while pos < len(self.text):
            match = regex.match(self.text, pos)
            if not match:
                raise ValueError(
                    f"Unexpected character in position {pos}: {self.text[pos]}"
                )

            pos = match.end()
            tok_type = match.lastgroup
            tok_val = match.group(tok_type)

            if tok_type != "WS":
                tokens.append((tok_type, tok_val))

        tokens.append(("EOF", None))
        return tokens

    def advance(self):
        if self.token_idx < len(self.tokens):
            self.current_token = self.tokens[self.token_idx]
            self.token_idx += 1

    def consume(self, expected_type: str, expected_val: str | None = None) -> str:
        tok_type, tok_val = self.current_token
        if tok_type == expected_type and (
            expected_val is None or tok_val.upper() == expected_val.upper()
        ):
            self.advance()
            return tok_val
        raise ValueError(
            f"Expecting {expected_type} {expected_val or ''}, got {tok_type} '{tok_val}'"
        )
