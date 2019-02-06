"""
LavaVu python interface: interactive HTML UI controls library
"""
import os
import sys
import time
import datetime
import json
from vutils import is_ipython, is_notebook
import weakref

#Register of controls and their actions
actions = []
#Register of windows (viewer instances)
windows = []

vertexShader = """
<script id="line-vs" type="x-shader/x-vertex">
precision highp float;
//Line vertex shader
attribute vec3 aVertexPosition;
attribute vec4 aVertexColour;
uniform mat4 uMVMatrix;
uniform mat4 uPMatrix;
uniform vec4 uColour;
varying vec4 vColour;
void main(void)
{
  vec4 mvPosition = uMVMatrix * vec4(aVertexPosition, 1.0);
  gl_Position = uPMatrix * mvPosition;
  vColour = uColour;
}
</script>
"""

fragmentShader = """
<script id="line-fs" type="x-shader/x-fragment">
precision highp float;
varying vec4 vColour;
void main(void)
{
  gl_FragColor = vColour;
}
</script>
"""

basehtml = """
<html>

<head>
<title>LavaVu Interface</title>
<meta http-equiv="content-type" content="text/html; charset=ISO-8859-1">

---SCRIPTS---

</head>

<body onload="initPage();" oncontextmenu="return false;">
---HIDDEN---
</body>

</html>
"""

inlinehtml = """
---SCRIPTS---
<div id="---ID---" style="display: block; width: ---WIDTH---px; height: ---HEIGHT---px;"></div>
---HIDDEN---

<script>
initPage("---ID---");
</script>
"""

#Some common elements (TODO: dynamically create these when not found)
hiddenhtml = """
<div id="progress" class="popup" style="display: none; width: 310px; height: 32px;">
  <span id="progressmessage"></span><span id="progressstatus"></span>
  <div id="progressbar" style="width: 300px; height: 10px; background: #58f;"></div>
</div>

<div id="hidden" style="display: none">
  <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAkAAAAPCAYAAAA2yOUNAAAAj0lEQVQokWNIjHT8/+zZs//Pnj37/+TJk/9XLp/+f+bEwf9HDm79v2Prqv9aKrz/GUYVEaeoMDMQryJXayWIoi0bFmFV1NWS+z/E1/Q/AwMDA0NVcez/LRsWoSia2luOUAADVcWx/xfO6/1/5fLp/1N7y//HhlmhKoCBgoyA/w3Vyf8jgyyxK4CBUF8zDAUAAJRXY0G1eRgAAAAASUVORK5CYII=" id="slider">
  <canvas id="gradient" width="2048" height="1"></canvas>
  <canvas id="palette" width="512" height="24" class="palette checkerboard"></canvas>
</div>
"""

#Property dict (str json) - set from lavavu
dictionary = '{}'

#Static HTML location
htmlpath = ""

def isviewer(target):
    """Return true if target is a viewer"""
    return not hasattr(target, "parent")

def getviewer(target):
    """Return its viewer if target is vis object
    otherwise just return target as if is a viewer"""
    if not isviewer(target):
        return target.parent
    return target

def getproperty(target, propname):
    """Return value of property from target
    if not defined, return the default value for this property
    """
    _lv = getviewer(target)
    if propname in target:
        return target[propname]
    elif propname in _lv.properties:
        #Get property default
        prop = _lv.properties[propname]
        return prop["default"]
    else:
        return None

_file_cache = dict()

def _webglcode(shaders, css, scripts, menu=True, lighttheme=True, stats=False):
    """
    Returns base WebGL code, by default using full WebGL renderer (draw.js)
    Pass 'drawbox.js' for box interactor only
    """
    code = shaders
    if menu:
        code += getjslibs(scripts + ['menu.js'])
        #HACK: Need to disable require.js to load dat.gui from inline script tags
        code += """
        <script>
        _backup_define = window.define;
        window.define = undefined;
        </script>
        """
        code += getjslibs(['dat.gui.min.js'])
        #Stats module also must be included within hacked section
        if stats:
            code += getjslibs(['stats.min.js'])
        code += """
        <script>
        window.define = _backup_define;
        delete _backup_define;
        </script>
        """
        if lighttheme:
            css.append("dat-gui-light-theme.css")
        #Some css tweaks
        css.append("gui.css")
    else:
        code += getjslibs(scripts)

    code += getcss(css)
    code += '<script id="dictionary" type="application/json">\n' + dictionary + '\n</script>\n'
    return code

def _webglviewcode(shaderpath, menu=True, lighttheme=True):
    """
    Returns WebGL base code for an interactive visualisation window
    """
    return _webglcode(getshaders(shaderpath), ['styles.css'], ['gl-matrix-min.js', 'OK-min.js', 'draw.js'], menu=menu, lighttheme=lighttheme, stats=True)

def _webglboxcode(menu=True, lighttheme=True):
    """
    Returns WebGL base code for the bounding box interactor window
    """
    return _webglcode(fragmentShader + vertexShader, ['control.css'], ['gl-matrix-min.js', 'OK-min.js', 'control.js', 'drawbox.js'], menu=menu, lighttheme=lighttheme)
    #return _webglcode(fragmentShader + vertexShader, ['control.css'], ['gl-matrix-min.js', 'OK.js', 'control.js', 'drawbox.js'], menu=menu, lighttheme=lighttheme)

def getcss(files=["styles.css"]):
    #Load stylesheets to inline tag
    return _filestohtml(files, tag="style")

def getjslibs(files):
    #Load a set of combined javascript libraries in script tags
    return _filestohtml(files, tag="script")

def _filestohtml(files, tag="script"):
    #Load a set of files into a string enclosed in specified html tag
    code = '<' + tag + '>\n'
    for f in files:
        code += _readfilehtml(f)
    code += '\n</' + tag + '>\n'
    return code

def _readfilehtml(filename):
    #Read a file from the htmlpath (or cached copy)
    global _file_cache
    if not filename in _file_cache:
        _file_cache[filename] = _readfile(os.path.join(htmlpath, filename))
    return _file_cache[filename]

def _readfile(filename):
    #Read a text file and return contents
    data = ""
    with open(filename, 'r') as f:
        data = f.read()
        f.close()
    return data

#def getshaders(path, shaders=['points', 'lines', 'triangles']):
def getshaders(path, shaders=['points', 'lines', 'triangles', 'volume']):
    #Load combined shaders
    src = ''
    sdict = {'points' : 'point', 'lines' : 'line', 'triangles' : 'tri', 'volume' : 'volume'};
    for key in shaders:
        src += '<script id="' + key + '-vs" type="x-shader/x-vertex">\n'
        src += _readfile(os.path.join(path, sdict[key] + 'Shader.vert'))
        src += '</script>\n\n'
        src += '<script id="' + key + '-fs" type="x-shader/x-fragment">\n'
        src += _readfile(os.path.join(path, sdict[key] + 'Shader.frag'))
        src += '</script>\n\n'
    return src

class Action(object):
    """Base class for an action triggered by a control

    Default action is to run a command

    also holds the global action list
    """
    actions = []

    def __init__(self, target, command=None, readproperty=None):
        self.target = target
        self.command = command
        if not hasattr(self, "property"):
            self.property = readproperty
        Action.actions.append(self)
        self.lastvalue = 0

    def script(self):
        #Return script action for HTML export
        if self.command is None: return ""
        #Run a command with a value argument
        return self.command + ' " + value + "'

    @staticmethod
    def export_actions(uid=0, port=0, proxy=False):
        #Process actions
        actionjs = '<script type="text/Javascript">\n'
        if port > 0:
            actionjs += 'function init(viewerid) {{_wi[viewerid] = new WindowInteractor(viewerid, {uid}, {port});\n'.format(uid=uid, port=port)
        else:
            actionjs += 'function init(viewerid) {_wi[viewerid] = new WindowInteractor(viewerid, {uid});\n'.format(uid=uid)

        actionjs += '_wi[viewerid].actions = [\n'

        for act in Action.actions:
            #Default placeholder action
            actscript = act.script()
            if len(actscript) == 0:
                #No action
                pass
            #Add to actions list
            actionjs += '  function(value) {_wi[viewerid].execute("' + actscript + '");},\n'
        #Add init and finish
        actionjs += '  null ];\n}\n</script>\n'
        return actionjs

    @staticmethod
    def export(html, filename="control.html", viewerid=0, fullpage=True):
        #Dump all output to control.html in current directory & htmlpath
        #Process actions
        actionjs = Action.export_actions()

        full_html = '<html>\n<head>\n<meta http-equiv="content-type" content="text/html; charset=ISO-8859-1">'
        full_html = '<html>\n<head>\n<meta http-equiv="content-type" content="text/html; charset=ISO-8859-1">'
        full_html += _webglboxcode()
        full_html += actionjs
        full_html += '</head>\n<body onload="init({0});">\n'.format(viewerid)
        full_html += html
        full_html += "\n</body>\n</html>\n"

        #Write the file, locally and in htmlpath
        if filename:
            #This will fail if htmlpath is a non writable location
            #filename = os.path.join(htmlpath, filename)
            hfile = open(filename, "w")
            hfile.write(full_html)
            hfile.close()
        else:
            return full_html

class PropertyAction(Action):
    """Property change action triggered by a control
    """

    def __init__(self, target, prop, command=None, index=None):
        self.property = prop
        #Default action after property set is redraw, can be set to provided
        if command is None:
            command = "redraw"
        self.command = command
        self.index = index
        super(PropertyAction, self).__init__(target, command)

    def script(self):
        #Return script action for HTML export
        #Set a property
        #Check for index (3D prop)
        propset = self.property + '=" + value + "'
        if self.index is not None:
            propset = self.property + '[' + str(self.index) + ']=" + value + "'
        # - Globally
        script = ''
        if isviewer(self.target):
            script = 'select; ' + propset
        # - on an object selector, select the object
        elif type(self.target).__name__ == 'ObjectSelect':
            script = propset
        # - On an object
        else:
            script = '<' + self.target["name"] + '>' + propset
        #Add any additional commands
        return script + '; ' + super(PropertyAction, self).script()


class CommandAction(Action):
    """Command action triggered by a control, with object select before command
    """

    def __init__(self, target, command, readproperty):
        self.command = command
        super(CommandAction, self).__init__(target, command, readproperty)

    def script(self):
        #Return script action for HTML export
        #Set a property
        # - Globally
        script = ''
        if isviewer(self.target):
            script = 'select; '
        # - on an object selector, select the object
        elif type(self.target).__name__ == 'ObjectSelect':
            script = ''
        # - On an object
        else:
            script = '<' + self.target["name"] + '>'
        #Add the commands
        return script + super(CommandAction, self).script()

class FilterAction(PropertyAction):
    """Filter property change action triggered by a control
    """
    def __init__(self, target, findex, prop, command=None):
        self.findex = findex
        if command is None: command = "redraw"
        self.command = command
        super(FilterAction, self).__init__(target, prop)

    def script(self):
        #Return script action for HTML export
        #Set a filter range
        cmd = "filtermin" if self.property == "minimum" else "filtermax"
        return 'select ' + self.target["name"] + '; ' + cmd + ' ' + str(self.findex) + ' " + value + "'
        #propset = "filters=" + json.dumps()
        #script = 'select ' + self.target["name"] + '; ' + propset

class HTML(object):
    """A class to output HTML controls
    """
    lastid = 0

    #Parent class for container types
    def __init__(self):
        self.uniqueid()

    def html(self):
        """Return the HTML code"""
        return ''

    def uniqueid(self):
        #Get a unique control identifier
        HTML.lastid += 1
        self.elid = "lvctrl_" + str(HTML.lastid)
        return self.elid

class Container(HTML):
    """A container for a set of controls
    """
    #Parent class for container types
    def __init__(self, viewer):
        self.viewer = viewer
        self._content = []
        super(Container, self).__init__()

    def add(self, ctrl):
        self._content.append(ctrl)

    def controls(self):
        return self.html()

    def html(self):
        html = ''
        for i in range(len(self._content)):
            html += self._content[i].controls()
        return html

class Window(Container):
    """
    Creates an interaction window with an image of the viewer frame 
    and webgl controller for rotation/translation

    Parameters
    ----------
    align: str
        Set to "left/right" to align viewer window, default is left
    """
    def __init__(self, viewer, align="left"):
        super(Window, self).__init__(viewer)
        self.align = align

    def html(self, wrapper=True, wrapperstyle=""):
        style = 'min-height: 200px; min-width: 200px; position: relative; display: inline-block; '
        style += 'float: ' + self.align + ';'
        if wrapper:
            style += ' margin-right: 10px;'
        html = ""
        html += '<div style="' + style + '">\n'
        html += '<img id="imgtarget_---VIEWERID---" draggable=false style="margin: 0px; border: 1px solid #aaa; display: inline-block;" src="iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAQAAAAAYLlVAAAAPUlEQVR42u3OMQEAAAgDINe/iSU1xh5IQPamKgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgLtwAMBsGqBDct9xQAAAABJRU5ErkJggg==">\n'
        html += """
           <div style="display: none; z-index: 200; position: absolute; top: 5px; right: 5px;">
             <select onchange="_wi[---VIEWERID---].box.mode = this.value;">
               <option>Rotate</option>
               <option>Translate</option>
               <option>Zoom</option>
             </select>
             <input type="button" value="Reset" onclick="_wi[---VIEWERID---].execute('reset');">
           </div>"""
        html += '</div>\n'
        #Display any contained controls
        if wrapper:
            html += '<div style="' + wrapperstyle + '" class="lvctrl">\n'
        html += super(Window, self).html()
        if wrapper:
            html += '</div>\n'
        #html += '<div style="clear: both;">\n'
        return html

class Panel(Container):
    """Creates a control panel with an interactive viewer window and a set of controls
    By default the controls will be placed to the left with the viewer aligned to the right

    Parameters
    ----------
    showwin: boolean
        Set to False to exclude the interactive window
    """
    def __init__(self, viewer, showwin=True):
        super(Panel, self).__init__(viewer)
        self.win = None
        if showwin:
            self.win = Window(viewer, align="right")

    def html(self):
        html = ""
        if self.win: html = self.win.html(wrapper=False)
        #Add control wrapper
        html += '<div style="padding:0px; margin: 0px; position: relative;" class="lvctrl">\n'
        html += super(Panel, self).html()
        html += '</div>\n'
        #if self.win: html += self.win.html(wrapperstyle="float: left; padding:0px; margin: 0px; position: relative;")
        return html

class Tabs(Container):
    """Creates a group of controls with tabs that can be shown or hidden

    Parameters
    ----------
    buttons: boolean
        Display the tab buttons for switching tabs
    """
    def __init__(self, target, buttons=True):
        self.tabs = []
        self.buttons = buttons
        super(Tabs, self).__init__(target)

    def tab(self, label=""):
        """Add a new tab, any controls appending will appear in the new tab
        Parameters
        ----------
        label: str
            Label for the tab, if omitted will be blank
        """
        self.tabs.append(label)

    def add(self, ctrl):
        if not len(self.tabs): self.tab()
        self._content.append(ctrl)
        ctrl.tab = len(self.tabs)-1

    def html(self):
        html = """
        <script>
        function openTab_---ELID---(el, tabName) {
          var i;
          var x = document.getElementsByClassName("---ELID---");
          for (i = 0; i < x.length; i++)
             x[i].style.display = "none";  
          document.getElementById("---ELID---_" + tabName).style.display = "block";  

          tabs = document.getElementsByClassName("tab_---ELID---");
          for (i = 0; i < x.length; i++)
            tabs[i].className = tabs[i].className.replace(" lvseltab", "");
          el.className += " lvseltab";
        }
        </script>
        """
        if self.buttons:
            html += "<div class='lvtabbar'>\n"
            for t in range(len(self.tabs)):
                #Add header items
                classes = 'lvbutton lvctrl tab_---ELID---'
                if t == 0: classes += ' lvseltab'
                html += '<button class="' + classes + '" onclick="openTab_---ELID---(this, this.innerHTML)">---LABEL---</button>'
                html = html.replace('---LABEL---', self.tabs[t])
            html += "</div>\n"
        for t in range(len(self.tabs)):
            #Add control wrappers
            style = ''
            if t != 0: style = 'display: none;'
            html += '<div id="---ELID---_---LABEL---" style="' + style + '" class="lvtab lvctrl ---ELID---">\n'
            for ctrl in self._content:
                if ctrl.tab == t:
                    html += ctrl.controls()
            html += '</div>\n'
            html = html.replace('---LABEL---', self.tabs[t])
        html = html.replace('---ELID---', self.elid)
        return html

class Control(HTML):
    """
    Control object

    Parameters
    ----------
    target: Obj or Viewer
        Add a control to an object to control object properties
        Add a control to a viewer to control global proerties and run commands
    property: str
        Property to modify
    command: str
        Command to run
    value: any type
        Initial value of the controls
    label: str
        Descriptive label for the control
    readproperty: str
        Property to read control value from on update (but not modified)
    """

    def __init__(self, target, property=None, command=None, value=None, label=None, index=None, readproperty=None):
        super(Control, self).__init__()
        self.label = label

        #Get id and add to register
        self.id = len(Action.actions)

        #Can either set a property directly or run a command
        self.property = readproperty
        self.target = target
        if property:
            #Property set
            action = PropertyAction(target, property, command, index)
            if label is None:
                self.label = property.capitalize()
            self.property = property
        elif command:
            #Command only
            action = CommandAction(target, command, readproperty)
            if label is None:
                self.label = command.capitalize()
        else:
            #Assume derived class will fill out the action, this is just a placeholder
            action = Action(target)

        if not self.label:
            self.label = ""

        #Get value from target or default if not provided
        if property is not None and target:
            if value is None:
                value = getproperty(target, property)
            else:
                target[property] = value #Set the provided value
        self.value = value

        #Append reload command from prop dict if no command provided
        if target and property is not None:
            _lv = getviewer(target)
            if  property in _lv.properties:
                prop = _lv.properties[property]
                #TODO: support higher reload values
                cmd = ""
                if prop["redraw"] > 1 and not "reload" in str(command):
                    cmd = "reload"
                elif prop["redraw"] > 0 and not "redraw" in str(command):
                    cmd = "reload"
                #Append if command exists
                if command is None:
                    command = cmd
                else:
                   command += " ; " + cmd

    def onchange(self):
        return "_wi[---VIEWERID---].do_action(" + str(self.id) + ", this.value, this);"

    def show(self):
        #Show only this control
        html = '<div style="" class="lvctrl">\n'
        html += self.html()
        html += '</div>\n'

    def html(self):
        return self.controls()

    def labelhtml(self):
        #Default label
        html = ""
        if len(self.label):
            html += '<p>' + self.label + ':</p>\n'
        return html

    def controls(self, type='number', attribs={}, onchange=""):
        #Input control
        html =  '<input id="---ELID---" class="---ELID---" type="' + type + '" '
        for key in attribs:
            html += key + '="' + str(attribs[key]) + '" '
        #Set custom attribute for property controls
        html += self.attribs()
        html += 'value="' + str(self.value) + '" '
        #Onchange event
        onchange += self.onchange()
        html += 'onchange="' + onchange + '" '
        html += '>\n'
        html = html.replace('---ELID---', self.elid)
        return html

    def attribs(self):
        html = ""
        if self.property:
            #Set custom attribute for property controls
            if not isviewer(self.target):
                html += 'data-target="' + str(self.target["name"]) + '" '
            html += 'data-property="' + self.property + '" '
        return html

class Divider(Control):
    """A divider element
    """

    def controls(self):
        return '<hr style="clear: both;">\n'

class Number(Control):
    """A basic numerical input control
    """

    def controls(self):
        html = self.labelhtml()
        html += super(Number, self).controls()
        return html + '<br>\n'

class Checkbox(Control):
    """A checkbox control for a boolean value
    """
    def labelhtml(self):
        return '' #'<br>\n'

    def controls(self):
        attribs = {}
        if self.value: attribs = {"checked" : "checked"}
        html = "<label>\n"
        html += super(Checkbox, self).controls('checkbox', attribs)
        html += " " + self.label + "</label><br>\n"
        return html

    def onchange(self):
        return "; _wi[---VIEWERID---].do_action(" + str(self.id) + ", this.checked ? 1 : 0, this);"

class Range(Control):
    """A slider control for a range of values

    Parameters
    ----------
    range: list/tuple
        Min/max values for the range
    """
    def __init__(self, target=None, property=None, command=None, value=None, label=None, index=None, range=None, step=None, readproperty=None):
        super(Range, self).__init__(target, property, command, value, label, index, readproperty)

        #Get range & step defaults from prop dict
        _lv = getviewer(target)
        defrange = [0., 1., 0.]
        if  property is not None and property in _lv.properties:
            prop = _lv.properties[property]
            #Check for integer type, set default step to 1
            T = prop["type"]
            if "integer" in T:
                defrange[2] = 1
            ctrl = prop["control"]
            if len(ctrl) > 1 and len(ctrl[1]) == 3:
                defrange = ctrl[1]

        if range is None:
            range = defrange[0:2]
        if step is None:
            step = defrange[2]

        self.range = range
        self.step = step
        if not step:
            #Assume a step size of 1 if range max-min > 5 and both are integers
            r = range[1] - range[0]
            if r > 5 and range[0] - int(range[0]) == 0 and range[1] - int(range[1]) == 0:
                self.step = 1
            else:
                self.step = r / 100.0

    def controls(self):
        attribs = {"min" : self.range[0], "max" : self.range[1], "step" : self.step}
        html = self.labelhtml()
        html += super(Range, self).controls('number', attribs, onchange='this.nextElementSibling.value=this.value; ')
        html += super(Range, self).controls('range', attribs, onchange='this.previousElementSibling.value=this.value; ')
        return html + '<br>\n'

class Button(Control):
    """A push button control to execute a defined command
    """
    def __init__(self, target, command, label=None):
        super(Button, self).__init__(target, "", command, "", label)

    def onchange(self):
        return "_wi[---VIEWERID---].do_action(" + str(self.id) + ", '', this);"

    def labelhtml(self):
        return ''

    def controls(self):
        html = self.labelhtml()
        html =  '<input class="---ELID---" type="button" value="' + str(self.label) + '" '
        #Onclick event
        html += 'onclick="' + self.onchange() + '" '
        html += '><br>\n'
        html = html.replace('---ELID---', self.elid)
        return html

class Entry(Control):
    """A generic input control for string values
    """
    def controls(self):
        html = self.labelhtml()
        html += '<input class="---ELID---" type="text" value="" '
        html += self.attribs()
        html += ' onkeypress="if (event.keyCode == 13) { _wi[---VIEWERID---].do_action(---ID---, this.value.trim(), this); };"><br>\n'
        html = html.replace('---ELID---', self.elid)
        return html.replace('---ID---', str(self.id))

class Command(Control):
    """A generic input control for executing command strings
    """
    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(command=" ", label="Command", *args, **kwargs)

    def controls(self):
        html = self.labelhtml()
        html += """
        <input class="---ELID---" type="text" value="" 
        onkeypress="if (event.keyCode == 13) { var cmd=this.value.trim(); 
        _wi[---VIEWERID---].do_action(---ID---, cmd ? cmd : 'repeat', this); this.value=''; };"><br>\n
        """
        html = html.replace('---ELID---', self.elid)
        return html.replace('---ID---', str(self.id))

class List(Control):
    """A list of predefined input values to set properties or run commands

    Parameters
    ----------
    options: list
        List of the available value strings
    """
    def __init__(self, target, property=None, options=None, *args, **kwargs):
        #Get default options from prop dict
        if options is None:
            defoptions = []
            _lv = getviewer(target)
            if  property is not None and property in _lv.properties:
                prop = _lv.properties[property]
                ctrl = prop["control"]
                if len(ctrl) > 2 and len(ctrl[2]):
                    defoptions = ctrl[2]
            options = defoptions
        self.options = options
        super(List, self).__init__(target, property, *args, **kwargs)

    def controls(self):
        html = self.labelhtml()
        html += '<select class="---ELID---" id="---ELID---" value="" '
        html += self.attribs()
        html += 'onchange="' + self.onchange() + '">\n'
        for opt in self.options:
            #Each element of options list can be:
            # - dict {"label" : label, "value" : value, "selected" : True/False}
            # - list [value, label, selected]
            # - value only
            if isinstance(opt, dict):
                selected = "selected" if opt.selected else ""
                html += '<option value="' + str(opt["value"]) + '" ' + selected + '>' + opt["label"] + '</option>\n'
            elif isinstance(opt, list) or isinstance(opt, tuple):
                selected = "selected" if len(opt) > 2 and opt[2] else ""
                html += '<option value="' + str(opt[0]) + '" ' + selected + '>' + str(opt[1]) + '</option>\n'
            else:
                html += '<option>' + str(opt) + '</option>\n'
        html += '</select><br>\n'
        html = html.replace('---ELID---', self.elid)
        return html

class Colour(Control):
    """A colour picker for setting colour properties
    """
    def __init__(self, *args, **kwargs):
        super(Colour, self).__init__(command="", *args, **kwargs)

    def controls(self):
        html = self.labelhtml()
        html += """
        <div><div class="colourbg checkerboard">
          <div id="---ELID---" ---ATTRIBS--- class="colour ---ELID---" onclick="
            var col = new Colour(this.style.backgroundColor);
            var offset = [this.getBoundingClientRect().left, this.getBoundingClientRect().top];
            var el = this;
            var savefn = function(val) {
              var c = new Colour(0);
              c.setHSV(val);
              el.style.backgroundColor = c.html();
              _wi[---VIEWERID---].do_action(---ID---, c.html(), el);
            }
            el.picker = new ColourPicker(savefn);
            el.picker.pick(col, offset[0], offset[1]);">
          </div>
        </div></div>
        <script>
        var el = document.getElementById("---ELID---");
        //Set the initial colour
        var col = new Colour('---VALUE---');
        el.style.backgroundColor = col.html();
        </script>
        """
        html = html.replace('---VALUE---', str(self.value))
        html = html.replace('---ELID---', self.elid)
        html = html.replace('---ATTRIBS---', self.attribs())
        return html.replace('---ID---', str(self.id))

class Gradient(Control):
    """A colourmap editor
    """
    def __init__(self, target, *args, **kwargs):
        super(Gradient, self).__init__(target, property="colourmap", command="", *args, **kwargs)
        #Get and save the map id of target object
        if isviewer(target):
            raise(Exception("Gradient control requires an Object target, not Viewer"))
        self.maps = target.parent.state["colourmaps"]
        self.map = None
        for m in self.maps:
            if m["name"] == self.value:
                self.map = m
        self.selected = -1;

    def controls(self):
        html = self.labelhtml()
        html += """
        <canvas id="---ELID---" ---ATTRIBS--- width="512" height="24" class="palette checkerboard">
        </canvas>
        <script>
        var el = document.getElementById("---ELID---"); //Get the canvas
        //Store the maps
        el.colourmaps = ---COLOURMAPS---;
        el.currentmap = ---COLOURMAP---;
        el.selectedIndex = ---SELID---;
        if (!el.gradient) {
          //Create the gradient editor
          el.gradient = new GradientEditor(el, function(obj, id) {
            //Gradient updated
            //var colours = obj.palette.toJSON()
            el.currentmap = obj.palette.get(el.currentmap);
            _wi[---VIEWERID---].do_action(---ID---, JSON.stringify(el.currentmap.colours));
            //_wi[---VIEWERID---].do_action(---ID---, obj.palette.toJSON(), el);

            //Update stored maps list by name
            if (el.selectedIndex >= 0)
              el.colourmaps[el.selectedIndex].colours = el.currentmap.colours; //el.gradient.palette.get();
          }
          , true); //Enable premultiply
        }
        //Load the initial colourmap
        el.gradient.read(el.currentmap.colours);
        </script>
        """
        mapstr = json.dumps(self.maps)
        html = html.replace('---COLOURMAPS---', mapstr)
        if self.map:
            html = html.replace('---COLOURMAP---', json.dumps(self.map))
        else:
            html = html.replace('---COLOURMAP---', '"black white"')
        html = html.replace('---SELID---', str(self.selected))
        html = html.replace('---ELID---', self.elid)
        html = html.replace('---ATTRIBS---', self.attribs())
        return html.replace('---ID---', str(self.id))

class ColourMapList(List):
    """A colourmap list selector, populated by the default colour maps
    """
    def __init__(self, target, selection=None, *args, **kwargs):
        if isviewer(target):
            raise(Exception("ColourMapList control requires an Object target, not Viewer"))
        #Load maps list
        if selection is None:
            selection = target.parent.defaultcolourmaps()
        options = [''] + selection
        #Also add the matplotlib colourmaps if available
        try:
            #Load maps list
            import matplotlib
            import matplotlib.pyplot as plt
            sel = matplotlib.pyplot.colormaps()
            options += matplotlib.pyplot.colormaps()
        except:
            pass

        #Preceding command with '.' calls via python API, allowing use of matplotlib maps
        super(ColourMapList, self).__init__(target, options=options, command=".colourmap", label="Load Colourmap", *args, **kwargs)

class ColourMaps(List):
    """A colourmap list selector, populated by the available colour maps,
    combined with a colourmap editor for the selected colour map
    """
    def __init__(self, target, *args, **kwargs):
        #Load maps list
        if isviewer(target):
            raise(Exception("ColourMaps control requires an Object target, not Viewer"))
        self.maps = target.parent.state["colourmaps"]
        options = [["", "None"]]
        sel = target["colourmap"]
        if sel is None: sel = ""
        for m in range(len(self.maps)):
            options.append([self.maps[m]["name"], self.maps[m]["name"]])
            #Mark selected
            if sel == self.maps[m]["name"]:
                options[-1].append(True)
                sel = m

        self.gradient = Gradient(target)
        self.gradient.selected = sel #gradient editor needs to know selection index
        self.gradient.label = "" #Clear label

        super(ColourMaps, self).__init__(target, options=options, command="", property="colourmap", *args, **kwargs)

    def onchange(self):
        #Find the saved palette entry and load it
        script = """
        var el = document.getElementById('---PALLID---'); 
        var sel = document.getElementById('---ELID---');
        if (sel.selectedIndex > 0) {
          el.selectedIndex = sel.selectedIndex-1;
          el.currentmap = el.colourmaps[el.selectedIndex];
          el.gradient.read(el.currentmap.colours);
        }
        """
        return script + super(ColourMaps, self).onchange()

    def controls(self):
        html = super(ColourMaps, self).controls() + self.gradient.controls()
        html = html.replace('---PALLID---', str(self.gradient.elid))
        return html

class TimeStepper(Range):
    """A time step selection range control with up/down buttons
    """
    def __init__(self, viewer, *args, **kwargs):
        #Acts as a command setter with some additional controls
        super(TimeStepper, self).__init__(target=viewer, label="Timestep", command="timestep", readproperty="timestep", *args, **kwargs)

        self.timesteps = viewer.timesteps()
        self.range = (self.timesteps[0], self.timesteps[-1])
        self.step = 1
        #Calculate step gap
        if len(self.timesteps) > 1:
            self.step = self.timesteps[1] - self.timesteps[0]
        self.value = 0

    def controls(self):
        html = Range.controls(self)
        #Note: unicode symbol escape must use double slash to be
        # passed through to javascript or python will process them
        html += """
        <script>
        var timer_---ELID--- = -1;
        function startTimer_---ELID---() {
          if (timer_---ELID--- >= 0) {
            if (timer_---ELID--- > 0)
              window.cancelAnimationFrame(timer_---ELID---);
            timer_---ELID--- = window.requestAnimationFrame(nextStep_---ELID---);
          }
        }
        function nextStep_---ELID---() {
          el = document.getElementById('---ELID---');
          if (el) {
            //Call again on image load - pass callback
            var V = _wi[---VIEWERID---];
            if (!V.box.canvas.mouse.isdown && !V.box.zoomTimer && (!V.box.gui || V.box.gui.closed))
              V.execute("next", startTimer_---ELID---);
            else
              setTimeout(nextStep_---ELID---, 100);
          }
        }
        function playPause_---ELID---(btn) {
          if (timer_---ELID--- >= 0) {
            btn.value="\\u25BA";
            btn.style.fontSize = "12px"
            window.cancelAnimationFrame(timer_---ELID---);
            timer_---ELID--- = -1;
          } else {
            timer_---ELID--- = 0;
            startTimer_---ELID---();
            btn.value="\\u25ae\\u25ae";
            btn.style.fontSize = "10px"
          }
        }
        </script>
        """
        html += '<input type="button" style="width: 50px;" onclick="var el = document.getElementById(\'---ELID---\'); el.stepDown(); el.onchange()" value="&larr;" />'
        html += '<input type="button" style="width: 50px;" onclick="var el = document.getElementById(\'---ELID---\'); el.stepUp(); el.onchange()" value="&rarr;" />'
        html += '<input type="button" style="width: 60px;" onclick="playPause_---ELID---(this);" value="&#9658;" />'
        html = html.replace('---ELID---', self.elid)
        return html

class DualRange(Control):
    """A set of two range slider controls for adjusting a minimum and maximum range

    Parameters
    ----------
    range: list/tuple
        Min/max values for the range
    """
    def __init__(self, target, properties, values=[None,None], label=None, range=(0.,1.), step=None):
        self.label = label

        self.ctrlmin = Range(target=target, property=properties[0], step=step, value=values[0], range=range, label="")
        self.ctrlmax = Range(target=target, property=properties[1], step=step, value=values[1], range=range, label="")

    def controls(self):
        return self.labelhtml() + self.ctrlmin.controls() + self.ctrlmax.controls()

class Range3D(Control):
    """A set of three range slider controls for adjusting a 3D value

    Parameters
    ----------
    range: list/tuple
        Min/max values for the ranges
    """
    def __init__(self, target, property, label, range=(0.,1.), step=None):
        self.label = label

        curval = getproperty(target, property)

        self.ctrlX = Range(target=target, property=property, step=step, value=curval[0], range=range, label="", index=0)
        self.ctrlY = Range(target=target, property=property, step=step, value=curval[1], range=range, label="", index=1)
        self.ctrlZ = Range(target=target, property=property, step=step, value=curval[2], range=range, label="", index=2)

    def controls(self):
        return self.labelhtml() + self.ctrlX.controls() + self.ctrlY.controls() + self.ctrlZ.controls()

class Filter(Control):
    """A set of two range slider controls for adjusting a minimum and maximum filter range

    Parameters
    ----------
    range: list/tuple
        Min/max values for the filter range
    """
    def __init__(self, target, filteridx, label=None, range=None, step=None):
        self.label = label
        if len(target["filters"]) <= filteridx:
            print("Filter index out of range: ", filteridx, len(target["filters"]))
            return None
        self.filter = target["filters"][filteridx]

        #Default label - data set name
        if label is None:
            self.label = self.filter['by'].capitalize()

        #Get the default range limits from the matching data source
        self.data = target["data"][self.filter['by']]
        if not range:
            #self.range = (self.filter["minimum"], self.filter["maximum"])
            if self.filter["map"]:
                range = (0.,1.)
            else:
                range = (self.data["minimum"], self.data["maximum"])

        self.ctrlmin = Range(step=step, range=range, value=self.filter["minimum"])
        self.ctrlmax = Range(step=step, range=range, value=self.filter["maximum"])

        #Replace actions on the controls
        Action.actions[self.ctrlmin.id] = FilterAction(target, filteridx, "minimum")
        Action.actions[self.ctrlmax.id] = FilterAction(target, filteridx, "maximum")

    def controls(self):
        return self.labelhtml() + self.ctrlmin.controls() + self.ctrlmax.controls()

class ObjectList(Control):
    """A set of checkbox controls for controlling visibility of all visualisation objects
    """
    def __init__(self, viewer, *args, **kwargs):
        super(ObjectList, self).__init__(target=viewer, label="Objects", *args, **kwargs)
        self.objctrls = []
        for obj in viewer.objects.list:
            self.objctrls.append(Checkbox(obj, "visible", label=obj["name"])) 

    def controls(self):
        html = self.labelhtml()
        for ctrl in self.objctrls:
            html += ctrl.controls()
        return html

class ObjectSelect(Container):
    """A list selector of all visualisation objects that can be used to
    choose the target of a set of controls

    Parameters
    ----------
    objects: list
        A list of objects to display, by default all available objects are added
    """
    def __init__(self, viewer, objects=None, *args, **kwargs):
        if not isviewer(viewer):
            print("Can't add ObjectSelect control to an Object, must add to Viewer")
            return
        self.parent = viewer
        if objects is None:
            objects = viewer.objects.list
        
        #Load maps list
        options = [(0, "None")]
        for o in range(len(objects)):
            obj = objects[o]
            options += [(o+1, obj["name"])]

        #The list control
        self._list = List(target=viewer, label="", options=options, command="select", *args, **kwargs)

        #Init container
        super(ObjectSelect, self).__init__(viewer) #, label="Objects", options=options, command="select", *args, **kwargs)

        #Holds a control factory so controls can be added with this as a target
        self.control = ControlFactory(self)

    #def onchange(self):
    #    #Update the control values on change
    #    #return super(ObjectSelect, self).onchange()
    #    return self._list.onchange()

    def __contains__(self, key):
        #print "CONTAINS",key
        obj = Action.actions[self._list.id].lastvalue
        #print "OBJECT == ",obj,(key in self.parent.objects.list[obj-1])
        return obj > 0 and key in self.parent.objects.list[obj-1]

    def __getitem__(self, key):
        #print "GETITEM",key
        obj = Action.actions[self._list.id].lastvalue
        if obj > 0:
            #Passthrough: Get from selected object
            return self.parent.objects.list[obj-1][key]
        return None

    def __setitem__(self, key, value):
        obj = Action.actions[self._list.id].lastvalue
        #print "SETITEM",key,value
        if obj > 0:
            #Passtrough: Set on selected object
            self.parent.objects.list[obj-1][key] = value

    #Undefined method call - pass call to target
    def __getattr__(self, key):
        #__getattr__ called if no attrib/method found
        def any_method(*args, **kwargs):
            #If member function exists on target, call it
            obj = Action.actions[self._list.id].lastvalue
            if obj > 0:
                method = getattr(self.parent.objects.list[obj-1], key, None)
                if method and callable(method):
                    return method(*args, **kwargs)
        return any_method

    def html(self):
        html = '<div style="border: #888 1px solid; display: inline-block; padding: 6px;" class="lvctrl">\n'
        html += self._list.controls()
        html += '<hr>\n'
        html += super(ObjectSelect, self).html()
        html += '</div>\n'
        return html

    def controls(self):
        return self.html()

class ControlFactory(object):
    """
    Create and manage sets of controls for interaction with a Viewer or Object
    Controls can run commands or change properties
    """
    #Creates a control factory used to generate controls for a specified target
    def __init__(self, target):
        self._target = weakref.ref(target)
        self.clear()
        self.interactor = False
        self.output = ""

        #Save types of all control/containers
        def all_subclasses(cls):
            return cls.__subclasses__() + [g for s in cls.__subclasses__() for g in all_subclasses(s)]

        #Control contructor shortcut methods
        #(allows constructing controls directly from the factory object)
        #Use a closure to define a new method to call constructor and add to controls
        def addmethod(constr):
            def method(*args, **kwargs):
                #Return the new control and add it to the list
                newctrl = constr(self._target(), *args, **kwargs)
                self.add(newctrl)
                return newctrl
            return method

        self._control_types = all_subclasses(Control)
        self._container_types = all_subclasses(Container)
        for constr in self._control_types + self._container_types:
            key = constr.__name__
            method = addmethod(constr)
            #Set docstring (+ Control docs)
            if constr in self._control_types:
                method.__doc__ = constr.__doc__ + Control.__doc__
            else:
                method.__doc__ = constr.__doc__
            self.__setattr__(key, method)

    def __call__(self, property, *args, **kwargs):
        """
        Calling with a property name creates the default control for that property
        """
        _lv = getviewer(self._target())
        if  property is not None and property in _lv.properties:
            #Get control info from prop dict
            prop = _lv.properties[property]
            T = prop["type"]
            ctrl = prop["control"]
            if len(ctrl) > 2 and len(ctrl[2]) > 1:
                #Has selections
                return self.List(property, *args, **kwargs)
            if "integer" in T or "real" in T:
                if len(ctrl) > 1 and len(ctrl[1]) == 3:
                    #Has range
                    return self.Range(property, *args, **kwargs)
                else:
                    return self.Number(property, *args, **kwargs)
            elif T == "string":
                return self.Entry(property, *args, **kwargs)
            elif T == "boolean":
                return self.Checkbox(property, *args, **kwargs)
            elif T == "colour":
                return self.Colour(property, *args, **kwargs)
            else:
                print("Unable to determine control type for property: " + property)
                print(prop)

    def add(self, ctrl):
        """
        Add a control
        """
        if type(ctrl) in self._container_types:
            #Save new container, further controls will be added to it
            self._containers.append(ctrl)
        elif len(self._containers):
            #Add to existing container
            self._containers[-1].add(ctrl)
        else:
            #Add to global list
            self._content.append(ctrl)

        #Add to viewer instance list too if not already being added
        if not isviewer(self._target()):
            self._target().parent.control.add(ctrl)

    def show(self, fallback=None):
        """
        Displays all added controls including viewer if any

        fallback: function
            A function which is called in place of the viewer display when run outside IPython
        """
        #Show all controls in container

        #Creates an interactor to connect javascript/html controls to IPython and viewer
        #if no viewer Window() created, it will be a windowless interactor
        viewerid = len(windows)
        if isviewer(self._target()):
            #Append the current viewer ref
            windows.append(self._target())
            #Use viewer instance just added
            viewerid = len(windows)-1

        #Generate the HTML
        html = ""
        chtml = ""
        for c in self._content:
            chtml += c.html()
        if len(chtml):
            html = '<div style="" class="lvctrl">\n' + chtml + '</div>\n'
        for c in self._containers:
            html += c.html()

        #Set viewer id
        html = html.replace('---VIEWERID---', str(viewerid))
        self.output += html

        #Display HTML inline or export
        if is_notebook():
            obj = self._target()
            if not obj.server:
                raise(Exception("LavaVu HTTP Server must be active for interactive controls, set port= parameter to > 0"))

            """
            HTTP server mode interaction, rendering in separate render thread:
             - This should work in all notebook contexts, colab, jupyterlab etc
             - Only problem remaining is port access, from docker or cloud instances etc, need to forward port
             - jupyter-server-proxy packaged (available on pip) supports forwarding port via the jupyter server
            """
            from IPython.display import display,HTML
            #Interaction requires some additional js/css/webgl
            #Insert stylesheet, shaders and combined javascript libraries
            display(HTML(_webglboxcode()))

            #Try and prevent this getting cached
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            html += "<!-- CREATION TIMESTAMP {0} -->".format(timestamp)

            #Pass port and object id from server
            actionjs = Action.export_actions(id(obj), obj.server.port)
            #Output the controls and start interactor
            html += "<script>init({0});</script>".format(viewerid)
            display(HTML(actionjs + html))
        else:
            #Export html file
            Action.export(self.output)
            if callable(fallback): fallback(self._target())

        #Auto-clear after show?
        #Prevents doubling up if cell executed again
        self.clear()

        #Pause to let everything catch up
        #time.sleep(.5)

    def redisplay(self):
        """Update the active viewer image if any
        Applies changes made in python to the viewer and forces a redisplay
        """
        #Find viewer id
        viewerid = windows.index(self._target())
        if is_notebook():
            from IPython.display import display,HTML
            display(HTML('<script>_wi[{0}].redisplay({0});</script>'.format(viewerid)))

    def update(self):
        """Update the control values from current viewer data
        Applies changes made in python to the UI controls
        """
        #NOTE: to do this now, all we need is to trigger a get_state call from interactor by sending any command
        if is_notebook() and len(windows):
            #Find viewer id
            viewerid = windows.index(self._target())
            from IPython.display import display,HTML
            display(HTML('<script>_wi[{0}].execute("");</script>'.format(viewerid)))
        
    def clear(self):
        self._content = []
        self._containers = []


