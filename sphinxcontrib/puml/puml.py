import os, subprocess, inspect, uuid, re

from docutils import nodes
from sphinx.util.compat import Directive
from docutils.parsers.rst import directives

class PumlDirective(Directive):

    # this enables content in the directive
    has_content = True
    option_spec = {'file': directives.unchanged,
        'height' : directives.unchanged, 
        'width' : directives.unchanged, 
        'scale' : directives.unchanged, 
        'align' : directives.unchanged,
        'figwidth' : directives.unchanged}

    def run(self):
        node = Puml()
        node['puml'] = self.content
        node['caption'] = self.content[0]
        node['file'] = self.options.get('file', None)
        node['height'] = self.options.get('height', None)
        node['width'] = self.options.get('width', None)
        node['scale'] = self.options.get('scale', None)
        node['align'] = self.options.get('align', None)
        node['figwidth'] = self.options.get('figwidth', None)
        node['source'] = self.state_machine.input_lines.source(self.lineno - self.state_machine.input_offset - 1);
        node['file'] = os.path.abspath(os.path.join(os.path.dirname(node['source']),node['file']))

        cl = self.content
        cl.pop(0)
        node['content'] = cl

        return [node]

class Puml(nodes.General, nodes.Element):
    pass

def dbg(string, *args):
    print '--->%s<--:%s' %(string, args)

def get_command(self, node, fileformat):
    cmd = list(str(self.builder.config.puml_path).split())
    cmd.extend('-charset utf-8'.split())
    cmd.extend(str('-t%s'%fileformat).split())
    cmd.extend(str('-o %s'%self.builder.outdir).split())
    return cmd

def do_image(self, node, fileformat):
    fname = os.path.join(self.builder.outdir,'puml-%s.%s'%(str(uuid.uuid4()), fileformat))
    if node['file'] is not None:
        cmd = get_command(self,node, fileformat)
        cmd.extend(node['file'].split())
        try:
            proc = subprocess.Popen(cmd)
        except OSError, err:
            dbg(err)

        msg, errMsg = proc.communicate()
        if proc.returncode != 0:
            dbg('FAILED', errMsg)
        eF = os.path.join(os.path.dirname(fname),
            '%s.%s'%(os.path.basename(node['file']).split('.')[0],fileformat))
        if os.path.exists(eF):
            os.rename(eF, fname)

    return fname

__ALIGNMENT__ = {'right': ('\\begin{flushright}', '\\end{flushright}'),
                 'left': ('\\begin{flushleft}', '\\end{flushleft}'),
                 'center': ('\\begin{center}', '\\end{center}'),
                 None: ('\\begin{center}', '\\end{center}')}

def __check_conflicting_options__(node):
    if node['figwidth'] and (node['width'] or node['height'] or node['scale']):
       errorContext=""
       if 'caption' in node:
           errorContext+="caption:{%s}"%(node['caption'])
	   if 'file' in node:
		   errorContext+="file:{%s}"%(node['file'])
       raise RuntimeError("Can not mix figwidth and options width, height, scale (caption: %s)"%(node['caption']))

def get_factor_from_string(string):
    percent = re.match('([0-9]*) *%', string )
    if percent:
        factor= 1.0*float(percent.group(1))/100.0
    else:
        factor= 1.0*float(node['scale'])
    return factor

def visit_latex(self, node):
    fname = do_image(self, node, self.builder.config.puml_output_latex_format)
    graphOpts = str('')

    __check_conflicting_options__(node)
    if node['figwidth'] is not None:
        # by not going above 99% width we get away from semi-random
        # line wrapping:
        fraction=0.99*get_factor_from_string(node['figwidth'])
        graphOpts+='width=%1.2f\linewidth,'%(fraction)
         
    if node['width'] is not None:
        graphOpts += 'width=%s,' %(node['width'])
    if node['height'] is not None:
        graphOpts += 'height=%s,' %(node['height'])
    if node['scale'] is not None:
        percent = re.match('([0-9]*) *%', node['scale'])
        if percent:
            graphOpts += 'scale=%.3f,' %(float(percent.group(1))/100)
        else:
            graphOpts += 'scale=%s,' %(node['scale'])
    if (node['align'] in __ALIGNMENT__) is False:
        node['align'] = None
    appendblock=""
    appendblock+='\n\\begin{figure}[H]\n%s\\capstart\n' % (__ALIGNMENT__.get(node['align'])[0])
    appendblock+='\n\\includegraphics[%s]{%s}\n' % (graphOpts, self.encode(os.path.basename(fname)))
    appendblock+='\n\\caption{%s}%s\\end{figure}\n' % (node['caption'], __ALIGNMENT__.get(node['align'])[1])
    self.body.append(appendblock)

def visit_html(self, node):
    """ css styles can be used to modify the look. 'umlblock' is used for the whole div
    containing the diagram. 'umlcaptions' is used by the caption text.

    png is used for now (svg is an option but requires more html work to get the scaling option
    right).

    The figwidth attribute is respected. It scales the image relative to the available horizontal space. A 70% size can be written either as 0.7 or 70%.

    Limitations, issues:
    - width and height options are ignored for now.
    - center align option reverts to left alignment.
    - right align option produces figure that goes outside of the parent div if the diagram 
      wider than the div (ie with small browser window).
    """
    alignment = {'right': 'style="float: right;"', 
                 'left': 'style="float: left;"',   
                 'center': 'style="float: left;"', 
                 None: ''}

    __check_conflicting_options__(node)

    # protect some characters from html interpretation?
    caption=node['caption'].replace('','')

    #umlstyle="width:97.5%%;border:2px solid;padding:1ex;background-color:#eeeeee;border-color:#bbbbbb;border-radius:1ex;"

    umlstyle="""padding: 5px;
    background-color: #f7f7f7;
    color: #333333;
    line-height: 120%;
    border: 1px solid #aaaaaa;
    border-left: none;
    border-right: none;"""

    fname = do_image(self, node, self.builder.config.puml_output_html_format)
    # note: svg does also work, but explorer scales without 
    # respecting aspect ratio. For that to work properly, we
    # would have to add the preserveAspectRatio="xMidYMid meet" attribute to all
    # produced svg images (should not be too hard since they are xml)
    graphOpts = str('')
    widthSet=None
    heightSet=None
    if node['figwidth'] is not None:
         fraction=get_factor_from_string(node['figwidth'])
         graphOpts+=' style="max-width:%s%%;min-width:50ex;" '%(round(100.0*fraction))

    #if node['scale'] is not None:
    #     figsize_pt=get_png_size(os.path.join(self.builder.outdir,fname))
    #     percent = re.match('([0-9]*) *%', node['scale'])
    #     if percent:
    #         factor= 1.0*percent.group(1)/100.0
    #     else:
    #         factor= 1.0*float(node['scale'])
    #     figsize_pt=(round(figsize_pt[0]*factor),round(figsize_pt[1]*factor))
    #     graphOpts+=' width="%d" height="%d" '%figsize_pt
    
    alignline=alignment[node['align']]

    # Set relative path to the image from the html file referencing it.
    tmpPath = '%s/%s'%(self.builder.outdir, os.path.dirname(self.builder.current_docname));
    fname = os.path.relpath(fname, tmpPath);

    picline='<a href="%s"><img src="%s" %s></a>' % (fname,fname,graphOpts)
    divline='''
<div %s style="%s" class="umlblock">
  %s<br>
  <div style="max-width: 50ex" class="umlcaptions">%s</div>
</div>
<div style="clear: both"></div>
'''%(alignline,umlstyle,picline,caption)
    self.body.append(divline)

def depart_latex(self, node):
    pass

def depart_html(self, node):
    pass

def setup(app):
    app.add_config_value('puml_path', 'plantuml', '')
    app.add_config_value('puml_epstopdf', 'epstopdf', '')
    app.add_config_value('puml_output_latex_format', 'eps', '')
    app.add_config_value('puml_output_html_format', 'png', '')

    app.add_node(Puml, latex=(visit_latex, depart_latex))
    app.add_node(Puml, html=(visit_html, depart_html))
    app.add_directive('puml', PumlDirective)
