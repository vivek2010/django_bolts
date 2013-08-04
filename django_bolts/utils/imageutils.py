
from PIL import Image, ImageDraw, ImageFont
from os import chdir, path, makedirs
from django.conf import settings   
import hashlib 
import re

def cropped_thumb(img,thumbsize):
    width, height = img.size    
    if width > height:
        delta = width - height
        left = int(delta/2)
        upper = 0
        right = height + left
        lower = height
    else:
        delta = height - width
        left = 0
        upper = int(delta/2)
        right = width
        lower = width + upper    
    img = img.crop((left, upper, right, lower))
    img.thumbnail(thumbsize, Image.ANTIALIAS)
    return img

class TextToImage(object):
    
    def __init__(self,font_file,font_dir,font_size=16,padding=0):
        """
        Object can be reused
        font_dir has to be relative to the media root
        """
        self.padding = padding
        self.font_type = ImageFont.truetype(font_file,font_size)
        self.font_dir = font_dir
        self.font_path = path.join(settings.MEDIA_ROOT,font_dir)
        try:
            makedirs(self.font_dir)
        except:
            pass

    def convert(self,text,fg="#000000",alt=''):        
        text = re.sub(r'\s+',' ', text).strip()
        md5 = hashlib.md5()
        md5.update(text)
        filename = "%s.png"%md5.hexdigest()
        filepath = path.join(self.font_path,filename)
        url = path.join(settings.MEDIA_URL,self.font_dir,filename)
        imgtag = '<img src="%s" alt="%s" height="15"/>'%(url,alt)        
        if path.exists(filepath): # Make sure img doesn't exist already
            return imgtag
        else:   
            font = self.font_type
            w, h= font.getsize(text)
            padding = self.padding
            img = Image.new('RGBA', (w+padding*2, h+padding*2), (255,255,255,0))
            draw = ImageDraw.Draw(img)
            draw.fontmode = "0" 
            draw.text((padding,padding), text, font=font, fill=fg)
            img.save(filepath,"png",quality=100)
    #        img.show()
        return imgtag

    