#!/usr/bin/env python3
"""Debug: capture the failing str.format frame locals via sys.settrace."""
import sys
sys.path.insert(0, "training")
import gen_corpus_v4 as m
import random

fail_frame = {}

def tracer(frame, event, arg):
    if event == "exception" and arg[0] is ValueError:
        fail_frame["f"] = frame
        fail_frame["exc"] = arg[1]
        return None
    return tracer

sys.settrace(tracer)
rng = random.Random(404)
try:
    for n in range(400):
        lang = rng.choices(list(m.LANG_MIX_V4), weights=list(m.LANG_MIX_V4.values()))[0]
        roll = rng.random()
        if roll < 0.12:
            m.make_negative_v4(rng, lang)
            continue
        if roll < 0.67:
            r = rng.random()
            fam = m._p(rng, m.NEW_FAMILIES_V4) if r < 0.30 else (m._p(rng, m.NEW_FAMILIES_V4) if r < 0.55 else "smuggle-unicode")
        else:
            fam = None
        m.make_doc_v4(rng, lang, fam)
except ValueError:
    pass
finally:
    sys.settrace(None)

f = fail_frame.get("f")
if f:
    print("FAIL in function:", f.f_code.co_name, "line", f.f_lineno)
    print("exc:", fail_frame["exc"])
    for k, v in f.f_locals.items():
        print(f"  {k} = {repr(v)[:160]}")
else:
    print("no ValueError frame captured")
