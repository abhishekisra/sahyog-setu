"""2026-11-08 (user: "2 karo"): read an age limit out of a scheme's eligibility text.
Only clear age wording counts (between X and Y years / X years or above /
upper age limit X ...); experience/residence/period years are ignored. Used
ONLY to make suggestions -- an admin approves each one (age_review_views).
Checked 2026-11-08: agrees with 202 of 214 schemes that already had ages."""
import re,html
BAD=re.compile(r'experience|resident|residing|domicile|period|within|membership|service|marri(ed|age) for|since|last \d|continuous|old age home|lease|loan|tenure|repay|registered for|working for|employed for|stay',re.I)
N=r'(\d{1,3})'
Y=r'\s*(?:years?|yrs?\.?)'
PATS=[  # (regex, kind) kind: range/min/max
 (re.compile(r'(?:age|aged)[^.;]{0,40}?between\s+'+N+r'\s*(?:and|to|-|–)\s*'+N+Y,re.I),'range'),
 (re.compile(r'between\s+(?:the\s+)?(?:age|ages)\s+(?:of\s+)?'+N+r'\s*(?:and|to|-|–)\s*'+N+r'(?:'+Y+r')?',re.I),'range'),
 (re.compile(r'between\s+'+N+r'\s*(?:and|to|-|–)\s*'+N+Y+r'\s*(?:of\s+age|old)?',re.I),'range'),
 (re.compile(r'(?:age|aged)[^.;]{0,30}?'+N+r'\s*(?:to|-|–)\s*'+N+Y,re.I),'range'),
 (re.compile(r'(?:age|aged)[^.;]{0,40}?(?:above|over|more than|at least|minimum(?: of)?|not less than)\s+'+N+Y,re.I),'min'),
 (re.compile(r'(?:aged?|age (?:should|must) be|of age)[^.;]{0,20}?'+N+Y+r'\s*(?:or|and)\s*(?:above|more|older)',re.I),'min'),
 (re.compile(r'\b'+N+Y+r'\s*(?:of age\s*)?(?:or|and)\s*(?:above|more|older)\b[^.;]{0,10}(?:in age|of age)?',re.I),'min_weak'),
 (re.compile(r'minimum age[^.;]{0,20}?'+N,re.I),'min'),
 (re.compile(r'(?:upper age limit|maximum age|age limit)[^.;]{0,30}?'+N,re.I),'max'),
 (re.compile(r'(?:age|aged)[^.;]{0,40}?(?:below|under|less than|not more than|not exceed(?:ing)?|up ?to)\s+'+N+Y,re.I),'max'),
]
def clean(t): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',t or '')))
def extract(text):
    t=clean(text); mins=[];maxs=[];quotes=[]
    for rx,kind in PATS:
        for m in rx.finditer(t):
            ctx=t[max(0,m.start()-60):m.end()+30]
            if BAD.search(ctx): continue
            nums=[int(x) for x in m.groups() if x]
            if any(n>100 for n in nums): continue
            if kind=='range':
                a,b=nums[0],nums[1]
                if a>=b or a<0: continue
                mins.append(a);maxs.append(b)
            elif kind.startswith('min'):
                if kind=='min_weak' and not re.search(r'\bage|aged|old\b',ctx,re.I): continue
                mins.append(nums[0])
            else: maxs.append(nums[0])
            quotes.append(t[max(0,m.start()-40):m.end()+20].strip())
    if not mins and not maxs: return None
    mn=min(mins) if mins else 0; mx=max(maxs) if maxs else 100
    if len(set(mins))>1 or len(set(maxs))>1: conf='check'   # several different ages mentioned (e.g. child + parent)
    else: conf='good'
    if mn>=mx: return None
    return {'min':mn,'max':mx,'quote':quotes[0][:220],'confidence':conf,'n':len(quotes)}
