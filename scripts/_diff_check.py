import struct, zlib, math, itertools
def read_png_rgb(p):
    d=open(p,'rb').read(); pos=8; idat=b''
    while pos<len(d):
        ln=struct.unpack('>I',d[pos:pos+4])[0]; typ=d[pos+4:pos+8]
        if typ==b'IHDR': w,h,bd,ct=struct.unpack('>IIBB',d[pos+8:pos+22][:10])
        if typ==b'IDAT': idat+=d[pos+8:pos+8+ln]
        pos+=12+ln
    raw=zlib.decompress(idat); ch=4 if ct==6 else 3; stride=w*ch
    px=bytearray(w*h*3); prev=bytearray(stride); o=0
    for y in range(h):
        f=raw[o]; o+=1; line=bytearray(raw[o:o+stride]); o+=stride
        if f==1:
            for i in range(ch,stride): line[i]=(line[i]+line[i-ch])&255
        elif f==2:
            for i in range(stride): line[i]=(line[i]+prev[i])&255
        elif f==3:
            for i in range(stride): line[i]=(line[i]+((prev[i] if i>=ch else 0)+line[i-ch] if i>=ch else 0)//2)&255
        elif f==4:
            for i in range(stride):
                a=line[i-ch] if i>=ch else 0; b=prev[i]; c=prev[i-ch] if i>=ch else 0
                pp=a+b-c; pa=abs(pp-a); pb=abs(pp-b); pc=abs(pp-c)
                pr=a if (pa<=pb and pa<=pc) else (b if pb<=pc else c)
                line[i]=(line[i]+pr)&255
        prev=line
        for x in range(w): px[(y*w+x)*3:(y*w+x)*3+3]=line[x*ch:x*ch+3]
    return w,h,px

base=r'C:\minimax+comfyUI\ComfyUI\input'
names=['_seg2_true_last','_seg3_first']
imgs={n:read_png_rgb(base+'\\'+n+'.png') for n in names}
for a,b in itertools.combinations(names,2):
    wa,ha,pa=imgs[a]; wb,hb,pb=imgs[b]
    if (wa,ha)!=(wb,hb):
        print(a,'vs',b,': size mismatch',(wa,ha),(wb,hb)); continue
    diff=math.sqrt(sum((pa[i]-pb[i])**2 for i in range(0,len(pa),499))/(len(pa)//499))
    print(a,'vs',b,': RMS',round(diff,1))
