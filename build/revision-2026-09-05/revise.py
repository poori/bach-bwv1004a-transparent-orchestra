"""Selective editorial revision; replay from the preserved MusicXML, never MXL.

This is a one-time, source-reviewed edit, not part of the default build.
"""
from pathlib import Path
from copy import deepcopy
import sys,json
import xml.etree.ElementTree as E
sys.path.insert(0,str(Path('src').resolve()))
import validate_outputs as v
BASE=Path('build/revision-2026-09-05')
STEM=v.STEM
root=E.parse(BASE/'before/score'/f'{STEM}.musicxml').getroot()
original=deepcopy(root)
parts={p.get('id'):p for p in root.findall('part')}
changes=[]
def bar(pid,b):return parts[pid].find(f'measure[@number="{b}"]')
def rhythm(n,d):
 for el in list(n):
  if el.tag in ('duration','type','dot','time-modification','beam'):n.remove(el)
 typ,dots={48:('32nd',0),96:('16th',0),144:('16th',1),192:('eighth',0),288:('eighth',1),384:('quarter',0),576:('quarter',1),768:('half',0),1152:('half',1)}[d]
 idx=next((i for i,x in enumerate(n) if x.tag not in ('pitch','rest','chord','grace')),len(n))
 n.insert(idx,E.Element('duration'));n[idx].text=str(d)
 # MusicXML order: duration, tie, voice, type, dot, accidental, ...
 idx=next((i for i,x in enumerate(n) if x.tag not in ('pitch','rest','chord','grace','duration','tie','voice')),len(n))
 n.insert(idx,E.Element('type'));n[idx].text=typ
 for _ in range(dots):idx+=1;n.insert(idx,E.Element('dot'))
def note(p,d,transpose=0):
 n=E.Element('note')
 if p is None:E.SubElement(n,'rest')
 else:
  p-=transpose;pitch=E.SubElement(n,'pitch');step,alter=[('C',0),('C',1),('D',0),('E',-1),('E',0),('F',0),('F',1),('G',0),('G',1),('A',0),('B',-1),('B',0)][p%12]
  E.SubElement(pitch,'step').text=step
  if alter:E.SubElement(pitch,'alter').text=str(alter)
  E.SubElement(pitch,'octave').text=str(p//12-1)
 E.SubElement(n,'voice').text='1';rhythm(n,d);return n

def rests(d):
 result=[]
 for unit in (768,384,192,96,48):
  while d>=unit:result.append(note(None,unit));d-=unit
 assert d==0
 return result

def replace(pid,b,events,reason,slur=False):
 m=bar(pid,b)
 for x in list(m):
  if x.tag in ('note','backup','forward'):m.remove(x)
 # Retain non-note directions and structural attributes, and place notes before final barline.
 idx=next((i for i,x in enumerate(m) if x.tag=='barline'),len(m))
 cursor=0;new=[]
 for s,e,n in sorted(events,key=lambda ev:ev[0]):
  assert s>=cursor,(pid,b,s,cursor)
  if s>cursor:new.extend(rests(s-cursor))
  n=deepcopy(n);n.attrib.pop('default-x',None);n.attrib.pop('default-y',None)
  # Rebuild local bowing only where ownership actually changes.
  if slur:
   for nt in n.findall('notations'):
    for x in list(nt):
     if x.tag=='slur':nt.remove(x)
  new.append(n);cursor=e
 length=768 if b==1 else 1152
 if not events:
  new=[note(None,length)];new[0].find('rest').set('measure','yes');cursor=length
 if cursor<length:new.extend(rests(length-cursor))
 if slur:
  onset=0;groups={}
  for n in new:
   d=int(n.findtext('duration'))
   if n.find('pitch') is not None and d<384:groups.setdefault(onset//384,[]).append(n)
   onset+=d
  for group in groups.values():
   if len(group)>1:
    for n,t in [(group[0],'start'),(group[-1],'stop')]:
     nt=n.find('notations')
     if nt is None:nt=E.SubElement(n,'notations')
     E.SubElement(nt,'slur',type=t,number='1')
 for n in new:m.insert(idx,n);idx+=1
 changes.append({'part':pid,'bar':b,'reason':reason})

def exchange(a,b,num,left=0,right=1152):
 ea=list(v.timed_notes(bar(a,num)));eb=list(v.timed_notes(bar(b,num)))
 def cut(ev):
  inside=[];outside=[]
  for n,s,e in ev:
   assert not(s<left<e or s<right<e),(num,s,e,left,right)
   (inside if left<=s and e<=right else outside).append((s,e,n))
  return inside,outside
 ia,oa=cut(ea);ib,ob=cut(eb)
 replace(a,num,oa+ib,'join a source phrase in one string voice',True)
 replace(b,num,ob+ia,'exchange source strand without adding a doubling',True)

exchange('P12','P13',4)
exchange('P12','P13',5,0,192)
# Quiet major opening: the second violins keep the first eight-bar phrase.
exchange('P13','P1',133,0,384)
exchange('P13','P3',135,0,1056)
exchange('P13','P3',136,0,384)
exchange('P13','P12',137,384,768)
exchange('P13','P14',139,960,1152)
exchange('P13','P12',140,0,384)
exchange('P13','P14',140,384,960)
# Recollection of the opening: first violins, with existing accompaniment exchanged.
for b in (249,250,251,254):exchange('P12','P3',b)
exchange('P12','P3',253,384,1152)
exchange('P12','P13',255,768,1152)
exchange('P12','P13',256,192,960)
exchange('P12','P14',256,960,1152)
# LilyPond melodyOne b.253 rearticulates D4 under a D4 already held by another voice;
# the MIDI merges that unison. Restore this explicit sixteenth-note attack.
ev=[(s,e,n) for n,s,e in v.timed_notes(bar('P12',253))]
ev.append((288,384,note(62,96)))
replace('P12',253,ev,'restore melodyOne D4 reattack from LilyPond bar 253',True)

# Only remove bassoon when BOTH other bass instruments cover every sounding
# interval with the same pitch class. Independent counterpoint is retained.
def covered(n,s,e,events):
 end=s
 for x,a,z in sorted(events,key=lambda x:x[1]):
  if v.pitch_to_midi(x)%12==v.pitch_to_midi(n)%12 and a<=end:end=max(end,z)
 return end>=e
for pid in ('P5','P6'):
 for b in range(1,258):
  ev=list(v.timed_notes(bar(pid,b)))
  c=list(v.timed_notes(bar('P15',b)));db=list(v.timed_notes(bar('P16',b)))
  if ev and all(covered(n,s,e,c) and covered(n,s,e,db) for n,s,e in ev):
   replace(pid,b,[],'remove simultaneous bassoon/cello/violone octave tripling')
   # Remove expressive directions belonging solely to the deleted material.
   for d in list(bar(pid,b).findall('direction')):
    if d.find('direction-type/wedge') is not None or d.find('direction-type/dynamics') is not None:bar(pid,b).remove(d)
# Let whole concertino units breathe without the 16-foot doubling. Keep a
# unit if removing violone would leave any of its bass pitches unsupported.
for first,last in ((33,52),(77,92),(133,156),(213,228)):
 for a in range(first,last+1,4):
  safe=True
  for b in range(a,a+4):
   support=[ev for pid in ('P5','P6','P15') for ev in v.timed_notes(bar(pid,b))]
   if not all(covered(n,s,e,support) for n,s,e in v.timed_notes(bar('P16',b))):safe=False
  if safe:
   for b in range(a,a+4):
    if bar('P16',b).find('note/pitch') is not None:
     replace('P16',b,[],'release violone for a complete supported concertino unit')
     for d in list(bar('P16',b).findall('direction')):
      if d.find('direction-type/dynamics') is not None:bar('P16',b).remove(d)
# Repair any paired hairpins affected by a removed bassoon bar as pairs, not counts.
for pid in ('P5','P6'):
 active={};remove=[]
 for m in parts[pid].findall('measure'):
  for d in m.findall('direction'):
   for w in d.findall('direction-type/wedge'):
    key=w.get('number','1')
    if w.get('type')!='stop':active[key]=(m,d)
    elif key in active:active.pop(key)
    else:remove.append((m,d))
 remove+=list(active.values())
 for m,d in remove:
  if d in list(m):m.remove(d)

# Hand-shaped brass phrases. Tuples are (start beat, duration beats, concert MIDI).
# Empty bars are intentional breaths. No modulo-four pitch generator is used.
H1={157:[(0,1.5,66),(1.5,.5,69)],158:[(1,2,64)],159:[(0,2,62)],160:[(1,2,64)],
161:[(0,1,66),(1,1,69)],162:[(1,1,64)],163:[(0,2,62)],164:[(1,2,64)],
165:[(0,1.5,66)],166:[(1,1.5,64)],167:[(0,2,62),(2,1,64)],168:[(1,2,64)],
169:[(0,1,66),(1,1.5,69)],170:[(1,2,64)],171:[(0,1.5,64)],172:[(1,2,64)],
173:[(0,1.5,66)],174:[(1,1,66)],175:[(0,1,62)],176:[(0,1,64),(1,1,66),(2,1,64)],
197:[(0,1,66),(1,1.5,66)],198:[(0,1,64),(1,1.5,66)],199:[(1,1.5,64)],200:[(1,2,64)],
201:[(0,1,66),(1,1,66),(2,1,69)],202:[(0,1,66),(1,2,66)],203:[(0,1,64),(1,2,64)],204:[(1,2,64)],
205:[(0,1,62),(1,1,66),(2,1,66)],206:[(0,1,66),(1,1,64),(2,1,64)],207:[(0,2,64)],208:[(1,1.5,64),(2.5,.5,62)]}
H2={157:[(0,2,62)],158:[(1,2,57)],159:[(0,2,54)],160:[],161:[(0,2,62)],162:[],163:[(0,2,54)],164:[(1,2,57)],
165:[(0,1.5,62)],166:[(1,1.5,57)],167:[(0,2,54)],168:[(1,2,57)],169:[(0,2,62)],170:[(1,2,57)],171:[(0,1.5,62)],172:[(1,2,57)],
173:[(0,1.5,62)],174:[(1,1,62)],175:[],176:[(1,1,62),(2,1,57)],197:[(0,2,62)],198:[(1,1.5,62)],199:[(1,1.5,62)],200:[(1,2,57)],
201:[(0,2,62)],202:[(0,3,62)],203:[(1,2,57)],204:[(1,2,57)],205:[(0,3,62)],206:[(2,1,62)],207:[(0,2,57)],208:[(1,1.5,57),(2.5,.5,50)]}
T1={165:[(0,1,74),(1,1.5,78)],166:[(1,1.5,76)],167:[],168:[(1,1.5,81)],
169:[(0,1,74),(1,1.5,78),(2.5,.5,81)],170:[(1,1.5,76)],171:[(1,1,76)],172:[(1,1.5,81)],
173:[(0,1.5,78)],174:[(1,1,74)],175:[],176:[(1,1,78),(2,1,76)],
201:[(0,1,74),(1,1,78)],202:[(1,1.5,78)],203:[(1,1.5,76)],204:[(1,1.5,81)],
205:[(0,1,74),(1,1,78),(2,1,78)],206:[(1,1,76)],207:[(0,1.5,81)],208:[(1,1.5,76),(2.5,.5,74)]}
T2={165:[(0,2,69)],166:[(1,1.5,69)],167:[],168:[],169:[(0,2,74)],170:[(1,1.5,69)],171:[(1,1,74)],172:[(1,1.5,69)],
173:[(0,1.5,74)],174:[],175:[],176:[(1,1,74),(2,1,69)],201:[(0,2,69)],202:[(1,1.5,74)],203:[(1,1.5,69)],204:[(1,1.5,69)],
205:[(0,3,74)],206:[],207:[(0,1.5,69)],208:[(1,1.5,69),(2.5,.5,62)]}
TI={169:[(0,1,50)],170:[],171:[],172:[(1,1,45)],173:[(0,1,50)],174:[],175:[],176:[(2,1,45)],
205:[(0,1,50)],206:[],207:[(0,1,45)],208:[(1,1,45),(2.5,.5,50)]}
for pid,plan in [('P7',H1),('P8',H2),('P9',T1),('P10',T2),('P11',TI)]:
 for b,ev in plan.items():
  events=[(round(s*384),round((s+d)*384),note(p,round(d*384),2 if pid!='P11' else 0)) for s,d,p in ev]
  replace(pid,b,events,'compose brass against local source harmony')
  # Old accents/slurs disappear with old notes. Mark the new structural entries.
  if b in (157,165,169,197,201,205) and events:
   n=bar(pid,b).find('note[pitch]');nt=E.SubElement(n,'notations');E.SubElement(E.SubElement(nt,'articulations'),'accent')
  if not events:
   for d in list(bar(pid,b).findall('direction')):
    if d.find('direction-type/dynamics') is not None:bar(pid,b).remove(d)

def words(pid,b,text):
 m=bar(pid,b);d=E.Element('direction',placement='above');E.SubElement(E.SubElement(d,'direction-type'),'words').text=text
 m.insert(next((i for i,c in enumerate(m) if c.tag not in ('attributes','print')),0),d)
def dynamic(pid,b,value):
 m=bar(pid,b)
 for d in list(m.findall('direction')):
  if d.find('direction-type/dynamics') is not None:m.remove(d)
 d=E.Element('direction',placement='below');E.SubElement(E.SubElement(d,'direction-type'),'dynamics').append(E.Element(value));E.SubElement(d,'sound',dynamics=str({'p':50,'mp':62,'mf':76,'f':90}[value]))
 m.insert(next((i for i,c in enumerate(m) if c.tag=='note'),len(m)),d)
words('P13',133,'Dolce, cantabile; one phrase through 140')
dynamic('P13',133,'mp');dynamic('P3',249,'p')
words('P3',249,'Dolce, beneath the violins')
for pid in ('P7','P8','P9','P10'):
 dynamic(pid,208,'mp')
 words(pid,208,'Dolce; release into the minor')
# Put the quiet-major instruction on the voice that now actually leads it.
for w in bar('P1',133).findall('.//words'):
 if w.text=='Dolce; let the major emerge without weight':w.text='Dolce, beneath Violin II'
# Explicit final-page break prevents MuseScore from clipping lower staff headers.
last_print=E.Element('print',{'new-page':'yes'})
bar('P1',254).insert(0,last_print)
for w in root.findall('.//words'):
 if w.text=='Clarino, broadly; reserve the full tone':w.text='Clarino; reserve full tone'
 if w.text=='Round tone; beneath the moving strings':w.text='Round tone, beneath strings'
# Keep tool provenance in encoding and repository credits, off the title page.
for credit in list(root.findall('credit')):
 if credit.findtext('credit-type')=='arranger':root.remove(credit)
for creator in list(root.findall('identification/creator')):
 if creator.get('type')=='arranger':root.find('identification').remove(creator)
# Metadata keeps honest provenance; no process commentary is added to performance text.
enc=root.find('identification/encoding')
if enc is not None:
 E.SubElement(enc,'encoding-description').text='Selective editorial revision, 5 September 2026; informed by Claude (Anthropic) feedback and source-reviewed by Codex (OpenAI).'
# Reconcile expression with the surviving material, pairing each wedge per staff.
for part in root.findall('part'):
 active={};remove=[]
 for m in part.findall('measure'):
  for d in m.findall('direction'):
   for w in d.findall('direction-type/wedge'):
    key=w.get('number','1')
    if w.get('type')!='stop':
     if key in active:remove.append(active[key])
     active[key]=(m,d)
    elif key not in active:remove.append((m,d))
    else:
     sm,sd=active.pop(key)
     if sm.find('note/pitch') is None or m.find('note/pitch') is None:remove.extend([(sm,sd),(m,d)])
   if m.find('note/pitch') is None and any(w.text in ('solo','ripieno') for w in d.findall('direction-type/words')):remove.append((m,d))
 remove+=list(active.values())
 for m,d in remove:
  if d in list(m):m.remove(d)
E.indent(root,space='  ')
out=Path('score')/f'{STEM}.musicxml'
out.write_text('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">\n'+E.tostring(root,encoding='unicode')+'\n')
(BASE/'revision-audit.json').write_text(json.dumps({'changes':changes,'before':v.musical_metrics(original),'after':v.musical_metrics(root)},indent=2)+'\n')
print('Changed bar-parts',len(changes))
