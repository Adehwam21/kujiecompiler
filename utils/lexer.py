import re
import enum
import sys

IDENTIFIER_REGEX = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
NUMBER_REGEX = re.compile(r'\d+(\.\d+)?')


class Lexer:
    def __init__(self, src_code):
        self.source = src_code
        self.curChar = ''   
        self.curPos = -1    
        self.line = 1       # line starts at 1
        self.col = 0        # col starts at 0
        self.nextChar()

    def nextChar(self):
        """Advance by one character and update line/col tracking."""
        self.curPos += 1
        if self.curPos >= len(self.source):
            self.curChar = '\0'
        else:
            self.curChar = self.source[self.curPos]

        # Track line/col
        if self.curChar == '\n':
            self.line += 1
            self.col = 0
        else:
            self.col += 1

    def lookahead(self):
        if self.curPos + 1 >= len(self.source):
            return '\0'
        return self.source[self.curPos + 1]

    def stop(self, message):
        sys.exit(f"[Lexing Error] line {self.line}, col {self.col}: {message}")

    def skipWhitespace(self):
        while self.curChar in [' ','    ', '\t', '\r']:
            self.nextChar()

    def skipComment(self):
        if self.curChar == '~':
            while self.curChar not in ['\n', ';', '\0']:
                self.nextChar()

    def getToken(self):
        self.skipWhitespace()
        self.skipComment()
        token = None

        # Operators and punctuation
        if self.curChar == '+':
            token = Token(self.curChar, TokenType.PLUS, self.line, self.col)
        elif self.curChar == '-':
            token = Token(self.curChar, TokenType.MINUS, self.line, self.col)
        elif self.curChar == '*':
            token = Token(self.curChar, TokenType.ASTERISK, self.line, self.col)
        elif self.curChar == '/':
            token = Token(self.curChar, TokenType.SLASH, self.line, self.col)
        elif self.curChar == '%':
            token = Token(self.curChar, TokenType.PERCENT, self.line, self.col)
        elif self.curChar == '=':
            if self.lookahead() == '=':
                lastChar = self.curChar
                self.nextChar()
                token = Token(lastChar + self.curChar, TokenType.EQEQ, self.line, self.col)
            else:
                token = Token(self.curChar, TokenType.EQ, self.line, self.col)
        elif self.curChar == '>':
            if self.lookahead() == '=':
                lastChar = self.curChar
                self.nextChar()
                token = Token(lastChar + self.curChar, TokenType.GTEQ, self.line, self.col)
            else:
                token = Token(self.curChar, TokenType.GT, self.line, self.col)
        elif self.curChar == '<':
            if self.lookahead() == '=':
                lastChar = self.curChar
                self.nextChar()
                token = Token(lastChar + self.curChar, TokenType.LTEQ, self.line, self.col)
            else:
                token = Token(self.curChar, TokenType.LT, self.line, self.col)
        elif self.curChar == '!':
            if self.lookahead() == '=':
                lastChar = self.curChar
                self.nextChar()
                token = Token(lastChar + self.curChar, TokenType.NOTEQ, self.line, self.col)
            else:
                self.stop(f"Expected !=, got!: {self.lookahead()}")

        # Strings
        elif self.curChar == '"':
            self.nextChar()
            startPos = self.curPos
            while self.curChar != '"':
                if self.curChar in ['\r', '\n', '\t', '\\', '%', '\0']:
                    self.stop(f"Illegal character in string: {self.curChar}")
                self.nextChar()
            tokText = self.source[startPos:self.curPos]
            token = Token(tokText, TokenType.STRING, self.line, self.col)

        # Numbers
        elif self.curChar.isdigit():
            match = NUMBER_REGEX.match(self.source, self.curPos)
            if match:
                tokText = match.group(0)
                self.curPos += len(tokText) - 1
                self.col += len(tokText) - 1
                token = Token(tokText, TokenType.NUMBER, self.line, self.col)
            else:
                self.stop(f"Illegal number, line {self.line}, col {self.col}")

        # Identifiers / Keywords
        elif self.curChar.isalpha() or self.curChar == '_':
            match = IDENTIFIER_REGEX.match(self.source, self.curPos)
            if match:
                tokText = match.group(0)
                self.curPos += len(tokText) - 1
                self.col += len(tokText) - 1
                keyword = Token.checkIfKeyword(tokText)
                token = Token(tokText, keyword if keyword else TokenType.IDENTIFIER, self.line, self.col)
            else:
                self.stop(f"Illegal identifier at line {self.line}, col {self.col}")

        elif self.curChar == '\n':
            token = Token(TokenType.ENDLINE, ';', self.line, self.col)
        elif self.curChar == ";":
            token = Token(self.curChar, TokenType.ENDLINE, self.line, self.col)
        elif self.curChar == '\0':
            token = Token('', TokenType.EOF, self.line, self.col)
        else:
            self.stop("Unknown token: " + self.curChar)

        self.nextChar()
        return token

    def tokenize_as_tuple(self):
        tokens = []
        while True:
            tok = self.getToken()
            tokens.append((tok.kind, tok.text))  # kind as string for testing
            if tok.kind == TokenType.EOF:
                break
        return tokens

    def tokenize_as_object(self):
        tokens = []
        while True:
            tok = self.getToken()
            tokens.append(tok)
            if tok.kind == TokenType.EOF:
                break
        return tokens


class Token:
    def __init__(self, tokenText, tokenKind, line=0, col=0):
        self.text = tokenText
        self.kind = tokenKind
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.kind.name}, '{self.text}', line={self.line}, col={self.col})"

    @staticmethod
    def checkIfKeyword(tokenText):
        for kind in TokenType:
            if kind.name == tokenText.upper() and 100 <= kind.value < 200:
                return kind
        return None


class TokenType(enum.Enum):
    EOF = -1
    ENDLINE = 0
    NUMBER = 1
    IDENTIFIER = 2
    STRING = 3

    # Keywords
    LABEL = 101
    GOTO = 102
    WREP = 103
    TAKE = 104
    MAKE = 105
    IF = 106
    THEN = 107
    ENDIF = 108
    WHILE = 109
    REPEAT = 110
    ENDWHILE = 111
    DO = 112
    ELSE = 113

    # Operators
    EQ = 201
    PLUS = 202
    MINUS = 203
    ASTERISK = 204
    SLASH = 205
    EQEQ = 206
    NOTEQ = 207
    LT = 208
    LTEQ = 209
    GT = 210
    GTEQ = 211
    PERCENT = 212
