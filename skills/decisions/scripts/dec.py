#!/usr/bin/env python3
"""Decision registry: choice -> pack -> iteration. Data lives in <project>/.decisions/.

The journal (log.jsonl) is hash-chained: every entry carries `prev` (hash of the previous
entry) and `h` (sha256 of its canonical content, prev included). `verify` detects any edit,
deletion, insertion or reordering, and cross-checks index.json against a replay of the journal.
All user-facing text comes from i18n catalogs (en, fr, or a project-local catalog).
"""
import argparse, fcntl, hashlib, json, os, re, subprocess, sys, unicodedata
from datetime import datetime
from pathlib import Path

VERSION = "1.0.0"
FORMAT = 3
DIR = ".decisions"
GENESIS = "0" * 64
SK = ("todo", "doing", "done", "validated")  # canonical state keys (stored in the journal)
FIELDS = ("question", "chosen", "alternatives", "reason")
REQ_AT = {2: ("chosen", "reason"), 3: ("chosen", "reason", "alternatives")}  # target state -> required fields
DEFAULTS = {"lang": "en", "max_pack": 6, "min_field": 10, "doc_dir": "docs/decisions"}
PLUG_I18N = Path(__file__).resolve().parent.parent / "i18n"
ANSWER_TAG = "[answer to a question]"
_ctx = {"root": None, "cfg": None, "cat": None}
_LOCK = None


# ---------------------------------------------------------------- config & i18n
def cfg():
    if _ctx["cfg"] is None:
        c, r = dict(DEFAULTS), _ctx["root"]
        if os.environ.get("DECISIONS_LANG"):
            c["lang"] = os.environ["DECISIONS_LANG"]
        try:
            c.update(json.loads((r / DIR / "config.json").read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            pass
        _ctx["cfg"] = c
    return _ctx["cfg"]


def _read_json(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def catalog():
    if _ctx["cat"] is None:
        lang, r = cfg()["lang"], _ctx["root"]
        cat = _read_json(PLUG_I18N / "en.json")
        cat.update(_read_json(PLUG_I18N / f"{lang}.json"))
        if r:
            cat.update(_read_json(r / DIR / "i18n" / f"{lang}.json"))
        _ctx["cat"] = cat
    return _ctx["cat"]


def has_catalog(lang):
    r = _ctx["root"]
    return (PLUG_I18N / f"{lang}.json").exists() or bool(r and (r / DIR / "i18n" / f"{lang}.json").exists())


def T(key, **kw):
    s = catalog().get(key, key)
    return s.format(**kw) if kw else s


def die(key, **kw):
    print(T("err", msg=T(key, **kw)), file=sys.stderr)
    sys.exit(1)


def maxp():
    return int(cfg()["max_pack"])


def warnp():
    return max(1, maxp() - 1)


def SN(i):
    return T(f"state.{i}")


def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower().replace("-", " ").replace("_", " "))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").strip()


def state_names():
    """Every accepted spelling of each state, across all shipped and project catalogs."""
    m = {norm(k): i for i, k in enumerate(SK)}
    m.update({"wip": 1, "ok": 3, "to do": 0, "in progress": 1})
    files = list(PLUG_I18N.glob("*.json"))
    if _ctx["root"]:
        files += list((_ctx["root"] / DIR / "i18n").glob("*.json"))
    for f in files:
        cat = _read_json(f)
        for i in range(4):
            if cat.get(f"state.{i}"):
                m[norm(cat[f"state.{i}"])] = i
    return m


def parse_state(s):
    names = state_names()
    if norm(s) not in names:
        die("bad_state", s=s, names=" | ".join(SK))
    return names[norm(s)]


def sidx(x):
    return SK.index(x) if x in SK else None


# ---------------------------------------------------------------- helpers
def need(v, what):
    if not v or not str(v).strip():
        die("empty", what=T(f"what.{what}"))
    return str(v).strip()


def root(create=False):
    p = Path.cwd()
    for d in [p, *p.parents]:
        if (d / DIR / "index.json").exists():
            _ctx.update(root=d, cfg=None, cat=None)
            return d
    if create:
        _ctx.update(root=p, cfg=None, cat=None)
        return p
    die("no_registry")


def lock(r):
    """Exclusive lock held for the duration of any command that writes."""
    global _LOCK
    if _LOCK is None:
        (r / DIR).mkdir(exist_ok=True)
        _LOCK = open(r / DIR / ".lock", "w")
        fcntl.flock(_LOCK, fcntl.LOCK_EX)


def clean_field(f, v):
    v = " ".join((v or "").split())
    if f == "alternatives" and norm(v) in ("none", "aucune", "aucun", "ninguna", "keine"):
        return "none"
    if len(v) < int(cfg()["min_field"]):
        die("field_vague", label=T(f"field.{f}"), n=len(v), min=cfg()["min_field"])
    return v


def missing(c, target):
    return (["question"] if not c.get("question") else []) + [f for f in REQ_AT.get(target, ()) if not c.get(f)]


def block(cid, c):
    v = lambda f: c.get(f) or T("doc.todo")
    return "\n".join([f"<!-- decisions:{cid} -->", f"## {c['title']}"] + [f"**{T('field.' + f)}**: {v(f)}" for f in FIELDS] + [f"<!-- /decisions:{cid} -->"])


def sync_doc(r, cid, c):
    """Write/refresh the decision's structured block in its document (between markers; other text untouched)."""
    p = r / c["doc"]
    p.parent.mkdir(parents=True, exist_ok=True)
    txt = p.read_text(encoding="utf-8") if p.exists() else f"# {c['title']}\n"
    pat = re.compile(rf"<!-- decisions:{cid} -->.*?<!-- /decisions:{cid} -->", re.S)
    b = block(cid, c)
    txt = pat.sub(lambda m: b, txt, count=1) if pat.search(txt) else txt.rstrip("\n") + "\n\n" + b + "\n"
    p.write_text(txt, encoding="utf-8")


def slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", norm(s))).strip("-")[:50] or "decision"


def docpath(r, doc):
    need(doc, "doc")
    base = r.resolve()
    p = (base / doc).resolve()
    if os.path.isabs(doc) or base not in p.parents:
        die("doc_outside", doc=doc)
    return p, str(p.relative_to(base))


def fhash(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


# ---------------------------------------------------------------- index (atomic writes)
def load(r):
    try:
        db = json.loads((r / DIR / "index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        die("index_bad", e=e)
    v = db.get("v", 0)
    if v > FORMAT:
        die("format_newer", v=v, f=FORMAT)
    if v < FORMAT:
        die("format_older", v=v, f=FORMAT)
    return db


def save(r, db):
    db["v"] = FORMAT
    db["head"] = tail_hash(r)
    tmp = r / DIR / "index.json.tmp"
    tmp.write_text(json.dumps(db, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, r / DIR / "index.json")


# ---------------------------------------------------------------- hash-chained journal
def canon(e):
    return json.dumps(e, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def chash(e):
    return hashlib.sha256(canon({k: v for k, v in e.items() if k != "h"}).encode("utf-8")).hexdigest()


def read_lines(r):
    p = r / DIR / "log.jsonl"
    return [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.exists() else []


def tail_hash(r):
    lines = read_lines(r)
    if not lines:
        return GENESIS
    try:
        h = json.loads(lines[-1]).get("h")
    except ValueError:
        die("journal_tail_bad")
    if not h:
        die("journal_unsealed")
    return h


def log(r, **e):
    """Append a chained entry. `t` = event date (may be retroactive), `rec` = real write time."""
    now = datetime.now().isoformat(timespec="seconds")
    e = {"t": now, **{k: v for k, v in e.items() if v is not None}}
    e["rec"], e["prev"] = now, tail_hash(r)
    e["h"] = chash(e)
    with open(r / DIR / "log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def replay(entries):
    """Replay the journal into expected iterations/packs/decisions; report inconsistent transitions."""
    I, P, C, issues = set(), {}, {}, []
    for no, e in entries:
        t, i = e.get("type"), str(e.get("id", ""))
        if t == "create":
            if i.startswith("C"):
                C[i] = {"title": e.get("title"), "pack": e.get("pack"), "doc": e.get("doc"), "state": 0, "dh": None, **{f: e.get(f, "") for f in FIELDS}}
            elif i.startswith("P"):
                P[i] = e.get("iter")
            elif i.startswith("I"):
                I.add(i)
        elif t in ("state", "regress") and i in C:
            frm, to = sidx(e.get("from")), sidx(e.get("to"))
            if frm != C[i]["state"]:
                issues.append(T("p.transition", n=no, id=i))
            if to is None:
                issues.append(T("p.badstate", n=no, id=i))
                continue
            C[i]["state"] = to
            C[i]["dh"] = e.get("dochash") if to == 3 else None
        elif t == "detail" and i in C:
            C[i].update(e.get("fields") or {})
        elif t == "move" and i in C:
            C[i]["pack"] = str(e.get("to", "")).split()[0]
        elif t == "merge" and i in C and e.get("into") in C and i != e.get("into"):
            absorbed, keep = C.pop(i), C[e["into"]]
            keep["state"] = min(keep["state"], absorbed["state"])
            if e.get("title"):
                keep["title"] = e["title"]
            keep.update(e.get("fields") or {})
            keep["dh"] = e.get("dochash") if keep["state"] == 3 else None
        elif t == "delete" and i in P:
            del P[i]
    return I, P, C, issues


def pack_count(db, pid):
    return sum(1 for c in db["choices"].values() if c["pack"] == pid)


def check(r, with_replay=True):
    """Verify hash chain, head, and index/journal consistency. Modifies nothing."""
    lines, probs, warns, ents = read_lines(r), [], [], []
    prev, unsealed, last_rec = GENESIS, 0, ""
    for no, l in enumerate(lines, 1):
        try:
            e = json.loads(l)
            assert isinstance(e, dict)
        except (ValueError, AssertionError):
            probs.append(T("p.json", n=no)); prev = None
            continue
        ents.append((no, e))
        if "h" not in e:
            unsealed += 1; prev = None
            continue
        if prev is not None and e.get("prev") != prev:
            probs.append(T("p.chain", n=no))
        if chash(e) != e["h"]:
            probs.append(T("p.content", n=no, type=e.get("type"), id=e.get("id")))
        prev = e["h"]
        if e.get("rec") and e["rec"] < last_rec:
            warns.append(T("w.clock", n=no))
        last_rec = max(last_rec, e.get("rec") or "")
    n = len(lines)
    if 0 < unsealed < n:
        probs.append(T("p.partial"))
    head = ents[-1][1].get("h") if ents and unsealed == 0 else (GENESIS if n == 0 else None)
    try:
        db = json.loads((r / DIR / "index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        db = None
        probs.append(T("p.index_missing"))
    if db is not None:
        for p in db.get("packs", {}):
            if pack_count(db, p) > maxp():
                warns.append(T("w.pack_over", pack=idx(db, p), n=pack_count(db, p), max=maxp()))
        inc = [idx(db, k) for k, c in db["choices"].items() if c["state"] >= 2 and missing(c, c["state"])]
        if inc:
            warns.append(T("w.incomplete", n=len(inc), list=", ".join(inc[:8]) + ("…" if len(inc) > 8 else "")))
    synced = None
    if db is not None and unsealed == 0:
        synced = db.get("head") == head
        if not synced:
            probs.append(T("p.head"))
    if with_replay and db is not None and not probs:
        I, P, C, issues = replay(ents)
        probs += issues
        for name, a, b in (("p.iters", db["iterations"], I), ("p.packs", db["packs"], P), ("p.choices", db["choices"], C)):
            if set(a) != set(b):
                probs.append(T(name, a=sorted(a), b=sorted(b)))
        for k in set(db["choices"]) & set(C):
            c, j = db["choices"][k], C[k]
            for f in ("title", "pack", "doc", "state") + FIELDS:
                if c.get(f, "" if f in FIELDS else None) != j[f]:
                    a, b = (SN(c[f]), SN(j[f])) if f == "state" else (c.get(f), j[f])
                    probs.append(T("p.field", id=k, f=f, a=a, b=b))
            if c.get("state") == 3:
                p = r / c["doc"]
                if not p.exists():
                    warns.append(T("w.doc_missing", id=k, doc=c["doc"]))
                elif j["dh"] and fhash(p) != j["dh"]:
                    warns.append(T("w.doc_changed", id=k, doc=c["doc"]))
    return {"n": n, "unsealed": unsealed, "probs": probs, "warns": warns, "head": head, "synced": synced}


def guard(r):
    res = check(r, with_replay=False)
    if res["probs"]:
        die("guard_altered")
    if res["unsealed"]:
        die("guard_unsealed")


# ---------------------------------------------------------------- numeric index & computed states
def bump(ent):
    ent["seq"] = ent.get("seq", 0) + 1
    return ent["seq"]


def idx(db, k):
    """Unique numeric index iteration.pack.decision (e.g. 1.2.3)."""
    if k in db["choices"]:
        c = db["choices"][k]; p = db["packs"][c["pack"]]
        return f"{p['iter'][1:]}.{p['n']}.{c['n']}"
    if k in db["packs"]:
        p = db["packs"][k]
        return f"{p['iter'][1:]}.{p['n']}"
    return k[1:]


def resolve(db, tok):
    """Accept an internal id (C1) or an index (1.2.3)."""
    if tok in db["choices"] or tok in db["packs"] or tok in db["iterations"]:
        return tok
    parts = str(tok).split(".")
    if all(x.isdigit() for x in parts) and len(parts) <= 3:
        for k in (db["iterations"], db["packs"], db["choices"])[len(parts) - 1]:
            if idx(db, k) == tok:
                return k
    die("unknown_id", tok=tok)


def lab(db, ident):
    pre, sep, k = str(ident).rpartition(":")
    try:
        if k in db["choices"] or k in db["packs"] or k in db["iterations"]:
            return f"{pre}{sep}{idx(db, k)}"
    except KeyError:
        pass
    return str(ident)


def nid(db, kind, prefix):
    return f"{prefix}{max([int(k[len(prefix):]) for k in db[kind]] + [0]) + 1}"


def pack_state(db, pid):
    st = [c["state"] for c in db["choices"].values() if c["pack"] == pid]
    return min(st) if st else 0


def iter_state(db, iid):
    st = [pack_state(db, k) for k, p in db["packs"].items() if p["iter"] == iid]
    return min(st) if st else 0


def derived(db):
    d = {f"pack:{k}": pack_state(db, k) for k in db["packs"]}
    d.update({f"iter:{k}": iter_state(db, k) for k in db["iterations"]})
    return d


def active_iter(db):
    return next((k for k in db["iterations"] if iter_state(db, k) < 3), None)


def commit(r, db, before, why, cause):
    """Log derived pack/iteration state changes, then save the index."""
    for k, v in derived(db).items():
        old = before.get(k)
        if (old is not None and old != v) or (old is None and v != 0):
            log(r, type="auto", id=k, **{"from": SK[old] if old is not None else None, "to": SK[v]}, why=T("auto_why", cause=cause, why=why))
    save(r, db)


# ---------------------------------------------------------------- merge candidates & overflow packs
STOP = {"de", "du", "des", "la", "le", "les", "un", "une", "et", "en", "pour", "sur", "avec", "au", "aux", "the", "of", "to", "for", "and", "in", "on", "with", "a", "an", "el", "los", "las", "para", "con", "der", "die", "das", "und"}


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]+", norm(s)) if len(w) > 1 and w not in STOP}


def candidates(db, pid, min_score=0.34):
    cs = sorted([(k, c) for k, c in db["choices"].items() if c["pack"] == pid], key=lambda x: x[1]["n"])
    out = []
    for i in range(len(cs)):
        for j in range(i + 1, len(cs)):
            (ka, a), (kb, b) = cs[i], cs[j]
            why, score = [], 0.0
            if a["doc"] == b["doc"]:
                why.append(T("cand.same_doc")); score = 1.0
            ta, tb = toks(a["title"]), toks(b["title"])
            if ta and tb:
                jac = len(ta & tb) / len(ta | tb)
                if jac >= min_score:
                    why.append(T("cand.titles", pct=round(jac * 100))); score = max(score, jac)
            if score:
                out.append((score, ka, kb, " ; ".join(why)))
    return sorted(out, reverse=True)


def print_candidates(db, pid, top=5):
    cand = candidates(db, pid)[:top]
    if not cand:
        print(T("cands.none", ix=idx(db, pid)))
        return
    print(T("cands.header", ix=idx(db, pid)))
    for sc, ka, kb, why in cand:
        print(f"  {idx(db, ka)} «{db['choices'][ka]['title']}» + {idx(db, kb)} «{db['choices'][kb]['title']}» — {why}")
    print("  " + T("cands.hint"))


def base_title(t):
    return re.sub(r"\s\(\d+\)$", "", t)


def overflow_pack(r, db, pid, why):
    """Overflow pack on the same subject: first non-full sibling, else a new «Title (n)». Returns (id, created)."""
    pk = db["packs"][pid]; it = pk["iter"]
    sibs = sorted([(k, v) for k, v in db["packs"].items() if v["iter"] == it and base_title(v["title"]) == base_title(pk["title"])], key=lambda x: x[1]["n"])
    for k, v in sibs:
        if pack_count(db, k) < maxp():
            return k, False
    nums = [int(m.group(1)) if (m := re.search(r"\((\d+)\)$", v["title"])) else 1 for _, v in sibs]
    p = nid(db, "packs", "P")
    db["packs"][p] = {"title": f"{base_title(pk['title'])} ({max(nums) + 1})", "iter": it, "kind": pk.get("kind", "link"), "n": bump(db["iterations"][it])}
    log(r, type="create", id=p, title=db["packs"][p]["title"], iter=it, why=T("overflow_why", ix=idx(db, pid), n=maxp(), why=why or T("why.newdec")))
    return p, True


# ---------------------------------------------------------------- commands
def detect_doc_dir(r):
    for d in ("docs", "doc", "documentation"):
        if (r / d).is_dir():
            return f"{d}/decisions"
    return DEFAULTS["doc_dir"]


def cmd_init(a):
    r = root(create=True)
    if (r / DIR / "index.json").exists():
        die("init_exists")
    lock(r)
    c = {"lang": a.lang or os.environ.get("DECISIONS_LANG") or DEFAULTS["lang"], "max_pack": a.max_pack or DEFAULTS["max_pack"],
         "min_field": DEFAULTS["min_field"], "doc_dir": a.doc_dir or detect_doc_dir(r)}
    (r / DIR).mkdir(exist_ok=True)
    (r / DIR / "config.json").write_text(json.dumps(c, indent=1) + "\n", encoding="utf-8")
    _ctx.update(cfg=None, cat=None)
    (r / DIR / "log.jsonl").touch()
    log(r, type="init", id="-", why=T("init.why"), config=c)
    save(r, {"iterations": {}, "packs": {}, "choices": {}})
    print(T("init.done", path=r / DIR, lang=c["lang"], doc_dir=c["doc_dir"], max=c["max_pack"]))
    if not has_catalog(c["lang"]):
        print(T("config.nocat", lang=c["lang"], src=PLUG_I18N / "en.json", dst=r / DIR / "i18n" / f"{c['lang']}.json"))


def cmd_config(a):
    r = root(); c = cfg()
    if not a.key:
        print("\n".join(f"{k} = {c[k]}" for k in DEFAULTS))
        return
    if a.key not in DEFAULTS or a.value is None:
        die("config.bad_key", k=a.key, keys=", ".join(DEFAULTS))
    try:
        v = int(a.value) if isinstance(DEFAULTS[a.key], int) else a.value.strip()
        assert v and (not isinstance(v, int) or 0 < v <= 200)
        if a.key == "max_pack":
            assert 2 <= v <= 50
        if a.key == "lang":
            assert re.fullmatch(r"[a-z]{2,3}(-[A-Za-z]{2,4})?", v)
    except (ValueError, AssertionError):
        die("config.bad_val", k=a.key, v=a.value)
    lock(r); guard(r)
    old = c[a.key]
    stored = _read_json(r / DIR / "config.json") or dict(DEFAULTS)
    stored[a.key] = v
    (r / DIR / "config.json").write_text(json.dumps(stored, indent=1) + "\n", encoding="utf-8")
    log(r, type="config", id="-", key=a.key, **{"from": old, "to": v}, why=a.why or T("why.config"))
    save(r, load(r))
    _ctx.update(cfg=None, cat=None)
    print(T("config.set", k=a.key, v=v))
    if a.key == "lang" and not has_catalog(v):
        print(T("config.nocat", lang=v, src=PLUG_I18N / "en.json", dst=r / DIR / "i18n" / f"{v}.json"))


def cmd_iter_new(a):
    r = root(); lock(r); guard(r); db = load(r)
    act = active_iter(db)
    if act and not a.force:
        die("iter_blocked", i=act, state=SN(iter_state(db, act)))
    before = derived(db)
    i = nid(db, "iterations", "I")
    db["iterations"][i] = {"title": need(a.title, "title")}
    log(r, type="create", id=i, title=a.title, why=a.why or T("why.create"))
    commit(r, db, before, a.why or T("why.create"), T("cause.create", id=i))
    print(T("created_iter", ix=idx(db, i), id=i, title=a.title))


def cmd_pack_new(a):
    r = root(); lock(r); guard(r); db = load(r)
    i = resolve(db, a.iter) if a.iter else active_iter(db)
    if not i or i not in db["iterations"]:
        die("no_iter")
    if iter_state(db, i) == 3 and not a.force:
        die("iter_validated_pack", i=i)
    before = derived(db)
    p = nid(db, "packs", "P")
    db["packs"][p] = {"title": need(a.title, "title"), "iter": i, "kind": a.kind, "n": bump(db["iterations"][i])}
    log(r, type="create", id=p, title=a.title, iter=i, why=a.why or T("why.create"))
    commit(r, db, before, a.why or T("why.create"), T("cause.create", id=p))
    print(T("created_pack", ix=idx(db, p), id=p, iter=i, title=a.title))


def cmd_pack_rm(a):
    r = root(); lock(r); guard(r); db = load(r)
    p = resolve(db, a.pack)
    if p not in db["packs"]:
        die("not_pack", id=p)
    if pack_count(db, p):
        die("pack_not_empty")
    before, ix = derived(db), idx(db, p)
    del db["packs"][p]
    log(r, type="delete", id=p, why=a.why)
    commit(r, db, before, a.why, T("cause.delete", id=p))
    print(T("pack_deleted", ix=ix, id=p))


def cmd_add(a):
    r = root(); lock(r); guard(r); db = load(r)
    a.pack = resolve(db, a.pack)
    if a.pack not in db["packs"]:
        die("not_pack", id=a.pack)
    if iter_state(db, db["packs"][a.pack]["iter"]) == 3 and not a.force:
        die("iter_validated_add")
    title = need(a.title, "title")
    if len(title) < 4:
        die("title_short")
    fields = {f: clean_field(f, getattr(a, f)) for f in FIELDS if getattr(a, f)}
    docp, rel = docpath(r, a.doc or f"{cfg()['doc_dir']}/{slug(title)}.md")
    before = derived(db)
    target, note = a.pack, None
    if pack_count(db, a.pack) >= maxp():
        print(T("pack_full", ix=idx(db, a.pack), n=maxp()))
        print_candidates(db, a.pack, top=3)
        if a.no_overflow:
            die("overflow_refused")
        target, made = overflow_pack(r, db, a.pack, a.why)
        note = T("overflow_note", ix=idx(db, a.pack), to=idx(db, target), title=db["packs"][target]["title"]) + (T("overflow_created") if made else "")
    c = nid(db, "choices", "C")
    entry = {"title": title, "pack": target, "doc": rel, "state": 0, "n": bump(db["packs"][target]), **{f: fields.get(f, "") for f in FIELDS}}
    created = not docp.exists()
    db["choices"][c] = entry
    sync_doc(r, c, entry)
    log(r, type="create", id=c, title=title, pack=target, doc=rel, doc_created=created, **fields, why=a.why or T("why.create"))
    commit(r, db, before, a.why or T("why.create"), T("cause.add", id=c))
    print(T("added", ix=idx(db, c), id=c, pack=target, doc=rel) + (T("doc_created") if created else T("doc_block_added")))
    if note:
        print(note)
    n = pack_count(db, target)
    if n >= warnp():
        print(T("warn_pack", ix=idx(db, target), n=n, max=maxp(), full=T("warn_full") if n >= maxp() else ""))


def cmd_detail(a):
    r = root(); lock(r); guard(r); db = load(r)
    k = resolve(db, a.id)
    if k not in db["choices"]:
        die("not_choice", id=k)
    c = db["choices"][k]
    if c["state"] == 3:
        die("detail_validated")
    need(a.why, "why")
    upd = {f: clean_field(f, getattr(a, f)) for f in FIELDS if getattr(a, f)}
    upd = {f: v for f, v in upd.items() if c.get(f) != v}
    if not upd:
        die("detail_nothing")
    log(r, type="detail", id=k, fields=upd, why=a.why)
    c.update(upd)
    sync_doc(r, k, c)
    save(r, db)
    print(T("detail_updated", ix=idx(db, k), labels=", ".join(T("field." + f) for f in upd)))


def cmd_set(a):
    r = root(); lock(r); guard(r); db = load(r)
    a.id = resolve(db, a.id)
    if a.id not in db["choices"]:
        die("not_choice", id=a.id)
    need(a.why, "why")
    c = db["choices"][a.id]
    new, old = parse_state(a.state), c["state"]
    if new == old:
        die("already_state", id=a.id, state=SN(old))
    upd = {f: clean_field(f, getattr(a, f)) for f in FIELDS if getattr(a, f)}
    upd = {f: v for f, v in upd.items() if c.get(f) != v}
    if new > old:
        miss = missing({**c, **upd}, new) if new >= 2 else ([] if c.get("question") or "question" in upd else ["question"])
        if miss:
            die("precision_missing", state=SN(new), labels=", ".join(T("field." + f) for f in miss), flags=" ".join(f'--{f} "…"' for f in miss))
    if new == 3 and fhash(r / c["doc"]) is None:
        die("doc_not_found", doc=c["doc"])
    if new < old:
        cur = int(db["packs"][c["pack"]]["iter"][1:])
        later = [k for k in db["iterations"] if int(k[1:]) > cur and iter_state(db, k) > 0]
        if later and not a.force:
            die("regress_later", later=later)
    before = derived(db)
    if upd:
        log(r, type="detail", id=a.id, fields=upd, why=a.why)
        c.update(upd)
    sync_doc(r, a.id, c)
    dh = fhash(r / c["doc"]) if new == 3 else None
    c["state"] = new
    log(r, type="regress" if new < old else "state", id=a.id, **{"from": SK[old], "to": SK[new]}, why=a.why, dochash=dh)
    commit(r, db, before, a.why, T("cause.set", id=a.id, state=SK[new]))
    print(T("set_done", ix=idx(db, a.id), a=SN(old), b=SN(new)) + (T("regress_mark") if new < old else ""))
    for k, v in derived(db).items():
        if before.get(k) != v:
            kind, ident = k.split(":")
            print(T("derived_line", kind=T(f"kind.{kind}"), ix=idx(db, ident), a=SN(before.get(k, 0)), b=SN(v)))


def cmd_move(a):
    r = root(); lock(r); guard(r); db = load(r)
    a.id, a.pack = resolve(db, a.id), resolve(db, a.pack)
    if a.id not in db["choices"] or a.pack not in db["packs"]:
        die("move_expect")
    need(a.why, "why")
    src, dst = db["packs"][db["choices"][a.id]["pack"]]["iter"], db["packs"][a.pack]["iter"]
    if 3 in (iter_state(db, src), iter_state(db, dst)) and not a.force:
        die("move_validated")
    before = derived(db)
    old, oldi = db["choices"][a.id]["pack"], idx(db, a.id)
    if old == a.pack:
        die("move_same")
    if pack_count(db, a.pack) >= maxp():
        print_candidates(db, a.pack)
        die("move_full", n=maxp())
    db["choices"][a.id]["pack"] = a.pack
    db["choices"][a.id]["n"] = bump(db["packs"][a.pack])
    log(r, type="move", id=a.id, **{"from": f"{old} ({oldi})", "to": f"{a.pack} ({idx(db, a.id)})"}, why=a.why)
    commit(r, db, before, a.why, T("cause.move", id=a.id))
    print(T("move_done", a=oldi, b=idx(db, a.id)))


def cmd_merge(a):
    r = root(); lock(r); guard(r); db = load(r)
    ka, kb = resolve(db, a.keep), resolve(db, a.absorbed)
    if ka not in db["choices"] or kb not in db["choices"]:
        die("merge.expect")
    if ka == kb:
        die("merge.same")
    need(a.why, "why")
    A, B = db["choices"][ka], db["choices"][kb]
    if A["pack"] != B["pack"]:
        die("merge.diffpack")
    ia, ib = idx(db, ka), idx(db, kb)
    before = derived(db)
    old, new = A["state"], min(A["state"], B["state"])
    appended = B["doc"] != A["doc"]
    if appended:
        with open(r / A["doc"], "a", encoding="utf-8") as f:
            f.write("\n\n" + T("merge.section", title=B["title"], ix=ib, doc=B["doc"], why=a.why) + "\n")
    if a.title:
        A["title"] = need(a.title, "title")
    copied = {f: B[f] for f in FIELDS if B.get(f) and not A.get(f)}
    A.update(copied)
    A["state"] = new
    if copied or a.title:
        sync_doc(r, ka, A)
    dh = fhash(r / A["doc"]) if new == 3 else None
    del db["choices"][kb]
    log(r, type="merge", id=kb, into=ka, **{"from": ib, "to": ia}, why=a.why, title=a.title, fields=copied or None, doc_appended=appended, dochash=dh)
    commit(r, db, before, a.why, T("cause.merge", a=ia, b=ib))
    print(T("merge.done", b=ib, a=ia, title=A["title"], state=T("merge.state", a=SN(old), b=SN(new)) if new != old else "", ix=idx(db, A["pack"]), n=pack_count(db, A["pack"]), max=maxp()))


def cmd_review(a):
    r = root(); db = load(r)
    if a.pack:
        packs = [resolve(db, a.pack)]
        if packs[0] not in db["packs"]:
            die("not_pack", id=packs[0])
    else:
        act = active_iter(db)
        packs = [p for p, pk in db["packs"].items() if a.all or pk["iter"] == act]
    shown = 0
    for p in packs:
        n, cand = pack_count(db, p), candidates(db, p)
        if not (a.pack or cand or n >= warnp()):
            continue
        shown += 1
        print(T("review.pack", ix=idx(db, p), title=db["packs"][p]["title"], n=n, max=maxp()) + (T("review.full") if n >= maxp() else (T("review.near") if n >= warnp() else "")))
        if cand:
            print("\n" + T("review.table") + "\n|---|---|---|---|")
            for sc, ka, kb, why in cand:
                A, B = db["choices"][ka], db["choices"][kb]
                print(f"| {idx(db, ka)} {A['title']} | {idx(db, kb)} {B['title']} | {why} | {SN(A['state'])} / {SN(B['state'])} |")
        else:
            print(T("review.nocand"))
        print()
    if not shown:
        print(T("review.none"))


def jstate(res):
    return T("journal.altered") if res["probs"] else T("journal.unsealed")


def cmd_status(a):
    r = root(); db = load(r)
    res = check(r)
    if res["probs"] or res["unsealed"]:
        print(T("status_warn", what=jstate(res)))
    if not db["iterations"]:
        print(T("reg_empty")); return
    act = active_iter(db)
    its = db["iterations"] if a.all else ({act: db["iterations"][act]} if act else {list(db["iterations"])[-1]: list(db["iterations"].values())[-1]})
    for i, it in its.items():
        print(f"{idx(db, i)} [{SN(iter_state(db, i))}] {it['title']}" + (f"  {T('active_mark')}" if i == act else ""))
        for p, pk in db["packs"].items():
            if pk["iter"] != i:
                continue
            cs = {k: c for k, c in db["choices"].items() if c["pack"] == p}
            nv = sum(1 for c in cs.values() if c["state"] == 3)
            print(f"  {idx(db, p)} [{SN(pack_state(db, p))}] {pk['title']}  " + T("validated_count", v=nv, n=len(cs)))
            for k, c in cs.items():
                if a.all or c["state"] < 3:
                    print(f"    {idx(db, k)} [{SN(c['state'])}] {c['title']} -> {c['doc']}")
    if act is None:
        print(T("all_validated"))


def cell(c, f, w):
    v = c.get(f) or ""
    if not v:
        return T("next.missing") if c["state"] >= {"question": 0, "chosen": 2, "reason": 2, "alternatives": 3}[f] else "—"
    v = v.replace("|", "\\|")
    return v if not w or len(v) <= w else v[: w - 1].rstrip() + "…"


def step(c):
    s = c["state"]
    if s == 3:
        return "—"
    miss = missing(c, s + 1) if s + 1 >= 2 else ([] if c.get("question") else ["question"])
    return T("step.prepare", labels=", ".join(T("field.short." + f) for f in miss), step=T(f"step.l{s}")) if miss else T(f"step.c{s}")


def render_next(db, a, w, res):
    out = []
    if res["probs"] or res["unsealed"]:
        out += [T("status_warn", what=jstate(res)), ""]
    if not db["iterations"]:
        return out + [T("next.reg_empty")]
    act = active_iter(db)
    esc = lambda x: str(x).replace("|", "\\|")
    for i in (list(db["iterations"]) if a.all else [act or list(db["iterations"])[-1]]):
        cs = [c for c in db["choices"].values() if db["packs"][c["pack"]]["iter"] == i]
        nv = sum(1 for c in cs if c["state"] == 3)
        out += [T("next.iter", ix=idx(db, i), title=db["iterations"][i]["title"], state=SN(iter_state(db, i)), v=nv, n=len(cs)), ""]
        for p, pk in db["packs"].items():
            if pk["iter"] != i:
                continue
            pcs = sorted([(k, c) for k, c in db["choices"].items() if c["pack"] == p], key=lambda x: x[1]["n"])
            out += [T("next.pack", ix=idx(db, p), title=esc(pk["title"]), n=len(pcs), max=maxp(), state=SN(pack_state(db, p))), ""]
            if not pcs:
                out += [T("next.nodec"), ""]
                continue
            hd = [T("h." + h) for h in ("index", "decision", "question", "chosen", "alternatives", "reason", "state", "next")]
            out += ["| " + " | ".join(hd) + " |", "|" + "---|" * len(hd)]
            for k, c in pcs:
                out.append(f"| {idx(db, k)} | {esc(c['title'])} | {cell(c, 'question', w)} | {cell(c, 'chosen', w)} | {cell(c, 'alternatives', w)} | {cell(c, 'reason', w)} | {SN(c['state'])} | {step(c)} |")
            out.append("")
    if act is None:
        out.append(T("next.all_done"))
    else:
        todo = [c for c in db["choices"].values() if db["packs"][c["pack"]]["iter"] == act and c["state"] < 3]
        vides = [p for p, pk in db["packs"].items() if pk["iter"] == act and not pack_count(db, p)]
        near = [(p, pack_count(db, p)) for p, pk in db["packs"].items() if pk["iter"] == act and pack_count(db, p) >= warnp()]
        if near:
            out += [T("next.near", list=", ".join(f"{idx(db, p)} ({n}/{maxp()})" for p, n in near)), ""]
        inc = [idx(db, k) for k, c in db["choices"].items() if db["packs"][c["pack"]]["iter"] == act and c["state"] >= 2 and missing(c, c["state"])]
        if inc:
            out += [T("next.incomplete", list=", ".join(inc)), ""]
        out.append(T("next.remaining", n=len(todo), empty=T("next.empty_packs", n=len(vides)) if vides else "", ix=idx(db, act)))
    return out


def cmd_next(a):
    """Markdown table of decisions (4 precision fields); also writes .decisions/next.md in full."""
    r = root(); db = load(r); res = check(r)
    print("\n".join(render_next(db, a, a.width, res)))
    head = T("next.head", date=datetime.now().strftime("%Y-%m-%d %H:%M"), h=(res["head"] or "-")[:8]) + "\n\n"
    tmp = r / DIR / "next.md.tmp"
    tmp.write_text(head + "\n".join(render_next(db, a, 0, res)) + "\n", encoding="utf-8")
    os.replace(tmp, r / DIR / "next.md")


def cmd_show(a):
    r = root(); db = load(r)
    a.id = resolve(db, a.id)
    ent = db["choices"].get(a.id) or db["packs"].get(a.id) or db["iterations"].get(a.id)
    print(idx(db, a.id), json.dumps(ent, ensure_ascii=False))
    for l in read_lines(r):
        try:
            e = json.loads(l)
        except ValueError:
            continue
        if str(e.get("id", "")).rpartition(":")[2] == a.id:
            print(json.dumps({k: v for k, v in e.items() if k not in ("prev", "h", "rec")}, ensure_ascii=False))


def cmd_log(a):
    r = root(); db = load(r)
    for l in read_lines(r)[-a.n:]:
        try:
            e = json.loads(l)
        except ValueError:
            print(T("log.bad")); continue
        ch = f"{e.get('from')}->{e.get('to')}" if "to" in e else e.get("title", "")
        hh = f" #{e.get('h', '--------')[:8]}" if a.hash else ""
        print(f"{e['t'][:16]} {e['type']:8} {lab(db, e.get('id', '-')):9} {ch} | {e.get('why', '')}{hh}")


def cmd_verify(a):
    r = root(); res = check(r)
    if res["probs"]:
        print(T("v.altered", n=len(res["probs"]), m=res["n"]))
        for p in res["probs"][:15]:
            print(f"  ✗ {p}")
        if len(res["probs"]) > 15:
            print(T("v.more", n=len(res["probs"]) - 15))
    elif res["unsealed"]:
        print(T("v.unsealed", n=res["unsealed"]))
    else:
        print(T("v.ok", n=res["n"], h=(res["head"] or "")[:8]))
    for w in res["warns"][:15]:
        print(f"  ⚠ {w}")
    if not res["probs"] and not res["unsealed"] and a.head:
        print(res["head"])
    sys.exit(2 if res["probs"] or res["unsealed"] else 0)


def cmd_seal(a):
    """Migrate an unhashed journal to the chain, or rebuild the chain after an accepted alteration."""
    r = root(); lock(r); res = check(r, with_replay=False)
    need(a.why, "why")
    broken = bool(res["probs"])
    if not broken and not res["unsealed"]:
        print(T("seal.nothing")); return
    if broken and not a.rebase:
        die("seal.need_rebase")
    try:
        old_head = tail_hash(r)
    except SystemExit:
        old_head = None
    lp = r / DIR / "log.jsonl"
    backup = r / DIR / f"log.jsonl.before-seal-{datetime.now().strftime('%Y%m%dT%H%M%S')}"
    backup.write_bytes(lp.read_bytes() if lp.exists() else b"")
    out, prev = [], GENESIS
    for l in read_lines(r):
        try:
            e = json.loads(l)
            assert isinstance(e, dict)
        except (ValueError, AssertionError):
            e = {"t": datetime.now().isoformat(timespec="seconds"), "type": "corrupt", "id": "-", "raw": l[:500], "why": T("seal.corrupt")}
        e.pop("h", None)
        e["prev"] = prev
        e["h"] = chash(e)
        prev = e["h"]
        out.append(json.dumps(e, ensure_ascii=False))
    tmp = r / DIR / "log.jsonl.tmp"
    tmp.write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")
    os.replace(tmp, lp)
    kind = "rebase" if broken else "migration"
    log(r, type="seal", id="-", mode=kind, entries=res["n"], problems=res["probs"][:10] if broken else None, previous_head=old_head, backup=backup.name, why=a.why)
    save(r, load(r))
    print(T("seal.done", mode=kind, n=res["n"], b=backup.name))


def cmd_export(a):
    r = root(); db = load(r); res = check(r)
    state = T("journal.ALTERED") if res["probs"] else (T("journal.UNSEALED") if res["unsealed"] else "OK")
    out = [T("export.title") + "\n", T("export.integrity", state=state, n=res["n"], h=(res["head"] or "-")[:16]) + "\n"]
    for i, it in db["iterations"].items():
        out.append(f"## {idx(db, i)} — {it['title']} [{SN(iter_state(db, i))}]\n")
        for p, pk in db["packs"].items():
            if pk["iter"] != i:
                continue
            out.append(f"### {idx(db, p)} — {pk['title']} [{SN(pack_state(db, p))}]\n")
            for k, c in db["choices"].items():
                if c["pack"] == p:
                    out.append(f"- **{idx(db, k)}** [{SN(c['state'])}] {c['title']} — [{c['doc']}]({c['doc']})")
            out.append("")
    out.append("## " + T("export.journal") + "\n")
    for l in read_lines(r):
        try:
            e = json.loads(l)
        except ValueError:
            continue
        ch = f"{e.get('from')} → {e.get('to')}" if "to" in e else e.get("title", "")
        out.append(f"- {e['t'][:16]} `{e['type']}` {lab(db, e.get('id', '-'))} {ch} — {e.get('why', '')} `#{str(e.get('h', ''))[:8]}`")
    path = r / DIR / (a.out or "export.md")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(T("export.done", path=path))


# ---------------------------------------------------------------- adopting an existing project
KW = re.compile(r"(i choose|we choose|let'?s go with|we'?ll go with|we('ll| will) use|we('ve)? decided|decided|instead of|rather than|switch(ed)? to|drop(ped)?|go with|we keep|"
                r"je choisis|on choisit|on part sur|on garde|on retient|d[ée]cid|finalement|plut[oô]t que|on abandonne|on valide|"
                r"elegimos|vamos con|decidimos|en lugar de|wir nehmen|wir entscheiden|entschieden|statt)", re.I)
SKIP_DIRS = {".git", "node_modules", ".decisions", ".venv", "venv", "__pycache__", "dist", "build", ".claude", ".next", "target"}
TXT = {".md", ".markdown", ".txt", ".rst", ".adoc"}
BIN = {".pdf", ".docx", ".pptx", ".xlsx", ".odt"}


def dstr(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def chat_dir(r):
    base = Path.home() / ".claude" / "projects"
    for slug_ in (str(r).replace("/", "-").replace(".", "-"), str(r).replace("/", "-")):
        if (base / slug_).is_dir():
            return base / slug_
    return None


def msg_text(e):
    if e.get("type") != "user" or e.get("isMeta"):
        return None
    c = (e.get("message") or {}).get("content")
    if isinstance(c, list):
        c = " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    if not isinstance(c, str):
        return None
    c = re.sub(r"<system-reminder>.*?</system-reminder>", "", c, flags=re.S).strip()
    return None if not c or c.startswith(("<command", "<local-command", "Caveat:")) else " ".join(c.split())


def tool_answer(e):
    """User's answer to a multiple-choice question (AskUserQuestion): an explicit, precise decision."""
    c = (e.get("message") or {}).get("content")
    if e.get("type") != "user" or not isinstance(c, list):
        return None
    for b in c:
        if isinstance(b, dict) and b.get("type") == "tool_result":
            x = b.get("content")
            x = " ".join(i.get("text", "") for i in x if isinstance(i, dict)) if isinstance(x, list) else (x or "")
            if "answered your questions" in x:
                return ANSWER_TAG + " " + " ".join(x.split("answered your questions:", 1)[1].split())[:600]
    return None


def assistant_text(e):
    c = (e.get("message") or {}).get("content")
    if e.get("type") != "assistant" or not isinstance(c, list):
        return None
    return " ".join(" ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text").split()) or None


def read_chat(f):
    """User messages [(date, text, assistant's last remark just before)]."""
    out, ctx = [], ""
    for l in f.read_text(errors="ignore").splitlines():
        try:
            e = json.loads(l)
        except ValueError:
            continue
        at = assistant_text(e)
        if at:
            ctx = at[-220:]
            continue
        t = tool_answer(e) or msg_text(e)
        if t:
            out.append((str(e.get("timestamp", ""))[:10], t, ctx))
    return out


def cmd_scan(a):
    r = next((d for d in [Path.cwd(), *Path.cwd().parents] if (d / DIR / "index.json").exists()), Path.cwd())
    _ctx.update(root=r if (r / DIR / "index.json").exists() else None, cfg=None, cat=None)
    if a.session:
        cd = chat_dir(r)
        fs = [f for f in (cd.glob("*.jsonl") if cd else []) if f.stem.startswith(a.session)]
        if not fs:
            die("scan.nosession")
        for d, t, ctx in read_chat(fs[0])[: a.max]:
            if not a.grep or re.search(a.grep, t, re.I):
                print(f"{d} {t[:a.width]}" + (f"\n   {T('scan.reply', ctx=ctx)}" if ctx and a.context else ""))
        return
    print(T("scan.project", root=r))
    ctx = [p for p in r.glob("*") if p.name.lower().startswith(("claude", "readme", "agents"))]
    cd = chat_dir(r)
    if cd and (cd / "memory").is_dir():
        ctx += list((cd / "memory").glob("*.md"))
    print(T("scan.context"))
    for p in ctx:
        st = p.stat(); print(f"{p.name} | {dstr(getattr(st, 'st_birthtime', st.st_ctime))} | {dstr(st.st_mtime)}")
    docs = []
    for dp, dn, fn in os.walk(r):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            ext = os.path.splitext(f)[1].lower()
            if ext in TXT | BIN:
                p = Path(dp) / f; st = p.stat()
                title = (p.read_text(errors="ignore")[:200].strip().splitlines() or [""])[0].lstrip("# ")[:60] if ext in TXT else ""
                docs.append((getattr(st, "st_birthtime", st.st_ctime), st.st_mtime, str(p.relative_to(r)), title))
    docs.sort()
    print(T("scan.docs", n=len(docs)))
    for b, m, p, t in docs[: a.max]:
        print(f"{dstr(b)} | {dstr(m)} | {p} | {t}")
    if len(docs) > a.max:
        print(T("scan.more", n=len(docs) - a.max))
    if (r / ".git").exists():
        out = subprocess.run(["git", "-C", str(r), "log", "--date=short", "--pretty=%ad|%s"], capture_output=True, text=True).stdout.splitlines()
        if out:
            months = {}
            for l in out:
                months[l[:7]] = months.get(l[:7], 0) + 1
            print(T("scan.git", n=len(out), a=out[-1][:10], b=out[0][:10]))
            print(T("scan.permonth") + " ".join(f"{k}:{v}" for k, v in sorted(months.items())))
            for l in [l for l in out if KW.search(l)][: a.max]:
                print(l[:120])
    if cd:
        fs = sorted(cd.glob("*.jsonl"), key=lambda f: f.stat().st_mtime)
        print(T("scan.chats", n=len(fs)))
        cands = []
        for f in fs:
            m = read_chat(f)
            if not m:
                continue
            print(f"{f.stem[:8]} | {m[0][0]} | {m[-1][0]} | {len(m)} | {m[0][1][:70]}")
            cands += [(d, f.stem[:8], t, c) for d, t, c in m if KW.search(t) or t.startswith(ANSWER_TAG)]
        print(T("scan.cands", n=len(cands)))
        for d, sid, t, c in cands[: a.max]:
            m = KW.search(t); i = max(0, m.start() - 50) if m else 0
            print(f"{d} | {sid} | {t[i:i + a.width]}")
            if c:
                print(f"   {T('scan.reply', ctx=c[-a.ctxw:])}")
        if len(cands) > a.max:
            print(T("scan.more", n=len(cands) - a.max))
    else:
        print(T("scan.nochats"))


def iso(d):
    return (d or datetime.now().strftime("%Y-%m-%d")) + "T00:00:00"


def cmd_import(a):
    r = root(create=True)
    try:
        plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        die("import.unreadable", e=e)
    new_reg = not (r / DIR / "index.json").exists()
    if not a.dry_run:
        lock(r)
        if not new_reg:
            guard(r)
    db = {"iterations": {}, "packs": {}, "choices": {}} if new_reg else load(r)
    if db["iterations"] and not a.append:
        die("import.nonempty")
    old_ids, old_packs = set(db["choices"]), set(db["packs"])
    dwhy = T("import.default_why")
    events, lastt = [], {}

    def ev(floor, date, **e):
        """Event date monotone per id and never earlier than its parent's."""
        t = max(iso(date), floor, lastt.get(e["id"], ""))
        lastt[e["id"]] = t
        events.append((t, e))
        return t

    for it in plan.get("iterations", []):
        i = nid(db, "iterations", "I"); db["iterations"][i] = {"title": need(it.get("title"), "title")}
        ti = ev("", it.get("date"), type="create", id=i, title=it["title"], why=it.get("why", dwhy))
        for pk in it.get("packs", []):
            p = nid(db, "packs", "P")
            db["packs"][p] = {"title": need(pk.get("title"), "title"), "iter": i, "kind": pk.get("kind", "link"), "n": bump(db["iterations"][i])}
            tp = ev(ti, pk.get("date") or it.get("date"), type="create", id=p, title=pk["title"], iter=i, why=pk.get("why", dwhy))
            cur_p, cur_tp, ovn = p, tp, 1
            for ch in pk.get("choices", []):
                if pack_count(db, cur_p) >= maxp():  # pack full: following decisions go to an overflow pack on the same subject
                    ovn += 1
                    cur_p = nid(db, "packs", "P")
                    db["packs"][cur_p] = {"title": f"{pk['title']} ({ovn})", "iter": i, "kind": pk.get("kind", "link"), "n": bump(db["iterations"][i])}
                    cur_tp = ev(tp, pk.get("date") or it.get("date"), type="create", id=cur_p, title=db["packs"][cur_p]["title"], iter=i, why=T("import.overflow_why", title=pk["title"], n=maxp()))
                c = nid(db, "choices", "C")
                ttl = need(ch.get("title"), "title")
                docp, rel = docpath(r, ch.get("doc") or f"{cfg()['doc_dir']}/{slug(ttl)}.md")
                if not ch.get("question"):
                    die("import.q_required", title=ttl)
                flds = {f: clean_field(f, ch[f]) for f in FIELDS if ch.get(f)}
                db["choices"][c] = {"title": ttl, "pack": cur_p, "doc": rel, "state": 0, "n": bump(db["packs"][cur_p]), **{f: flds.get(f, "") for f in FIELDS}}
                tc = ev(cur_tp, ch.get("date"), type="create", id=c, title=ttl, pack=cur_p, doc=rel, why=ch.get("why", dwhy), src=ch.get("src"), **flds)
                cur = 0
                hist = ch.get("history") or [{"state": ch.get("state", "todo"), "date": ch.get("date"), "why": ch.get("why", dwhy)}]
                for h in hist:
                    new = parse_state(h["state"])
                    if new != cur:
                        if new > cur and new >= 2 and missing(db["choices"][c], new):
                            die("import.state_missing", title=ttl, state=SN(new), labels=", ".join(T("field." + f) for f in missing(db["choices"][c], new)))
                        ev(tc, h.get("date") or ch.get("date"), type="regress" if new < cur else "state", id=c, **{"from": SK[cur], "to": SK[new]},
                           why=need(h.get("why"), "why"), src=h.get("src"), dochash="PENDING" if new == 3 else None)
                        cur = new
                db["choices"][c]["state"] = cur
    for p in db["packs"]:
        if p not in old_packs and pack_count(db, p) > maxp():
            die("import.pack_over", title=db["packs"][p]["title"], n=pack_count(db, p), max=maxp())
    its = list(db["iterations"])
    bad = [k for k in its[:-1] if iter_state(db, k) < 3]
    if bad:
        die("import.not_validated", list=bad)
    for k, v in derived(db).items():
        if v:
            kind, ident = k.split(":")
            ts = max([t for t, e in events if e["id"] in db["choices"] and (db["choices"][e["id"]]["pack"] == ident or db["packs"][db["choices"][e["id"]]["pack"]]["iter"] == ident)] or [iso(None)])
            events.append((ts, dict(type="auto", id=k, **{"from": None, "to": SK[v]}, why=T("import.auto_why"))))
    events.sort(key=lambda x: x[0])
    if a.dry_run:
        print(T("import.dry"))
        a.all = True
        print_status(db, True)
        print(T("import.events", n=len(events)))
        return
    (r / DIR).mkdir(exist_ok=True)
    (r / DIR / "log.jsonl").touch()
    if new_reg:
        c0 = dict(DEFAULTS, doc_dir=detect_doc_dir(r), lang=cfg()["lang"])
        (r / DIR / "config.json").write_text(json.dumps(c0, indent=1) + "\n", encoding="utf-8")
        log(r, type="init", id="-", why=T("init.why"), config=c0)
    for k, ch in db["choices"].items():
        if k not in old_ids:
            sync_doc(r, k, ch)
    for t, e in events:
        if e.get("dochash") == "PENDING":
            e["dochash"] = fhash(r / db["choices"][e["id"]]["doc"])
        log(r, t=t, **e)
    save(r, db)
    print(T("import.done", i=len(db["iterations"]), p=len(db["packs"]), c=len(db["choices"]), n=len(events)))


def print_status(db, show_all):
    """Tree view used by dry-run (no files involved)."""
    act = active_iter(db)
    for i, it in db["iterations"].items():
        print(f"{idx(db, i)} [{SN(iter_state(db, i))}] {it['title']}" + (f"  {T('active_mark')}" if i == act else ""))
        for p, pk in db["packs"].items():
            if pk["iter"] != i:
                continue
            cs = {k: c for k, c in db["choices"].items() if c["pack"] == p}
            print(f"  {idx(db, p)} [{SN(pack_state(db, p))}] {pk['title']}  " + T("validated_count", v=sum(1 for c in cs.values() if c["state"] == 3), n=len(cs)))
            for k, c in cs.items():
                print(f"    {idx(db, k)} [{SN(c['state'])}] {c['title']} -> {c['doc']}")


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(prog="dec.py", description="Decision registry (see decisions.md)")
    ap.add_argument("--version", action="version", version=f"decisions {VERSION} (format {FORMAT})")
    sp = ap.add_subparsers(dest="cmd", required=True, metavar="command")

    def add(name, fn, help, *args, why=False, why_required=False, force=False):
        s = sp.add_parser(name, help=help, description=help); s.set_defaults(fn=fn)
        for x in args:
            s.add_argument(x[0], **x[1])
        if why or why_required:
            s.add_argument("--why", required=why_required, help="justification (journaled)")
        if force:
            s.add_argument("--force", action="store_true", help="override a safeguard (justify it)")
        return s

    F = lambda h: {"help": h}
    add("init", cmd_init, "create the registry here (--lang = user's language code)", ("--lang", F("ISO language code of the user, e.g. en, fr, es")), ("--doc-dir", F("default folder for decision documents")), ("--max-pack", {"type": int, "help": "max decisions per pack (default 6)"}))
    add("config", cmd_config, "show or set config (lang, max_pack, min_field, doc_dir)", ("key", {"nargs": "?"}), ("value", {"nargs": "?"}), why=True)
    add("iter-new", cmd_iter_new, "open a new iteration (previous must be Validated)", ("title", {}), why=True, force=True)
    add("pack-new", cmd_pack_new, "create a pack in the active iteration", ("title", {}), ("--iter", {}), ("--kind", {"choices": ["link", "time"], "default": "link", "help": "link = same subject, time = same period"}), why=True, force=True)
    add("pack-rm", cmd_pack_rm, "delete an empty pack", ("pack", {}), why_required=True)
    add("add", cmd_add, "add a decision (document created or block appended)", ("title", {}), ("--pack", {"required": True}), ("--doc", F("path relative to project; default <doc_dir>/<slug>.md")),
        ("--question", {"required": True, "help": "the precise question this decision settles"}), ("--chosen", F("chosen option")), ("--alternatives", F("rejected alternatives (or 'none')")), ("--reason", F("why this option")),
        ("--no-overflow", {"action": "store_true", "help": "refuse instead of using an overflow pack when the pack is full"}), why=True, force=True)
    add("detail", cmd_detail, "set/correct the 4 fields of a decision", ("id", {}), ("--question", {}), ("--chosen", {}), ("--alternatives", {}), ("--reason", {}), why_required=True)
    add("set", cmd_set, "change a decision's state (todo|doing|done|validated); Done/Validated require detail", ("id", {}), ("state", {}), ("--question", {}), ("--chosen", {}), ("--alternatives", {}), ("--reason", {}), why_required=True, force=True)
    add("move", cmd_move, "move a decision to another pack", ("id", {}), ("pack", {}), why_required=True, force=True)
    add("merge", cmd_merge, "merge two decisions of one pack (first kept, second absorbed)", ("keep", {}), ("absorbed", {}), ("--title", F("new title for the kept decision")), why_required=True)
    add("review", cmd_review, "find mergeable decisions (full or near-full packs)", ("pack", {"nargs": "?"}), ("--all", {"action": "store_true"}))
    add("status", cmd_status, "tree view of the active iteration", ("--all", {"action": "store_true"}))
    add("next", cmd_next, "Markdown table of decisions + next steps (also writes .decisions/next.md)", ("--all", F("all iterations") | {"action": "store_true"}), ("--width", {"type": int, "default": 70, "help": "max cell width on screen (0 = full)"}))
    add("show", cmd_show, "one element's record and full history", ("id", {}))
    add("log", cmd_log, "recent journal events", ("-n", {"type": int, "default": 10}), ("--hash", {"action": "store_true"}))
    add("verify", cmd_verify, "check journal integrity (exit 2 if altered/unsealed)", ("--head", {"action": "store_true", "help": "also print the full head hash"}))
    add("seal", cmd_seal, "chain a legacy journal, or --rebase after an accepted alteration", ("--rebase", {"action": "store_true"}), why_required=True)
    add("export", cmd_export, "readable recap in .decisions/export.md", ("--out", {}))
    add("scan", cmd_scan, "inventory of an existing project (docs, git, chats) before adoption", ("--max", {"type": int, "default": 40}), ("--width", {"type": int, "default": 200}), ("--session", {}), ("--grep", {}),
        ("--ctxw", {"type": int, "default": 160, "help": "context length (assistant's preceding remark)"}), ("--context", {"action": "store_true", "help": "with --session: show the preceding remark"}))
    add("import", cmd_import, "import a retroactive plan (JSON); always --dry-run first", ("plan", {}), ("--dry-run", {"action": "store_true"}), ("--append", {"action": "store_true"}))
    a = ap.parse_args()
    if a.cmd not in ("init", "import", "scan"):
        root()
    a.fn(a)


if __name__ == "__main__":
    main()
