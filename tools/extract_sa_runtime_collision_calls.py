from pathlib import Path
import re, json, csv
ROOT=Path(__file__).resolve().parents[1]

def parse(path):
 out=[]
 for line in path.read_text(errors='replace').splitlines():
  m=re.match(r'\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} )+)\s*(.*)', line)
  if m: out.append((int(m.group(1),16),m.group(3).strip(),line.rstrip()))
 return out

def find_delta(data):
 pref=bytes([1,0x41,1,0x42,1,0x43,1,0x44])
 return data.find(pref)-0x2e20

def toktext(raw): return ''.join(chr(b) if 32<=b<127 else f'\\x{b:02x}' for b in raw)

def val(lines, idx):
 text=lines[idx][1]
 # coordinates/variables
 if text.startswith('push'):
  m=re.match(r'push\s+0x([0-9a-f]+)\(%bp\)', text)
  if m: return f'bp+{int(m.group(1),16):02x}'
  m=re.match(r'push\s+-0x([0-9a-f]+)\(%bp\)', text)
  if m: return f'bp-{int(m.group(1),16):02x}'
  m=re.match(r'push\s+0x([0-9a-f]+)$', text)
  if m: return int(m.group(1),16)
 if text.startswith('push   %ax'):
  prev2='\n'.join(t for _,t,_ in lines[max(0,idx-3):idx])
  # coordinate patterns: only when the current push directly follows the mov/inc/dec sequence
  if 'mov    0xa(%bp),%ax' in prev2 and 'dec    %ax' in prev2: return 'bp+0a-1'
  if 'mov    0xc(%bp),%ax' in prev2 and 'dec    %ax' in prev2: return 'bp+0c-1'
  if 'mov    0xe(%bp),%ax' in prev2 and 'inc    %ax' in prev2: return 'bp+0e+1'
  if 'mov    0xc(%bp),%ax' in prev2 and 'inc    %ax' in prev2: return 'bp+0c+1'
  mloc = re.search(r'mov    -0x([0-9a-f]+)\(%bp\),%ax', prev2)
  if mloc and 'dec    %ax' in prev2: return f'bp-{int(mloc.group(1),16):02x}-1'
  mloc = re.search(r'mov    0x([0-9a-f]+)\(%bp\),%ax', prev2)
  if mloc and 'dec    %ax' in prev2: return f'bp+{int(mloc.group(1),16):02x}-1'
  # if mov from memory/local exact
  for j in range(idx-1,max(-1,idx-10),-1):
   tt=lines[j][1]
   m=re.match(r'mov\s+\$0x([0-9a-f]+),%ax', tt)
   if m: return int(m.group(1),16)
   m=re.match(r'mov\s+\$0x([0-9a-f]+),%al', tt)
   if m: return int(m.group(1),16)
   if tt.startswith('xor    %ax,%ax'): return 0
   m=re.match(r'mov\s+(-?0x[0-9a-f]+|0x[0-9a-f]+)\(%bp\),%ax', tt)
   if m:
    raw=m.group(1)
    return ('bp-'+raw[3:] if raw.startswith('-0x') else 'bp+'+raw[2:])
   m=re.match(r'mov\s+(-?0x[0-9a-f]+|0x[0-9a-f]+)\(%bp\),%al', tt)
   if m:
    raw=m.group(1)
    return ('bpb-'+raw[3:] if raw.startswith('-0x') else 'bpb+'+raw[2:])
   # stop at a previous push unless it is push cs/ss etc? maybe okay
   if tt.startswith('push'): break
 return '?'

def fmt(v):
 if isinstance(v,int): return f'0x{v:04X}' if v>0xff else f'0x{v:02X}'
 return str(v)


def find_setter_addr(items):
    # The first map-token table starts at CS:2e20. The first matching case calls
    # the runtime cell setter. SAM1 uses 0x1059e; SAM2/SAM3 are shifted.
    for i, (_a, _t, line) in enumerate(items):
        if "mov    $0x2e20,%di" in line or "bf 20 2e" in line:
            for j in range(i, min(len(items), i + 80)):
                m = re.match(r"call\s+0x([0-9a-f]+)$", items[j][1])
                if m:
                    return int(m.group(1), 16)
    raise RuntimeError("could not locate runtime cell setter")


def extract(ep):
 items=parse(ROOT/f'dissassembly/SAM{ep}_unpacked_linear_8086.asm')
 data=(ROOT/f'dissassembly/SAM{ep}_unlz.exe').read_bytes(); delta=find_delta(data)
 setter_addr=find_setter_addr(items)
 out=[]
 for idx,(a,text,line) in enumerate(items):
  if text != f'call   0x{setter_addr:x}': continue
  token_off=None; strcmp_idx=None
  # nearest preceding lcall strcmp and mov imm di; do not cross earlier call 1059e or function start
  for j in range(idx-1,max(-1,idx-80),-1):
   if re.search(r'lcall  \$0x[0-9a-f]+,\$0x724', items[j][1]):
    for k in range(j-1,max(-1,j-8),-1):
     m=re.match(r'mov\s+\$0x([0-9a-f]+),%di', items[k][1])
     if m:
      token_off=int(m.group(1),16); strcmp_idx=j; break
    if token_off is not None: break
  if token_off is None: continue
  # collect non-segment pushes since previous setter call, or since strcmp for first write
  prev_call = max([k for k in range(strcmp_idx+1, idx) if items[k][1]==f'call   0x{setter_addr:x}'] or [strcmp_idx])
  pushes=[]
  for j in range(idx-1, prev_call, -1):
   tt=items[j][1]
   if tt.startswith('push') and not re.match(r'push\s+%(cs|ss|es|ds)$', tt):
    pushes.append(val(items,j))
    if len(pushes)==8: break
  if len(pushes)!=8:
   # maybe no compare, skip
   pass
  pushes=list(reversed(pushes))
  if len(pushes)<8: continue
  y,x,c6,c8,ca,body,foot,unknown=pushes
  raw=data[delta+token_off:delta+token_off+2]
  out.append(dict(call_addr=a, token_offset=token_off, token_hex=raw.hex(' '), token_display=toktext(raw), token_second=raw[1], y=str(y), x=str(x), internal_code=fmt(c6), layer_b=fmt(c8), layer_c=fmt(ca), body_solid=body if isinstance(body,int) else str(body), foot_solid=foot if isinstance(foot,int) else str(foot), unknown=str(unknown)))
 return out


def write_outputs():
    out = ROOT / 'docs' / 'derived_collision_tables_all'
    out.mkdir(exist_ok=True)
    summary = {}
    for ep in (1, 2, 3):
        arr = extract(ep)
        summary[f'SAM{ep}'] = arr
        with (out / f'SAM{ep}_runtime_collision_calls.csv').open('w', newline='') as f:
            if arr:
                w = csv.DictWriter(f, fieldnames=arr[0].keys())
                w.writeheader()
                w.writerows(arr)
        (out / f'SAM{ep}_runtime_collision_calls.json').write_text(json.dumps(arr, indent=2), encoding='utf-8')
    (out / 'runtime_collision_calls.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print('wrote', out)
    for ep in (1,2,3):
        arr=summary[f'SAM{ep}']
        print(f'SAM{ep}: {len(arr)} writes, {len(set(e["token_second"] for e in arr))} unique tokens')

if __name__ == '__main__':
    write_outputs()
