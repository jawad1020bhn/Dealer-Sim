"""Readers for the decrypted PES 2017 edit file (P17) and the Football Life 27 / PES 2021 edit file (FL).
Layouts follow the4chancup/4ccEditor. Parse only; writers live in the task scripts."""
import struct, unicodedata
u16=lambda d,o:struct.unpack_from('<H',d,o)[0]; u32=lambda d,o:struct.unpack_from('<I',d,o)[0]
def S(d,o,n,enc='utf8'): return d[o:o+n].split(b'\0')[0].decode(enc,'replace')
def norm(s):
    s=unicodedata.normalize('NFKD',s); return ''.join(c for c in s.lower() if c.isalnum() and not unicodedata.combining(c))
POS=['GK','CB','LB','RB','DMF','CMF','LMF','RMF','AMF','LWF','RWF','SS','CF']
PP17=['CF','SS','LWF','RWF','AMF','DMF','CMF','LMF','RMF','CB','LB','RB','GK']
F17=[('atk',7),('def',7),('gk',7),('drib',7),('mo_fk',4),('finish',7),('lowpass',7),('loftpass',7),('header',7),('form',3),('e_player',1),
 ('swerve',7),('catching',7),('clearing',7),('reflex',7),('injury',2),('uB',1),('e_basic',1),
 ('body_ctrl',7),('phys',7),('kick_pwr',7),('exp_pwr',7),('mo_armd',3),('e_regpos',1),
 ('age',6),('reg_pos',4),('uC',1),('play_style',5),('ball_ctrl',7),('ball_win',7),('weak_acc',2),
 ('jump',7),('mo_armr',3),('mo_ck',3),('cover',7),('weak_use',2)]+[('pp_'+p,2) for p in PP17]+[('mo_hd',2),('mo_hr',2),('mo_pk',2),('place_kick',7),
 ('e_playpos',1),('e_ability',1),('e_skill',1),('stamina',7),('speed',7),('e_style',1),('e_com',1),('e_motion',1),('base_copy',1),('uD',1),('foot',1),('uE',1)]+\
 [('com%d'%i,1) for i in range(7)]+[('sk%d'%i,1) for i in range(28)]
assert sum(w for _,w in F17)==280
STATS17=['atk','ball_ctrl','drib','lowpass','loftpass','finish','place_kick','swerve','header','def','ball_win','kick_pwr','speed','exp_pwr','body_ctrl','phys','jump','gk','catching','clearing','reflex','cover','stamina']
def pack17(p):
    """The 35-byte ability block of a PES 2017 player record (record offset +16)."""
    v=0;b=0
    for n,w in F17:
        assert 0<=p[n]<(1<<w),(n,p[n]); v|=p[n]<<b; b+=w
    return v.to_bytes(35,'little')
class P17:
    PSZ=0xBC; P0=0x78; T0=0x3C3E58; TSZ=0x1E0; M0=0x410118; R0=0x475A90; RSZ=164; G0=0x490640; GSZ=0x274
    def __init__(s,path):
        s.d=d=open(path,'rb').read()
        s.np=u16(d,0x5C); s.nt=u16(d,0x60)
        s.players={}; s.porder=[]; s.dups=[]
        for i in range(s.np):
            o=s.P0+i*s.PSZ; p={'i':i,'id':u32(d,o),'u4':d[o+4:o+10],'nation':u16(d,o+10),'height':d[o+12],'weight':d[o+13],'gc1':d[o+14],'gc2':d[o+15]}
            v=int.from_bytes(d[o+16:o+16+35],'little'); b=0
            for n,w in F17: p[n]=(v>>b)&((1<<w)-1); b+=w
            p['name']=S(d,o+0x34,46); p['shirt']=S(d,o+0x62,18,'latin1'); p['app_id']=u32(d,o+0x74); p['raw']=d[o:o+s.PSZ]
            if p['id'] in s.players: s.dups.append(p['id'])
            s.players[p['id']]=p; s.porder.append(p['id'])
        s.teams={}
        for i in range(s.nt):
            o=s.T0+i*s.TSZ; s.teams[u32(d,o)]={'i':i,'id':u32(d,o),'name':S(d,o+0x98,0x46),'abbr':S(d,o+0xDE,4,'latin1'),'raw':d[o:o+s.TSZ]}
        s.rosters={}
        for i in range(s.nt):
            o=s.R0+i*s.RSZ; s.rosters[u32(d,o)]=[(u32(d,o+4+4*k),d[o+132+k]) for k in range(32)]
        s.plans={}
        for i in range(s.nt):
            o=s.G0+i*s.GSZ; tid=u32(d,o); g={'raw':d[o:o+s.GSZ]}
            pres=[]
            for pi in range(3):
                po=o+4+pi*160; forms=[]
                for f in range(3):
                    fo=po+f*33; forms.append({'pos':list(d[fo:fo+11]),'yx':[(d[fo+11+2*k],d[fo+12+2*k]) for k in range(11)]})
                pres.append({'forms':forms,'flags':list(d[po+99:po+106]),'support':d[po+140],'num_atk':d[po+141],'dline':d[po+142],'compact':d[po+143],'num_def':d[po+144]})
            g['presets']=pres; q=o+4+480
            g['xi']=list(d[q:q+11]); g['bench']=list(d[q+11:q+32]); g['takers']=list(d[q+32:q+38]); g['join']=list(d[q+38:q+41]); g['captain']=d[q+41]
            s.plans[tid]=g
        s.managers={}
        for i in range(700):
            o=s.M0+i*88
            if o+88> 0x422500: break
            mid=u32(d,o); nm=S(d,o+9,60)
            if mid or nm: s.managers[mid]={'i':i,'id':mid,'nat':u16(d,o+4),'name':nm}
    def squad(s,t): return [(pid,num) for pid,num in s.rosters.get(t,[]) if pid]
    def isclub(s,t): return bool(s.teams[t]['raw'][0x1A]&0x20)
# ---- FL27 / PES21
class FL:
    G0=0xA09880; GSZ=0x274
    def __init__(s,path):
        s.d=d=open(path,'rb').read()
        T0=0x7C+30000*0x138; s.teams={}
        for i in range(u16(d,0x64)):
            o=T0+i*0x24C; s.teams[u32(d,o)]={'id':u32(d,o),'mgr':u32(d,o+4),'name':S(d,o+0x68,70),'abbr':S(d,o+0xAE,4,'latin1')}
        s.rosters={}
        for i in range(u16(d,0x70)):
            o=0x9D4648+i*0x11C; s.rosters[u32(d,o)]=[(u32(d,o+4+4*k),u16(d,o+0xA4+2*k)) for k in range(40)]
        s.managers={}
        for i in range(u16(d,0x66)):
            o=0x958DA4+i*0x58; s.managers[u32(d,o)]={'id':u32(d,o),'nat':u16(d,o+4),'name':S(d,o+9,60)}
        s.plans={}
        for i in range(u16(d,0x74)):
            o=s.G0+i*s.GSZ; q=o+4+480; pres=[]
            for k in range(3):
                po=o+4+k*160
                pres.append({'pos':list(d[po:po+11]),'yx':[(d[po+11+2*j],d[po+12+2*j]) for j in range(11)],'flags':list(d[po+99:po+106]),'sliders':list(d[po+140:po+145])})
            s.plans[u32(d,o)]={'raw':d[o:o+s.GSZ],'presets':pres,'order':list(d[q:q+40]),'takers':list(d[q+40:q+46]),'captain':d[q+49]}
    def squad(s,t): return [(pid,num) for pid,num in s.rosters.get(t,[]) if pid]
