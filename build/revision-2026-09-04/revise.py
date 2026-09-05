"""Replay the musical revision from the local pre-revision snapshot.

Writes replayed.musicxml and replayed-audit.json here, never the master.
The final signature and cue corrections were subsequent editorial changes.
"""
from pathlib import Path
import sys, json, copy
import xml.etree.ElementTree as E
sys.path.insert(0,str(Path('src').resolve()))
from validate_outputs import timed_notes, pitch_to_midi, musical_metrics
from orchestrate_chaconne import MONOPHONIC_RELAYS, INSTRUMENTS
base=Path('build/revision-2026-09-04')
master=Path('score/Bach_BWV1004a_Leipzig_orchestral_realization.musicxml')
r=E.parse(base/'before'/master).getroot()
before=copy.deepcopy(r)
parts={p.get('id'):p for p in r.findall('part')}
changes=[]
def bar(pid,b): return parts[pid].find(f"measure[@number='{b}']")
def words(m,text):
 d=E.Element('direction',placement='above'); E.SubElement(E.SubElement(d,'direction-type'),'words').text=text
 m.insert(next((i for i,c in enumerate(m) if c.tag not in ('attributes','print')),0),d)
def silence(pid,b,reason):
 m=bar(pid,b)
 count=len(m.findall('note/pitch'))
 if not count:return
 for c in list(m):
  if c.tag not in ('attributes','print','barline'):m.remove(c)
 n=E.Element('note');E.SubElement(n,'rest');E.SubElement(n,'duration').text='1152';E.SubElement(n,'voice').text='1';E.SubElement(n,'type').text='half';E.SubElement(n,'dot')
 m.insert(next((i for i,c in enumerate(m) if c.tag=='barline'),len(m)),n)
 changes.append(dict(part=pid,bar=b,removed_notes=count,reason=reason))
# Each brass entry is a complete four-bar unit; the original pitches remain.
windows={'P7':[(157,176),(197,208)],'P8':[(157,176),(197,208)],'P9':[(165,176),(201,208)],'P10':[(165,176),(201,208)],'P11':[(169,176),(205,208)]}
for pid,ranges in windows.items():
 for b in range(133,209):
  if not any(a<=b<=z for a,z in ranges):silence(pid,b,'reserve brass/percussion for staged climaxes')
# Remove only complete secondary-wind bars whose exact sounding events are
# covered by another non-brass voice; leave phrasing/ornaments untouched.
for pid in ('P2','P4'):
 for a,z in ((121,148),(209,220),(241,256)):
  for b in range(a,z+1):
   m=bar(pid,b)
   if any(m.findall(x) for x in ('.//wedge','.//tied','.//trill-mark','.//fermata','.//words')):continue
   notes=list(timed_notes(m))
   others={(s,e,pitch_to_midi(n)) for oid in parts if oid!=pid and oid not in windows for n,s,e in timed_notes(bar(oid,b))}
   if notes and all((s,e,pitch_to_midi(n)) in others for n,s,e in notes):silence(pid,b,'remove exact redundant wind doubling')
levels={'pp':38,'p':50,'mp':62,'mf':76,'f':90,'ff':104}
keyids={inst.key:f'P{i+1}' for i,inst in enumerate(INSTRUMENTS)}
# Keep the existing large-scale curve; distinguish solo line from ground.
for pid,p in parts.items():
 for m in p.findall('measure'):
  b=int(m.get('number'))
  for d in m.findall('direction'):
   dyn=d.find('direction-type/dynamics')
   if dyn is None:continue
   old=dyn[0].tag;new=old
   if pid=='P16':new={'ff':'mf','f':'mf','mf':'mp','mp':'p','p':'pp'}.get(old,old)
   elif pid=='P6':new={'ff':'f','f':'mf','mf':'mp'}.get(old,old)
   if 249<=b<=254:new='mf' if pid in ('P3','P12','P14','P15') else 'mp'
   if b>=255 and pid in ('P6','P16'):new='pp'
   if new!=old:
    dyn[0].tag=new
    sound=d.find('sound')
    if sound is not None:sound.set('dynamics',str(levels[new]))
def dynamic(pid,b,value):
 m=bar(pid,b)
 if m.find('note/pitch') is None:return
 for d in list(m.findall('direction')):
  if d.find('direction-type/dynamics') is not None:m.remove(d)
 d=E.Element('direction',placement='below');E.SubElement(E.SubElement(d,'direction-type'),'dynamics').append(E.Element(value));E.SubElement(d,'sound',dynamics=str(levels[value]))
 m.insert(next((i for i,c in enumerate(m) if c.tag=='note'),len(m)),d)
for pid in ('P7','P8'):
 for b,v in ((157,'mp'),(165,'mf'),(169,'f'),(197,'mp'),(201,'mf'),(205,'f')):dynamic(pid,b,v)
for pid in ('P9','P10'):
 for b,v in ((165,'mf'),(169,'f'),(201,'mf'),(205,'f')):dynamic(pid,b,v)
for b in (169,205):dynamic('P11',b,'mf')
# Mark the newly exposed structural entries, replacing removed early accents.
for pid,entries in {'P7':(157,169,197,205),'P8':(157,169,197,205),'P9':(165,169,201,205),'P10':(165,169,201,205),'P11':(169,205)}.items():
 for b in entries:
  n=bar(pid,b).find('note[pitch]')
  if n is None:continue
  nt=n.find('notations')
  if nt is None:nt=E.SubElement(n,'notations')
  ar=nt.find('articulations')
  if ar is None:ar=E.SubElement(nt,'articulations')
  if ar.find('accent') is None:E.SubElement(ar,'accent')
# Four-bar handoffs are audible above a lighter basso continuo.
for a,z,key in MONOPHONIC_RELAYS:
 if a<249:dynamic(keyids[key],a,'mf' if a<229 else 'f')
for w in r.findall('.//words'):
 if w.text=='H · D major — ripieno festivo':w.text='H · D major — dolce, luminoso'
 if w.text=='L · Major-mode cadence — tutti':w.text='L · Major-mode cadence — gathering to tutti'
 if w.text=='P · Final ripieno':w.text='P · Final return — nobile, sostenuto'
words(bar('P1',133),'Dolce; let the major emerge without weight')
words(bar('P7',157),'Round tone; beneath the moving strings')
words(bar('P9',165),'Clarino, broadly; reserve the full tone')
words(bar('P11',169),'Support the cadence; never cover the bass')
words(bar('P12',249),'Nobile, come un ricordo')
words(bar('P16',1),'Light foundation; follow the solo voice')
r.find("identification/creator[@type='arranger']").text='Codex (OpenAI)'
# Unique non-brass pitch/rhythm events must survive all thinning.
def events(root):
 return {(int(m.get('number')),s,e,pitch_to_midi(n)) for p in root.findall('part') if p.get('id') not in windows for m in p.findall('measure') for n,s,e in timed_notes(m)}
assert events(before)==events(r)
E.indent(r,space='  ')
(base/'replayed.musicxml').write_text('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">\n'+E.tostring(r,encoding='unicode')+'\n')
report={'changes':changes,'non_brass_pitch_rhythm_event_set_preserved':True,'before':musical_metrics(before),'after':musical_metrics(r)}
(base/'replayed-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print('Revised bars:',len(changes),'removed doubling notes:',sum(c['removed_notes'] for c in changes))
