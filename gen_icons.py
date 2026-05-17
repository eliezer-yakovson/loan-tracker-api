
from PIL import Image, ImageDraw, ImageFont
import os
out = r'c:\Users\e3251\Downloads\Loan and Debt Calculations\frontend\public'
def make_icon(size, path):
    img = Image.new('RGBA', (size, size), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([0,0,size-1,size-1], fill=(23,49,54))
    pad = int(size*0.08)
    draw.ellipse([pad,pad,size-1-pad,size-1-pad], fill=(34,184,194))
    font_size = int(size*0.45)
    try: font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', font_size)
    except: font = ImageFont.load_default()
    text = u'\u20aa'
    bbox = draw.textbbox((0,0), text, font=font)
    tw,th = bbox[2]-bbox[0],bbox[3]-bbox[1]
    x,y = (size-tw)//2-bbox[0],(size-th)//2-bbox[1]
    draw.text((x,y), text, fill=(255,255,255), font=font)
    img.save(path, 'PNG')
    print('Created', path)
make_icon(192, os.path.join(out,'icon-192.png'))
make_icon(512, os.path.join(out,'icon-512.png'))
make_icon(180, os.path.join(out,'apple-touch-icon.png'))

