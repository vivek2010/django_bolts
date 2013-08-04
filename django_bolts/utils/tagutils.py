from __future__ import division
from jinja2 import Markup
import math



def create_tagcloud(tags,maxfont=12,minfont=4,maxweight=800,minweight=100,css=""):
    """
    tags should be a list of tuples - (name,url,frequency)    
    """        
    freq =[ f[-1]+1 for f in tags ]
    maxf = max(freq)
    minf = min(freq) 
    result = []
    if css:
        css = "class='%s'"%css
    else:
        css = ""
    for q,url,f in tags:
        f = f + 1
        if maxf == minf:
            nf = 0.5
        else:
            denom = (maxf - minf)      
            nf = (f - minf)/denom
        size =  round( (nf * (maxfont-minfont) ) + minfont ) * 3
        thick = round( (nf * (maxweight-minweight) ) + minweight )
        colors = ['pink','blue','gray','yellow','black']
        colors.reverse()
        tcolors = len(colors)
        color = int((tcolors-1)*nf)
        color = colors[color]                 
        h = "<a href='%s' style='font-size:%dpx;padding:0 0.25em;font-weight:%d; color:%s' %s> %s </a>"%(url,size,thick,color,css,q)
        result.append( Markup(h) )
    return result


if __name__ == '__main__':
    tags = [
        ("asdsd", "Asdasd", 1),
        ("asdsd", "Asdasd", 10),
        ("asdsd", "Asdasd", 4),
        ("asdsd", "Asdasd", 8),
        ("asdsd", "Asdasd", 2),                                    
    ]
    create_tagcloud(tags)