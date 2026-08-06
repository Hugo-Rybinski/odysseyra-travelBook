"""A position-tracking JSON parser: returns (value, lines) where ``lines`` maps
a path tuple (keys and array indices) to the 1-based line of that value."""

from __future__ import annotations

from ..models import ItineraryError


class JSONPositionError(ItineraryError):
    pass


class _PosParser:
    _WS = " \t\n\r"

    def __init__(self, text: str):
        self.s = text
        self.i = 0
        self.n = len(text)
        self.lines: dict[tuple, int] = {}

    def line_at(self, idx: int) -> int:
        return self.s.count("\n", 0, min(idx, self.n)) + 1

    def _fail(self, msg: str):
        raise JSONPositionError(f"{msg} at line {self.line_at(self.i)}")

    def _ws(self):
        while self.i < self.n and self.s[self.i] in self._WS:
            self.i += 1

    def parse(self):
        self._ws()
        val = self._value(())
        self._ws()
        return val, self.lines

    def _value(self, path):
        self._ws()
        if self.i >= self.n:
            self._fail("unexpected end of input")
        self.lines[path] = self.line_at(self.i)
        c = self.s[self.i]
        if c == "{":
            return self._object(path)
        if c == "[":
            return self._array(path)
        if c == '"':
            return self._string()
        if c == "-" or c.isdigit():
            return self._number()
        for lit, val in (("true", True), ("false", False), ("null", None)):
            if self.s.startswith(lit, self.i):
                self.i += len(lit)
                return val
        self._fail(f"unexpected character {c!r}")

    def _object(self, path):
        obj = {}
        self.i += 1
        self._ws()
        if self.i < self.n and self.s[self.i] == "}":
            self.i += 1
            return obj
        while True:
            self._ws()
            if self.i >= self.n or self.s[self.i] != '"':
                self._fail("expected a string key")
            key = self._string()
            self._ws()
            if self.i >= self.n or self.s[self.i] != ":":
                self._fail("expected ':'")
            self.i += 1
            obj[key] = self._value(path + (key,))
            self._ws()
            if self.i >= self.n:
                self._fail("unterminated object")
            c = self.s[self.i]
            self.i += 1
            if c == ",":
                continue
            if c == "}":
                break
            self._fail("expected ',' or '}'")
        return obj

    def _array(self, path):
        arr = []
        self.i += 1
        self._ws()
        if self.i < self.n and self.s[self.i] == "]":
            self.i += 1
            return arr
        idx = 0
        while True:
            arr.append(self._value(path + (idx,)))
            idx += 1
            self._ws()
            if self.i >= self.n:
                self._fail("unterminated array")
            c = self.s[self.i]
            self.i += 1
            if c == ",":
                continue
            if c == "]":
                break
            self._fail("expected ',' or ']'")
        return arr

    def _string(self):
        i = self.i + 1
        buf = []
        esc = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f",
               "n": "\n", "r": "\r", "t": "\t"}
        while i < self.n:
            c = self.s[i]
            if c == "\\":
                nxt = self.s[i + 1]
                if nxt == "u":
                    buf.append(chr(int(self.s[i + 2:i + 6], 16)))
                    i += 6
                else:
                    buf.append(esc.get(nxt, nxt))
                    i += 2
                continue
            if c == '"':
                self.i = i + 1
                return "".join(buf)
            buf.append(c)
            i += 1
        self.i = i
        self._fail("unterminated string")

    def _number(self):
        start = self.i
        while self.i < self.n and self.s[self.i] in "+-0123456789.eE":
            self.i += 1
        tok = self.s[start:self.i]
        try:
            return int(tok)
        except ValueError:
            return float(tok)


def load_with_lines(text: str):
    return _PosParser(text).parse()
