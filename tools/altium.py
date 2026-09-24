import olefile, struct

def records(path):
    data = olefile.OleFileIO(path).openstream('FileHeader').read()
    i, out = 0, []
    while i + 4 <= len(data):
        n = struct.unpack('<I', data[i:i + 4])[0] & 0xFFFFFF
        body = data[i + 4:i + 4 + n].rstrip(b'\0').decode('latin-1')
        i += 4 + n
        rec = {}
        for kv in body.split('|'):
            if '=' in kv:
                k, v = kv.split('=', 1)
                rec[k.upper()] = v
        out.append(rec)
    return out

if __name__ == '__main__':
    import sys
    for idx, r in enumerate(records(sys.argv[1])):
        if r.get('RECORD') in ('215', '216', '217', '218'):
            print(idx - 1, {k: v for k, v in r.items() if k not in ('COLOR', 'AREACOLOR', 'TEXTCOLOR', 'UNIQUEID')})
