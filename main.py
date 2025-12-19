import urllib.request
import tkinter as tk
from html.parser import HTMLParser
import re

# Core modules

class HTMLElement():
    def __init__(self, element_type, element_data={}, id=None, tags=None):
        self.type = element_type
        self.data = element_data
        self.id = id
        self.tags = tags if tags is not None else []


class HTMLCollection():
    def __init__(self):
        self.elements = []

    def addObject(self, element_type, element_data={}, tags=None):
        element_id = len(self.elements) + 1
        self.elements.append(HTMLElement(element_type, element_data, id=element_id, tags=tags))
        return element_id


# ================== SIMPLE JAVASCRIPT INTERPRETER ==================

class SimpleJSInterpreter:
    def __init__(self, html_collection):
        self.html_collection = html_collection
        self.vars = {}
        self.functions = {}

    def run(self, code, tag_stack=None):
        if tag_stack is None:
            tag_stack = []
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
                self.run(self.functions[m.group(1)], tag_stack)
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
                    self.run(";".join(block), tag_stack)
                i += 1
                continue

            # -------- document.write --------
            m = re.match(r'document\.write\((.+?)\)', line)
            if m:
                val = self.eval_value(m.group(1))
                self.html_collection.addObject("text", {"content": str(val)}, tags=tag_stack)
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
    def __init__(self):
        super().__init__()
        self.css_rules = {}
        self.tag_stack = []
        self.tag_styles = {}

        self.in_style = False
        self.style_buffer = ""

        self.in_script = False
        self.script_buffer = ""

        self.htmlCollection = HTMLCollection()
        self.js = SimpleJSInterpreter(self.htmlCollection)

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
            self.htmlCollection.addObject("br")
            return

        styles = {}
        styles.update(self.css_rules.get(tag, {}))
        if "class" in attrs:
            styles.update(self.css_rules.get("." + attrs["class"], {}))
        if "id" in attrs:
            styles.update(self.css_rules.get("#" + attrs["id"], {}))
        styles.update(self.parse_css_block(attrs.get("style", "")))

        style_tag_name = f"style_{len(self.tag_styles)}"
        self.tag_styles[style_tag_name] = styles
        
        # Push the tag, its attributes, and its generated style name to the stack
        self.tag_stack.append((tag, attrs, style_tag_name))

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False
            self.parse_global_css(self.style_buffer)
            self.style_buffer = ""
            return

        if tag == "script":
            self.in_script = False
            self.js.run(self.script_buffer, [s for _, _, s in self.tag_stack])
            self.script_buffer = ""
            return

        if self.tag_stack and self.tag_stack[-1][0] == tag:
            self.tag_stack.pop()
            # Add an end marker for block-level elements to handle newlines
            if tag in {"p", "h1", "h2", "h3", "h4", "h5", "h6", "div", "li"}:
                self.htmlCollection.addObject(f"end_{tag}")


    def handle_data(self, data):
        if self.in_style:
            self.style_buffer += data
        elif self.in_script:
            self.script_buffer += data
        elif self.tag_stack:
            # Get current tag info from the top of the stack
            tag, attrs, _ = self.tag_stack[-1]
            # Get all styles from the stack to handle nesting
            style_tags = [s for _, _, s in self.tag_stack]
            self.htmlCollection.addObject(tag, {"content": data.strip(), "attrs": attrs}, tags=style_tags)

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
            elif k == "font-weight":
                props["weight"] = v
            elif k == "font-size":
                size = re.sub(r"\D", "", v)
                if size:
                    props["size"] = int(size)
        return props


# ================== BROWSER ==================

def browse(url, root = None, isHtml = False):
    if root is None:
        root = tk.Tk()
    
    # Clear previous content
    for widget in root.winfo_children():
        widget.destroy()

    createSearchBar(root,url)

    root.title("Python Mini Browser")

    content_frame = tk.Frame(root)
    content_frame.pack(expand=True, fill="both")

    try:
        if not isHtml:
            with urllib.request.urlopen(url) as r:
                html = r.read().decode("utf-8", errors="ignore")
        else:
            html = url
            
        cssrenderer = AdvancedCSSRenderer()
        cssrenderer.feed(html)

        # A frame to hold inline elements for a single "line"
        inline_container = tk.Frame(content_frame)
        inline_container.pack(fill="x", anchor="w")

        block_elements = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "div", "li"}
        
        for element in cssrenderer.htmlCollection.elements:
            if element.type == "title" and element.data.get("content"):
                root.title(element.data["content"])

            elif element.type.startswith("end_") and element.type[4:] in block_elements:
                # End of a block, start a new line for subsequent elements
                inline_container = tk.Frame(content_frame)
                inline_container.pack(fill="x", anchor="w")

            elif element.type == "br":
                inline_container = tk.Frame(content_frame)
                inline_container.pack(fill="x", anchor="w")

            elif element.data.get("content"):
                content = element.data["content"]
                
                style = {}
                if element.tags:
                    for tag_name in element.tags:
                        if tag_name in cssrenderer.tag_styles:
                            style.update(cssrenderer.tag_styles[tag_name])

                font_family = "Arial" # Hardcoded for now
                font_weight = style.get("weight", "normal")
                font_size = style.get("size", 12)
                
                widget_config = {
                    "text": content,
                    "font": (font_family, font_size, font_weight),
                    "fg": style.get("foreground", "black"),
                    "bg": style.get("background", "white"),
                    "wraplength": 800 # Fixed wraplength
                }

                label = tk.Label(inline_container, **widget_config)
                
                if element.type == "a":
                    link_url = element.data.get("attrs", {}).get("href")
                    if link_url:
                        label.config(fg="blue", cursor="hand2")
                        current_font = widget_config["font"]
                        # Add underline to font weight
                        new_weight = f"{current_font[2]} underline"
                        label.config(font=(current_font[0], current_font[1], new_weight))
                        
                        def make_callback(url_to_open):
                            return lambda e: browse(createAbsoluteURL(url,url_to_open), root)
                        label.bind("<Button-1>", make_callback(link_url))

                label.pack(side="left", anchor="nw")

    except Exception as e:
        tk.Label(content_frame, text=f"Error: {e}", fg="red").pack(anchor="w")

def GetBasisURL(url):
    segments = url.split("/")
    #Remove empty parts of list
    segments = [segment for segment in segments if segment]
    prefix = ""
    if segments[0] in ["https:","http:"]:
        prefix = segments.pop(0)
    print(segments)
    return prefix+"//"+segments[0]
def createAbsoluteURL(url, givenUrl):
    print(url,givenUrl)
    if givenUrl.startswith("https://") or givenUrl.startswith("http://"):
        return givenUrl
    elif givenUrl.startswith("/"):
        return GetBasisURL(url) + givenUrl
    else:
        return url + "/" + givenUrl


def createSearchBar(root,url = ""):
    top_frame = tk.Frame(root)
    top_frame.pack(fill="x")

    urlSelect = tk.Entry(root)
    urlSelect.delete(0, tk.END)
    urlSelect.insert(0,url)
    urlSelect.pack(in_=top_frame, side="left", fill="x", expand=True)
    searchButton = tk.Button(root,text="Search",command=lambda: browse(urlSelect.get(), root) )
    searchButton.pack(in_=top_frame, side="right")
# ================== ENTRY ==================

if __name__ == "__main__":
    #browse(exampleHtml,isHtml=True)
    GetBasisURL("https://femboycodedev.github.io/htmlTest.github.io/linkTest")
    root = tk.Tk()

    createSearchBar(root)


    root.geometry("800x600")

    browse("https://femboycodedev.github.io/htmlTest.github.io/",root)

    root.mainloop()
    #browse("https://example.com")
