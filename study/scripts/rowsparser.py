"""Shared HTML parser for Headphone Zone feature-chart rows."""
import re
from html.parser import HTMLParser


class Rows(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.stack, self.cur, self.field, self.buf = [], [], None, None, []

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get("class") or ""
        if tag == "br" and self.field:
            self.buf.append(" | ")
            return
        if tag in ("br", "img", "input", "meta", "link", "hr", "source"):
            return
        role = None
        if "feature-chart__table-row" in cls:
            role = "row"
            self.cur = {"h": "", "v": []}
        elif self.cur is not None and "feature-chart__heading" in cls:
            role = "h"
        elif self.cur is not None and "feature-chart__value" in cls:
            role = "v"
        if role in ("h", "v"):
            self.field, self.buf = role, []
        self.stack.append(role)

    def handle_endtag(self, tag):
        if tag in ("br", "img", "input", "meta", "link", "hr", "source") or not self.stack:
            return
        role = self.stack.pop()
        txt = re.sub(r"\s+", " ", "".join(self.buf)).strip(" |")
        if role == "h" and self.cur is not None:
            self.cur["h"], self.field = txt, None
        elif role == "v" and self.cur is not None:
            self.cur["v"].append(txt)
            self.field = None
        elif role == "row" and self.cur is not None:
            self.rows.append(self.cur)
            self.cur = None

    def handle_data(self, d):
        if self.field:
            self.buf.append(d)
