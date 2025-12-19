import urllib.request
import tkinter as tk
import tkinter.font
import tkinter.messagebox
from html.parser import HTMLParser
import re

# Core modules

class HTMLElement():
    def __init__(self, element_type, element_data={}, id=None, tags=None):
        self.type = element_type
        self.data = element_data
        self.id = id
        self.tags = tags if tags is not None else []
        self.boundObject = None
        self.onclick = None
        self.JSOveride = {}


class HTMLCollection():
    def __init__(self):
        self.elements = []

    def addObject(self, element_type, element_data={}, tags=None,element_id=None):
        if element_id is None:
            element_id = len(self.elements) + 1
        self.elements.append(HTMLElement(element_type, element_data, id=element_id, tags=tags))
        return self.elements[-1]


# ================== CUSTOM WIDGETS ==================

class TransparentLabel(tk.Canvas):
    def __init__(self, master=None, **kwargs):
        text = kwargs.pop("text", "")
        font_tuple = kwargs.pop("font", ("Arial", 12))
        fg = kwargs.pop("fg", "black")
        underline = kwargs.pop("underline", False)

        if "bg" not in kwargs and "background" not in kwargs:
            if master:
                kwargs["bg"] = master.cget("bg")

        family = font_tuple[0]
        size = font_tuple[1]
        weight = "normal"
        if len(font_tuple) > 2:
            weight = font_tuple[2]

        self.font = tkinter.font.Font(family=family, size=size, weight=weight, underline=underline)

        width = self.font.measure(text)
        height = self.font.metrics("linespace")

        super().__init__(master, width=width, height=height, **kwargs)

        self.text_id = self.create_text(0, 0, text=text, font=self.font, fill=fg, anchor="nw")
        self.config(highlightthickness=0)
        self.text_content = text

    def config(self, **kwargs):
        if 'fg' in kwargs:
            self.itemconfig(self.text_id, fill=kwargs.pop('fg'))

        font_updated = False
        if 'underline' in kwargs:
            self.font.config(underline=kwargs.pop('underline'))
            font_updated = True

        if 'font' in kwargs:
            font_tuple = kwargs.pop('font')
            family = font_tuple[0]
            size = font_tuple[1]
            weight = "normal"
            if len(font_tuple) > 2:
                weight = font_tuple[2]
            self.font.config(family=family, size=size, weight=weight)

            width = self.font.measure(self.text_content)
            height = self.font.metrics("linespace")
            super().config(width=width, height=height)
            font_updated = True

        if font_updated:
            self.itemconfig(self.text_id, font=self.font)
        if "text" in kwargs:
            self.text_content = kwargs.pop('text')
            self.itemconfig(self.text_id, text=self.text_content)
            width = self.font.measure(self.text_content)
            height = self.font.metrics("linespace")
            super().config(width=width, height=height)
        if "text_content" in kwargs:
            self.text_content =kwargs.pop('text_content')
            self.itemconfig(self.text_id, text=self.text_content)
            width = self.font.measure(self.text_content)
            height = self.font.metrics("linespace")
            super().config(width=width, height=height)




        super().config(**kwargs)

    def configure(self, **kwargs):
        self.config(**kwargs)

# ================== SIMPLE JAVASCRIPT INTERPRETER ==================

class SimpleJSInterpreter:
    def __init__(self, html_collection):
        self.html_collection = html_collection
        self.vars = {}
        self.functions = {}

    def run(self, code, tag_stack=None):
        #print(code)
        if tag_stack is None:
            tag_stack = []
        lines = self.split_statements(code)
        print(lines)
        i = 0

        while i < len(lines):

            line = lines[i].strip()
            #print("JS LINE",line)
            if not line or line.startswith("//"):
                i += 1
                continue

            # -------- alert definition --------
            m = re.match(r'alert\((.+?)\)', line)
            if m:
                print("JS:", m.group(1))
                tkinter.messagebox.showinfo("Alert", m.group(1))
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
            # -------- const assignment --------
            m = re.match(r'const\s+(\w+)\s*=\s*(.+)', line)
            if m:
                self.vars[m.group(1)] = self.eval_value(m.group(2))
                i += 1
                continue
            # -------- docuemnt functions -------
            # for stuff like document.getElementById()
            m = re.match(r"document\.(\w+)\((.+?)\)\.?(\w+)?", line)
            if m:
                #document.getElementById(id)
                if m.group(1) == "getElementById":
                    element = None
                    #print(m.group(1),m.group(2))
                    #print(self.html_collection.elements)
                    targetId = m.group(2)
                    if targetId[0] == "'" and targetId[-1] == "'":
                        targetId = targetId[1:-1]
                    elif targetId[0] == '"' and targetId[-1] == '"':
                        targetId = targetId[1:-1]
                    print(targetId)
                    for item in self.html_collection.elements:
                        print(item.id,targetId)
                        if item.id == targetId:
                            element = item
                            break
                    #print(m.group(3))
                    if m.group(3) == "onclick":
                        body = []
                        i += 1
                        while i < len(lines) and "}" not in lines[i]:
                            body.append(lines[i])
                            i += 1
                        func = ";".join(body)
                        print(func)
                        i += 1
                        print(element)
                        if element is not None:
                            element.onclick = func
                        continue
                    if m.group(3) == "innerText":
                        print(element)
                        if element is not None:
                            text = line.split("=",1)
                            text = text[1]
                            print(text)
                            text  = self.eval_value(text)
                            print(text)
                            element.JSOveride["innerText"] =text
                            element.boundObject.configure(text_content=text)
                            #element.boundObject.configure(text="test")

                        i+=1

                        continue

                    #


            print("JS error:", line)
            i += 1

    def eval_value(self, val):
        val = val.strip()
        if val.startswith(("'", '"')) and val.endswith(("'", '"')):
            return val[1:-1]
        if val.isdigit():
            return int(val)
        if val == "true":
            return True
        if val == "false":
            return False
        else:
            if True in [x in val for x in list("+-/*")]:
                #Replace variables
                if True in [x in val for x in ["'", '"']]:
                    operationType = "string"
                else:
                    operationType = "number"
                for var_name, var_value in self.vars.items():
                    #Determine the type of operation

                    if operationType == "string":
                        var_value = f"str({var_value})"
                    elif operationType == "number":
                        var_value = f"{var_value}"
                    val = val.replace(var_name, str(var_value))



                print(val)
                try:
                    return eval(val)
                except Exception as e:
                    print(e)
                    return val

        return self.vars.get(val, "")

    def eval_condition(self, cond):
        m = re.match(r'(\w+)\s*={2,3}\s*(.+)', cond)
        if m:
            return self.vars.get(m.group(1)) == self.eval_value(m.group(2))
        return bool(self.vars.get(cond))

    def split_statements(self, code):
        all_stmts = []
        for line in code.splitlines():
            stmts, buf, depth = [], "", 0
            for c in line:
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                if c == ";" and depth == 0:
                    if buf.strip():
                        stmts.append(buf.strip())
                    buf = ""
                else:
                    buf += c
            if buf.strip():
                stmts.append(buf.strip())
            all_stmts.extend(stmts)
        return all_stmts


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
        current_element = self.htmlCollection.addObject(tag, {"attrs": attrs}, tags=[style_tag_name], element_id=attrs.get("id"))
        self.tag_stack.append((tag, attrs, style_tag_name, current_element))


    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False
            self.parse_global_css(self.style_buffer)
            self.style_buffer = ""
            return

        if tag == "script":
            self.in_script = False
            self.js.run(self.script_buffer, [s for _, _, s, _ in self.tag_stack])
            self.script_buffer = ""
            return

        if self.tag_stack and self.tag_stack[-1][0] == tag:
            self.tag_stack.pop()
            # Add an end marker for block-level elements to handle newlines
            if tag in {"p", "h1", "h2", "h3", "h4", "h5", "h6", "div", "li", "button"}:

                self.htmlCollection.addObject(f"end_{tag}")


    def handle_data(self, data):
        if self.in_style:
            self.style_buffer += data
        elif self.in_script:
            self.script_buffer += data
        elif self.tag_stack:
            # Get current tag info from the top of the stack
            tag, attrs, _, element = self.tag_stack[-1]
            # Get all styles from the stack to handle nesting
            style_tags = [s for _, _, s, _ in self.tag_stack]
            
            if data.strip():
                if not element.data.get("content"):
                    element.data["content"] = ""
                element.data["content"] += data.strip()


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
                weight = v
                if weight == "lighter":
                    weight = "normal"
                elif weight == "bolder":
                    weight = "bold"
                elif weight.isdigit():
                    weight_val = int(weight)
                    if weight_val <= 500:
                        weight = "normal"
                    else:
                        weight = "bold"
                props["weight"] = weight
            elif k == "font-size":
                size = re.sub(r"\D", "", v)
                if size:
                    props["size"] = int(size)
            elif k == "font-family":
                k, v = [x.strip() for x in item.split(":", 1)]
                rawdata = v.split(",")
                font = rawdata.pop(0)
                if font[0] == "'" and font[-1] == "'":
                    font = font[1:-1]
                elif font[0] == '"' and font[-1] == '"':
                    font = font[1:-1]
                data = [font]+rawdata
                #print(v,font)
                props["font-family"] = data
            else:
                props[k] = v
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
        text_elements_size = {"h1": 24, "h2": 20, "h3": 18, "h4": 16, "h5": 14, "h6": 12, "p": 10}
        
        for element in cssrenderer.htmlCollection.elements:
            print(element.type,element.data)
            if element.type == "title" and element.data.get("content"):
                root.title(element.data["content"])

            elif element.type.startswith("end_") and element.type[4:] in block_elements:
                # End of a block, start a new line for subsequent elements
                inline_container = tk.Frame(content_frame)
                inline_container.pack(fill="x", anchor="w")

            elif element.type == "br":
                inline_container = tk.Frame(content_frame)
                inline_container.pack(fill="x", anchor="w")

            elif element.data.get("content") or element.data.get("attrs",{}).get("id"):
                content = element.data.get("content","None")
                
                style = {}
                if element.tags:
                    for tag_name in element.tags:
                        if tag_name in cssrenderer.tag_styles:
                            style.update(cssrenderer.tag_styles[tag_name])

                font_family = "Arial" # Hardcoded for now
                font_family = style.get("font-family", [font_family])[0]
                #print(font_family)
                #print(style)
                font_weight = style.get("weight", "normal")
                font_size = style.get("size", text_elements_size.get(element.type, 12))

                text_transform = style.get("text-transform", "none")

                if text_transform == "uppercase":
                    content = content.upper()

                elif text_transform == "lowercase":
                    content = content.lower()

                elif text_transform == "capitalize":
                    content = content.capitalize()

                elif text_transform == "none":
                    pass

                widget_config = {
                    "text": content,
                    "font": (font_family, font_size, font_weight),
                    "fg": style.get("foreground", "black"),
                    "bg": style.get("background"),
                }
                
                widget_config = {k: v for k, v in widget_config.items() if v is not None}

                if element.type == "button":
                    button = tk.Button(inline_container, **widget_config)

                    onclick_js = element.data.get("attrs", {}).get("onclick")
                    if element.onclick:
                        onclick_js = element.onclick

                    if onclick_js:
                        def make_callback(js_code):
                            return lambda: cssrenderer.js.run(js_code)
                        button.config(command=make_callback(onclick_js))

                    element.boundObject = button
                    button.pack(side="left", anchor="nw")
                else:
                    label = TransparentLabel(inline_container, **widget_config)

                    onclick_js = element.data.get("attrs", {}).get("onclick")
                    if element.onclick:
                        onclick_js = element.onclick

                    if onclick_js:
                        label.config(cursor="hand2")
                        def make_callback(js_code):
                            return lambda e: cssrenderer.js.run(js_code)
                        label.bind("<Button-1>", make_callback(onclick_js))
                    elif element.type == "a":
                        link_url = element.data.get("attrs", {}).get("href")
                        if link_url:
                            label.config(fg="blue", cursor="hand2", underline=True)
                            def make_callback(url_to_open):
                                return lambda e: browse(createAbsoluteURL(url,url_to_open), root)
                            label.bind("<Button-1>", make_callback(link_url))

                    element.boundObject = label
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
    #print(segments)
    return prefix+"//"+segments[0]
def createAbsoluteURL(url, givenUrl):
    #print(url,givenUrl)
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
    url = "https://femboycodedev.github.io/htmlTest.github.io/linkTest"
    url = "https://femboycodedev.github.io/htmlTest.github.io/jsTest1"
    browse(url,root)

    root.mainloop()
    #browse("https://example.com")
