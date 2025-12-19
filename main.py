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

        self.tag = ""
        self.attrs = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        print(tag)
        self.tag = tag
        print(attrs)
        self.attrs = attrs

        if tag == "style":
            self.in_style = True
            return

        if tag == "script":
            if "src" in attrs:
                return  # ignore external JS safely
            self.in_script = True
            return

        if tag == "br":
            self.htmlCollection.addObject("br", tags=list(self.tag_stack))
            return

        styles = {}
        styles.update(self.css_rules.get(tag, {}))
        if "class" in attrs:
            styles.update(self.css_rules.get("." + attrs["class"], {}))
        if "id" in attrs:
            styles.update(self.css_rules.get("#" + attrs["id"], {}))
        styles.update(self.parse_css_block(attrs.get("style", "")))

        tag_name = f"tk_{len(self.tag_stack)}"
        self.tag_styles[tag_name] = styles
        self.tag_stack.append(tag_name)

    def handle_endtag(self, tag):
        if tag == "style":
            self.in_style = False
            self.parse_global_css(self.style_buffer)
            self.style_buffer = ""
            return

        if tag == "script":
            self.in_script = False
            self.js.run(self.script_buffer, self.tag_stack)
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
            print(data)

            self.htmlCollection.addObject(self.tag, {"content": data,"attrs":self.attrs}, tags=list(self.tag_stack))

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


# ================== BROWSER ==================

def browse(url, root = None, isHtml = False):
    if root == None:
        root = tk.Tk()
    
    root.title("Python Mini Browser")

    #txt = tk.Text(root, wrap="word")
    #txt.pack(expand=True, fill="both")

    try:
        if not isHtml:
            print("Opening URL")
            with urllib.request.urlopen(url) as r:
                html = r.read().decode("utf-8", errors="ignore")
            print("URL GOT")
        else:
            html = url
        cssrenderer = AdvancedCSSRenderer()
        cssrenderer.feed(html)

        for name, props in cssrenderer.tag_styles.items():
            continue
            txt.tag_configure(
                name,
                foreground=props.get("foreground", "black"),
                background=props.get("background", "white"),
                font=("Arial", props.get("size", 10), props.get("weight", "normal")),
            )
        tkObjects = []
        typeRemap = {"p":"text","h1":"text","h2":"text","h3":"text","h4":"text","h5":"text","h6":"text","a":"link"}
        for element in cssrenderer.htmlCollection.elements:
            
            remmapedType = None
            if element.type in typeRemap:
                remmapedType = typeRemap[element.type]


            if element.type == "title":
                root.title(element.data.get("content", ""))

            if "text" in [element.type,remmapedType]:

                fontSizes = {"p":16,"h1":32,"h2":24,"h3":20,"h4":18,"h5":16,"h6":14}


                text = element.data.get("content", "")

                #print(element.data)
                
                txtTemp = tk.Label(root, text = text, font=("Helvetica", fontSizes[element.type]),justify="left", anchor="w")
                txtTemp.pack(expand=False,anchor="w")
                tkObjects.append(txtTemp)
                #txtTemp.insert(tk.END, , element.tags)
                tkObjects.append(txtTemp)
            if "link" in [element.type, remmapedType]:
                text = element.data.get("content","")
                attrs = element.data.get("attrs","")
                #print(attrs)

                link = attrs.get("href","")

                def clearAndBrowse(url,root,objects):
                    for object in objects:
                        object.destroy()
                    browse(url,root)

                

                redirectFunction = lambda: clearAndBrowse(link,root, tkObjects)

                labelTemp = tk.Button(root,text = text, command = redirectFunction)
                #labelTemp.pack()
                labelTemp.pack(expand=False,anchor="w")
                tkObjects.append(labelTemp)

            elif element.type == "br":
                labelTemp = tk.Label(root,text = "")
                labelTemp.pack()
                tkObjects.append(labelTemp)



    except Exception as e:
        errorLabel = tk.Label(root, text =  f"Error: {e}")
        errorLabel.pack()
        #txt.delete("1.0", tk.END)
        #txt.insert(tk.END,)

    root.mainloop()


# ================== ENTRY ==================

if __name__ == "__main__":
    exampleHtml = '''
    <!DOCTYPE html>
    <html lang="en"><head>
    <meta http-equiv="content-type" content="text/html; charset=windows-1252"><title>Example Domain</title><meta name="viewport" content="width=device-width, initial-scale=1"><style>body{background:#eee;width:60vw;margin:15vh auto;font-family:system-ui,sans-serif}h1{font-size:1.5em}div{opacity:0.8}a:link,a:visited{color:#348}</style></head><body><div><h1>Example Domain</h1><p>This domain is for use in documentation examples without needing permission. Avoid use in operations.</p><p><a href="https://iana.org/domains/example">Learn more</a></p></div>"""
    </body></(html>
    '''
    #browse(exampleHtml,isHtml=True)
    browse("https://example.com")
