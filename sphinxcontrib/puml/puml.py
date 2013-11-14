import os, subprocess, inspect, uuid

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
        'align' : directives.unchanged }
	
    def run(self):
        print
    	node = Puml()
    	node['puml'] = self.content
    	node['caption'] = self.content[0]
    	node['file'] = self.options.get('file', None)
    	node['height'] = self.options.get('height', None)
    	node['width'] = self.options.get('width', None)
    	node['scale'] = self.options.get('scale', None)
    	node['align'] = self.options.get('align', None)
    	
    	cl = self.content
    	cl.pop(0)
    	node['content'] = cl

    	dbg(inspect.getmembers(self))
    	for n in inspect.getmembers(self):
    	   dbg('Insp',n)
    	   
        return [node]
        
class Puml(nodes.General, nodes.Element):
    pass

def dbg(string, *args):
	print '--->%s<--:%s' %(string, args)
	
def get_command(self, node):
    cmd = list(str(self.builder.config.puml_path).split())
    cmd.extend('-charset utf-8'.split())
    cmd.extend(str('-t%s'%self.builder.config.puml_output_format).split())
    cmd.extend(str('-o %s'%self.builder.outdir).split())
    return cmd
    
def do_image(self, node):
    fname = os.path.join(self.builder.outdir,'puml-%s.%s'%(str(uuid.uuid4()), self.builder.config.puml_output_format))
    if node['file'] is not None:
        cmd = get_command(self,node)
        cmd.extend(node['file'].split())
        try:
            proc = subprocess.Popen(cmd)
        except OSError, err:
            dbg(err)
            
        msg, errMsg = proc.communicate()
        if proc.returncode != 0:
            dbg('FAILED', errMsg)
        eF = os.path.join(os.path.dirname(fname),
            '%s.%s'%(os.path.basename(node['file']).split('.')[0],self.builder.config.puml_output_format))
        if os.path.exists(eF):
            os.rename(eF, fname)
    return os.path.basename(fname)

__ALIGNMENT__ = {'right': ('\\begin{flushright}', '\\end{flushright}'),
                 'left': ('\\begin{flushleft}', '\\end{flushleft}'),
                 'center': ('\\begin{center}', '\\end{center}'),
                 None: ('\\begin{center}', '\\end{center}')}

def visit_latex(self, node):
    fname = do_image(self, node)
    dbg(fname)
    graphOpts = str('')
    if node['width'] is not None:
        graphOpts += 'width=%s,' %(node['width'])
    if node['height'] is not None:
        graphOpts += 'height=%s,' %(node['height'])
    if node['scale'] is not None:
        graphOpts += 'scale=%s,' %(node['scale'])
    dbg('options', graphOpts)
    dbg(str(node['align']) in __ALIGNMENT__)
    if (node['align'] in __ALIGNMENT__) is False:
        node['align'] = None
        dbg('Align changed')
    self.body.append('\n\\begin{figure}[H]\n%s\\capstart\n' % (__ALIGNMENT__.get(node['align'])[0]))
    self.body.append('\n\\includegraphics[%s]{%s}\n' % (graphOpts, self.encode(fname)))
    self.body.append('\n\\caption{%s}%s\\end{figure}\n' % (node['caption'], __ALIGNMENT__.get(node['align'])[1]));
    


def depart_latex(self, node):
    pass
    
    
def setup(app):
    app.add_config_value('puml_path', 'plantuml', '')
    app.add_config_value('puml_epstopdf', 'epstopdf', '')
    app.add_config_value('puml_output_format', 'eps', '')
    
    app.add_node(Puml, latex=(visit_latex, depart_latex))
    app.add_directive('puml', PumlDirective)
