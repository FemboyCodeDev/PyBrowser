import urllib.request
import tkinter as tk
from html.parser import HTMLParser
import re

# Core modules

class HTMLElement():
    def __init__(self,element_type,element_data = {},id = None):
        self.type = element_type
        self.data = element_data
        self.id = id



class HTMLCollection():
    def __init__(self):
        self.elements = []
    def addObject(self,element_type,element_data = {}):
        element_id = len(self.elements)+1
        self.elements.append(HTMLElement(element_type,element_data),id = element_id)
        return element_id



# ================== SIMPLE JAVASCRIPT INTERPRETER ==================

class SimpleJSInterpreter:
    def __init__(self, text_widget):
        self.text = text_widget
        self.vars = {}
        self.functions = {}

    def run(self, code):
        lines = self.split_statements(code)
        i = 0

        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith("//"):
                i += 1
                continue

            # -------- function definition --------
            m = re.match(r'function\s+(\w+)\s*\(\)\s*\{', line)
            if m:
                fname = m.group(1)
                body = []
                i += 1
                while i < len(lines) and "}" not in lines[i]:
                    body.append(lines[i])
                    i += 1
                self.functions[fname] = ";".join(body)
                i += 1
                continue

            # -------- function call --------
            m = re.match(r'(\w+)\s*\(\)', line)
            if m and m.group(1) in self.functions:
                self.run(self.functions[m.group(1)])
                i += 1
                continue

            # -------- if statement --------
            m = re.match(r'if\s*\((.*?)\)\s*\{', line)
            if m:
                condition = m.group(1)
                block = []
                i += 1
                while i < len(lines) and "}" not in lines[i]:
                    block.append(lines[i])
                    i += 1
                if self.eval_condition(condition):
                    self.run(";".join(block))
                i += 1
                continue

            # -------- document.write --------
            m = re.match(r'document\.write\((.+?)\)', line)
            if m:
                val = self.eval_value(m.group(1))
                self.text.insert(tk.END, str(val))
                i += 1
                continue

            # -------- console.log --------
            m = re.match(r'console\.log\((.+?)\)', line)
            if m:
                print("JS:", self.eval_value(m.group(1)))
                i += 1
                continue

            # -------- var assignment --------
            m = re.match(r'var\s+(\w+)\s*=\s*(.+)', line)
            if m:
                self.vars[m.group(1)] = self.eval_value(m.group(2))
                i += 1
                continue

            print("JS error:", line)
            i += 1

    def eval_value(self, val):
        val = val.strip()
        if val.startswith(("'", '"')):
            return val[1:-1]
        if val.isdigit():
            return int(val)
        if val == "true":
            return True
        if val == "false":
            return False
        return self.vars.get(val, "")

    def eval_condition(self, cond):
        m = re.match(r'(\w+)\s*={2,3}\s*(.+)', cond)
        if m:
            return self.vars.get(m.group(1)) == self.eval_value(m.group(2))
        return bool(self.vars.get(cond))

    def split_statements(self, code):
        stmts, buf, depth = [], "", 0
        for c in code:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
            if c == ";" and depth == 0:
                stmts.append(buf.strip())
                buf = ""
            else:
                buf += c
        if buf.strip():
            stmts.append(buf.strip())
        return stmts


# ================== HTML + CSS RENDERER ==================

class AdvancedCSSRenderer(HTMLParser):
    def __init__(self, text_widget):
        super().__init__()
        self.text = text_widget
        self.css_rules = {}
        self.tag_stack = []

        self.in_style = False
        self.style_buffer = ""

        self.in_script = False
        self.script_buffer = ""

        self.js = SimpleJSInterpreter(text_widget)

        self.htmlCollection = HTMLCollection()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "style":
            self.in_style = True
            return

        if tag == "script":
            if "src" in attrs:
                return  # ignore external JS safely
            self.in_script = True
            return

        if tag == "br":

            #self.text.insert(tk.END, "\n")
            self.htmlCollection.addObject("br")
            return

        styles = {}
        styles.update(self.css_rules.get(tag, {}))
        if "class" in attrs:
            styles.update(self.css_rules.get("." + attrs["class"], {}))
        if "id" in attrs:
            styles.update(self.css_rules.get("#" + attrs["id"], {}))
        styles.update(self.parse_css_block(attrs.get("style", "")))

        tag_name = f"tk_{len(self.tag_stack)}"
        self.apply_tk_styles(tag_name, styles)
        self.tag_stack.append(tag_name)

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False
            self.parse_global_css(self.style_buffer)
            self.style_buffer = ""
            return

        if tag == "script":
            self.in_script = False
            self.js.run(self.script_buffer)
            self.script_buffer = ""
            return

        if self.tag_stack:
            self.tag_stack.pop()

    def handle_data(self, data):
        if self.in_style:
            self.style_buffer += data
        elif self.in_script:
            self.script_buffer += data
        else:
            self.text.insert(tk.END, data, tuple(self.tag_stack))

    # ---------- CSS ----------
    def parse_global_css(self, css):
        for sel, block in re.findall(r"([^{]+)\{([^}]+)\}", css):
            self.css_rules[sel.strip()] = self.parse_css_block(block)

    def parse_css_block(self, block):
        props = {}
        for item in block.split(";"):
            if ":" not in item:
                continue
            k, v = [x.strip().lower() for x in item.split(":", 1)]
            if k == "color":
                props["foreground"] = v
            elif k == "background-color":
                props["background"] = v
            elif k == "font-weight" and v == "bold":
                props["weight"] = "bold"
            elif k == "font-size":
                size = re.sub(r"\D", "", v)
                if size:
                    props["size"] = int(size)
        return props

    def apply_tk_styles(self, name, props):
        self.text.tag_configure(
            name,
            foreground=props.get("foreground", "black"),
            background=props.get("background", "white"),
            font=("Arial", props.get("size", 10), props.get("weight", "normal")),
        )


# ================== BROWSER ==================

def browse(url):
    root = tk.Tk()
    root.title("Python Mini Browser")

    txt = tk.Text(root, wrap="word")
    txt.pack(expand=True, fill="both")

    try:
        with urllib.request.urlopen(url) as r:
            html = r.read().decode("utf-8", errors="ignore")
        AdvancedCSSRenderer(txt).feed(html)
    except Exception as e:
        txt.insert(tk.END, f"Error: {e}")

    root.mainloop()


# ================== ENTRY ==================

if __name__ == "__main__":
    browse("https://example.com")
