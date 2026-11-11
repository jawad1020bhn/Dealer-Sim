import re, colorsys, hashlib
p='NIGHTLEDGER.html'
s=open(p,encoding='utf-8').read()
a=s.index('<script>')+8
b=s.index('</script>')
js=s[a:b]

# 1) fix the two stale cyan/red rgba expressions
js=js.replace("rgba(63,224,197,'","rgba(201,162,95,'")
js=js.replace("rgba(255,95,112,'","rgba(198,118,110,'")

# 2) collect distinct hex colours in JS and classify
hexes=[]
for m in re.finditer(r'#[0-9a-fA-F]{6}\b',js):
    h=m.group(0).lower()
    if h not in hexes:hexes.append(h)

def hls(h):
    r,g,b=int(h[1:3],16),int(h[3:5],16),int(h[5:7],16)
    return colorsys.rgb_to_hls(r/255,g/255,b/255)

accents=['#c9a25f','#d9a15b','#c6766e','#7f9c72','#7f9bb5','#a595bb','#b08a5a','#8fa38c','#d2b48c','#9c8fb0']
text_map={'#312d28':'#b5b0a9','#302c27':'#8f8d87','#2f2b26':'#8f8d87','#1c1a17':'#8f8d87'}
mapping={}
counter=0
for h in hexes:
    hue,l,sat=hls(h)
    hd=hue*360
    if h in text_map:
        mapping[h]=text_map[h]
    elif 0.15<=l<0.34 and 15<=hd<=60 and sat<0.30:
        mapping[h]=accents[counter%len(accents)]
        counter+=1
    # else keep (true dark backgrounds, already-light paper, cool dark slate)

for h,new in mapping.items():
    js=js.replace(h,new)

# 3) add a marker so a future transform pass won't re-darken these colours
if '/* PALETTE_NORMALIZED */' not in js:
    js='/* PALETTE_NORMALIZED */\n'+js

s=s[:a]+js+s[b:]
open(p,'w',encoding='utf-8').write(s)
print('mapped',len(mapping),'hex colours')
for h,n in mapping.items():print(h,'->',n)
