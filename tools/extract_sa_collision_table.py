from __future__ import annotations
import re, json, csv
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISS = ROOT / 'dissassembly'

# The token table is addressed as CS:2e20 in the map-token routine.  In the
# unpacked linear image it is at linear 10750 for SAM1; instead of assuming a
# relocation delta, locate the token-byte pattern directly in each EXE.
# Only used for comments; actual CS offset comes from the disassembly.
TOKEN_TABLE_CS_OFF = 0x2E20
TOKEN_TABLE_PREFIX = bytes([0x01, 0x41, 0x01, 0x42, 0x01, 0x43, 0x01, 0x44])

@dataclass
class CollisionEntry:
    token_offset: int
    token_hex: str
    token_display: str
    internal_code: str
    layer_b: str
    layer_c: str
    body_solid: int
    foot_solid: int
    target_x: str = 'x'
    target_y: str = 'y'
    call_addr: int = 0


def parse_asm(path: Path):
    items=[]
    for line in path.read_text(errors='replace').splitlines():
        m=re.match(r'\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} )+)\s*(.*)', line)
        if m:
            items.append((int(m.group(1),16), m.group(3).strip(), line.rstrip()))
    return items


def find_range(items):
    # Locate the first map-token table (bytes 01 41 01 42 ... shown by objdump
    # as bogus instructions), then take the function immediately following it.
    table_i = next(i for i, (_a, _t, line) in enumerate(items) if "01 41 01" in line)
    start = next(i for i in range(table_i + 1, len(items)) if items[i][1] == "mov    %sp,%bp")
    end = next(i for i in range(start + 1, len(items)) if "lret   $0x8" in items[i][1])
    return start, end


def table_cs_offset(items):
    return next(a for a, _t, line in items if "01 41 01" in line)

def token_text(raw: bytes) -> str:
    parts=[]
    for b in raw:
        if 32 <= b < 127:
            parts.append(chr(b))
        else:
            parts.append(f'\\x{b:02x}')
    return ''.join(parts)


def value_from_recent(lines, idx):
    # Return symbolic value pushed by instruction at idx, looking backwards for
    # the mov/xor sequence that prepared AX/AL.
    a,text,line=lines[idx]
    if text.startswith('push   0xc(%bp)'):
        return 'y'
    if text.startswith('push   0xa(%bp)'):
        return 'x'
    m=re.match(r'push\s+0x([0-9a-f]+)$', text)
    if m:
        return f'word_{int(m.group(1),16):04x}'
    if text.startswith('push   %ax'):
        # x-1 special pattern
        prev3='\n'.join(t for _,t,_ in lines[max(0,idx-3):idx])
        if 'mov    0xa(%bp),%ax' in prev3 and 'dec    %ax' in prev3:
            return 'x-1'
        for j in range(idx-1, max(-1, idx-8), -1):
            tt=lines[j][1]
            m=re.match(r'mov\s+\$0x([0-9a-f]+),%ax', tt)
            if m:
                return int(m.group(1),16)
            m=re.match(r'mov\s+\$0x([0-9a-f]+),%al', tt)
            if m:
                return int(m.group(1),16)
            if tt.startswith('xor    %ax,%ax'):
                return 0
            if tt.startswith('push'):
                break
    return '?'


def fmt(v):
    if isinstance(v,int):
        return f'0x{v:04X}' if v>0xff else f'0x{v:02X}'
    return str(v)


def extract_for_episode(ep:int):
    asm_path=DISS/f'SAM{ep}_unpacked_linear_8086.asm'
    exe_path=DISS/f'SAM{ep}_unlz.exe'
    items=parse_asm(asm_path)
    start,end=find_range(items)
    sub=items[start:end]
    data=exe_path.read_bytes()
    table_file_off=data.find(TOKEN_TABLE_PREFIX)
    if table_file_off < 0:
        raise RuntimeError(f'could not locate token table in {exe_path}')
    delta=table_file_off - TOKEN_TABLE_CS_OFF
    entries=[]
    for idx,(a,text,line) in enumerate(sub):
        if not re.match(r'call\s+0x[0-9a-f]+$', text):
            continue
        # nearest compare token pointer before this call
        token_off=None
        for j in range(idx-1, max(-1,idx-50), -1):
            m=re.match(r'mov\s+\$0x([0-9a-f]+),%di', sub[j][1])
            if m:
                token_off=int(m.group(1),16)
                break
        if token_off is None:
            continue
        token=data[delta+token_off:delta+token_off+2]
        pushes=[]
        # collect pushes since jne after strcmp, excluding push %cs
        for j in range(idx-1, max(-1,idx-30), -1):
            tt=sub[j][1]
            if tt.startswith('push') and not tt.startswith('push   %cs'):
                pushes.append(value_from_recent(sub,j))
                if len(pushes)==8:
                    break
        if len(pushes)!=8:
            print('WARN push count',ep,hex(a),len(pushes))
            continue
        pushes=list(reversed(pushes))
        # args order: y,x,c6,c8,ca,body,foot,unknown-bg flag
        y,x,c6,c8,ca,body,foot,_unknown=pushes
        entries.append(CollisionEntry(
            token_offset=token_off,
            token_hex=token.hex(' '),
            token_display=token_text(token),
            internal_code=fmt(c6),
            layer_b=fmt(c8),
            layer_c=fmt(ca),
            body_solid=int(body) if isinstance(body,int) else -1,
            foot_solid=int(foot) if isinstance(foot,int) else -1,
            target_x=str(x),
            target_y=str(y),
            call_addr=a,
        ))
    return entries


def write_outputs():
    out=ROOT/'docs'/'derived_collision_tables'
    out.mkdir(exist_ok=True)
    all_summary={}
    for ep in (1,2,3):
        entries=extract_for_episode(ep)
        all_summary[f'SAM{ep}']=[asdict(e) for e in entries]
        with (out/f'SAM{ep}_collision_table.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(asdict(entries[0]).keys()))
            w.writeheader(); w.writerows(asdict(e) for e in entries)
    (out/'collision_tables.json').write_text(json.dumps(all_summary,indent=2),encoding='utf-8')
    # compare
    base={(e['token_hex'],e['target_x'],e['target_y']):(e['internal_code'],e['layer_b'],e['layer_c'],e['body_solid'],e['foot_solid']) for e in all_summary['SAM1']}
    same=True
    for name,arr in all_summary.items():
        cur={(e['token_hex'],e['target_x'],e['target_y']):(e['internal_code'],e['layer_b'],e['layer_c'],e['body_solid'],e['foot_solid']) for e in arr}
        if cur!=base:
            same=False
    print('episodes identical:',same)
    for ep in (1,2,3):
        print('SAM%d entries'%ep,len(all_summary[f'SAM{ep}']))
    print('wrote',out)

if __name__=='__main__':
    write_outputs()
