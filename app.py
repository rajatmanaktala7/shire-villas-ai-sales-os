import os
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shire_ai_os.db")

# Railway/Postgres compatibility:
# Force SQLAlchemy to use psycopg v3 rather than falling back to psycopg2.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    company = Column(String(200), nullable=True)
    designation = Column(String(200), nullable=True)
    source = Column(String(100), default="manual")
    status = Column(String(50), default="New")
    score = Column(Float, default=0)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Shire Villas AI Sales OS", version="2.0.0")

class LeadCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    designation: Optional[str] = None
    source: str = "manual"
    notes: str = ""

class LeadUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    score: Optional[float] = None

class DraftRequest(BaseModel):
    channel: str = "email"
    objective: str = "Introduce Shire Villas and request a meeting"

STATUSES = ["New", "Researching", "Qualified", "Message Ready", "Contacted", "Replied", "Meeting Booked", "Follow-up", "Not Interested", "Converted"]

def lead_to_dict(x):
    return {
        "id": x.id, "name": x.name, "email": x.email, "phone": x.phone,
        "company": x.company, "designation": x.designation, "source": x.source,
        "status": x.status, "score": x.score, "notes": x.notes,
        "created_at": x.created_at.isoformat() if x.created_at else None,
    }

@app.get("/health")
def health():
    return {"status": "ok", "service": "shire-villas-ai-sales-os", "version": "2.0.0"}

@app.get("/api/dashboard")
def dashboard_metrics():
    db = SessionLocal()
    try:
        leads = db.query(Lead).all()
        total = len(leads)
        qualified = sum(1 for x in leads if (x.score or 0) >= 65)
        meetings = sum(1 for x in leads if x.status == "Meeting Booked")
        converted = sum(1 for x in leads if x.status == "Converted")
        avg_score = round(sum((x.score or 0) for x in leads) / total, 1) if total else 0
        pipeline = {s: 0 for s in STATUSES}
        sources = {}
        for x in leads:
            pipeline[x.status if x.status in pipeline else "New"] += 1
            src = x.source or "manual"
            sources[src] = sources.get(src, 0) + 1
        return {
            "total_leads": total,
            "qualified_leads": qualified,
            "meetings": meetings,
            "converted": converted,
            "average_score": avg_score,
            "pipeline": pipeline,
            "sources": sources,
        }
    finally:
        db.close()

@app.get("/api/leads")
def list_leads():
    db = SessionLocal()
    try:
        return [lead_to_dict(x) for x in db.query(Lead).order_by(Lead.id.desc()).all()]
    finally:
        db.close()

@app.post("/api/leads")
def create_lead(payload: LeadCreate):
    db = SessionLocal()
    try:
        lead = Lead(**payload.model_dump())
        db.add(lead)
        db.commit()
        db.refresh(lead)
        return lead_to_dict(lead)
    finally:
        db.close()

@app.patch("/api/leads/{lead_id}")
def update_lead(lead_id: int, payload: LeadUpdate):
    db = SessionLocal()
    try:
        lead = db.get(Lead, lead_id)
        if not lead:
            raise HTTPException(404, "Lead not found")
        for k, v in payload.model_dump(exclude_none=True).items():
            setattr(lead, k, v)
        db.commit()
        db.refresh(lead)
        return lead_to_dict(lead)
    finally:
        db.close()

@app.post("/api/leads/{lead_id}/score")
def score_lead(lead_id: int):
    db = SessionLocal()
    try:
        lead = db.get(Lead, lead_id)
        if not lead:
            raise HTTPException(404, "Lead not found")
        score = 20
        score += 20 if lead.email else 0
        score += 15 if lead.phone else 0
        score += 15 if lead.company else 0
        score += 10 if lead.designation else 0
        score += 10 if lead.notes and len(lead.notes) > 30 else 0
        score += 10 if lead.source and lead.source.lower() not in ("manual", "") else 0
        lead.score = min(score, 100)
        lead.status = "Qualified" if lead.score >= 65 else "Researching"
        db.commit()
        db.refresh(lead)
        return {
            "status": "READY_FOR_REVIEW",
            "lead": lead_to_dict(lead),
            "explanation": "Starter rule-based score. AI scoring can be connected in the next phase."
        }
    finally:
        db.close()

@app.post("/api/leads/{lead_id}/draft")
def generate_draft(lead_id: int, payload: DraftRequest):
    db = SessionLocal()
    try:
        lead = db.get(Lead, lead_id)
        if not lead:
            raise HTTPException(404, "Lead not found")
        first = lead.name.split()[0]
        company_line = f" at {lead.company}" if lead.company else ""
        if payload.channel.lower() == "whatsapp":
            draft = (
                f"Hello {first}, I’m reaching out from Shire Villas, Siolim, Goa. "
                f"We are presenting a limited collection of luxury villas. "
                f"I thought this may be relevant to you{company_line}. "
                "May I share a concise investment brief and arrange a short call?"
            )
        else:
            draft = (
                f"Dear {first},\n\nI’m reaching out from Shire Villas in Siolim, Goa. "
                "We are presenting a limited collection of luxury villas designed for discerning buyers and investors. "
                f"Based on your profile{company_line}, I thought the opportunity may be relevant.\n\n"
                "May I share the investment brief and arrange a short introductory call?\n\nRegards,\nShire Villas Team"
            )
        return {
            "status": "READY_FOR_REVIEW", "channel": payload.channel,
            "objective": payload.objective, "draft": draft,
            "notice": "Nothing has been sent automatically."
        }
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTML_PAGE

HTML_PAGE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Shire Villas AI Sales OS</title>
<style>
:root{--nav:#132238;--ink:#1a2635;--muted:#718096;--bg:#f5f7fb;--card:#fff;--line:#e7ebf0;--accent:#af7d37;--green:#1d8a62;--red:#c74b50;--blue:#2e67c8;--orange:#c47a20}
*{box-sizing:border-box}body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Arial;background:var(--bg);color:var(--ink)}
.shell{display:grid;grid-template-columns:245px 1fr;min-height:100vh}.side{background:var(--nav);color:#fff;padding:28px 18px;position:sticky;top:0;height:100vh}.brand{padding:0 10px 26px;border-bottom:1px solid #ffffff20}.brand h1{font-size:19px;letter-spacing:1px;margin:0}.brand small{color:#aeb9c9}.nav{margin-top:24px}.nav a{display:flex;gap:11px;align-items:center;color:#cbd5e1;text-decoration:none;padding:12px 14px;border-radius:9px;margin:6px 0;font-size:14px}.nav a.active,.nav a:hover{background:#ffffff12;color:#fff}.dot{width:8px;height:8px;border-radius:50%;background:#7d8da4}.nav a.active .dot{background:#d3a45e}.side-foot{position:absolute;bottom:24px;left:28px;color:#92a0b4;font-size:12px}
.main{min-width:0}.topbar{height:74px;background:#fff;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;padding:0 32px;position:sticky;top:0;z-index:5}.topbar h2{font-size:18px;margin:0}.online{font-size:12px;padding:7px 11px;border-radius:999px;background:#e7f7f1;color:#187454;font-weight:700}.content{padding:28px 32px;max-width:1500px;margin:auto}.hero{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:22px}.hero h3{margin:0 0 5px;font-size:26px}.hero p{margin:0;color:var(--muted);font-size:14px}.primary{background:var(--accent);color:#fff;border:0;border-radius:9px;padding:11px 16px;font-weight:700;cursor:pointer}.cards{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;margin-bottom:18px}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;box-shadow:0 4px 14px #15223808}.metric .label{color:var(--muted);font-size:12px;font-weight:650}.metric .value{font-size:28px;font-weight:800;margin:7px 0 3px}.metric .sub{font-size:11px;color:#93a0ae}.grid2{display:grid;grid-template-columns:1.25fr .75fr;gap:16px;margin-bottom:18px}.section-title{font-size:15px;font-weight:800;margin:0 0 15px}.pipeline{display:grid;grid-template-columns:repeat(5,1fr);gap:8px}.stage{background:#f8fafc;border:1px solid var(--line);border-radius:10px;padding:12px}.stage b{font-size:21px}.stage span{display:block;color:var(--muted);font-size:11px;margin-top:3px}.source-row{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #eef1f4;font-size:13px}.source-row:last-child{border:0}.toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:14px}.toolbar input,.toolbar select{border:1px solid #d9e0e7;background:#fff;padding:10px 11px;border-radius:8px;font:inherit}.toolbar input{min-width:260px;flex:1}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:12px}table{border-collapse:collapse;width:100%;min-width:900px;background:#fff}th{background:#f8fafc;color:#738093;text-transform:uppercase;font-size:10px;letter-spacing:.5px}th,td{padding:12px 14px;border-bottom:1px solid #edf0f3;text-align:left}td{font-size:13px}.leadname{font-weight:750}.small{font-size:11px;color:var(--muted);margin-top:2px}.badge{display:inline-block;padding:5px 8px;border-radius:999px;background:#eef3f8;font-size:10px;font-weight:800}.score{font-weight:800}.hot{color:var(--green)}.mid{color:var(--orange)}.low{color:#7c8794}.actions{display:flex;gap:5px;flex-wrap:wrap}.btn{border:1px solid #dbe2e9;background:#fff;border-radius:7px;padding:7px 9px;font-size:11px;cursor:pointer;color:#334155}.btn:hover{background:#f6f8fb}.review{border-left:4px solid var(--accent)}pre{white-space:pre-wrap;margin:0;background:#f8fafc;border-radius:10px;padding:14px;min-height:92px;font:12px/1.55 ui-monospace,SFMono-Regular,Consolas;color:#334155}.modal{display:none;position:fixed;inset:0;background:#0b1726aa;z-index:20;align-items:center;justify-content:center;padding:16px}.modal.show{display:flex}.modal-box{background:#fff;border-radius:15px;padding:23px;width:min(720px,100%);max-height:90vh;overflow:auto}.modal-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:17px}.modal-head h3{margin:0}.x{border:0;background:transparent;font-size:24px;cursor:pointer}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:11px}.form-grid input,.form-grid select,.form-grid textarea{width:100%;padding:11px;border:1px solid #d8dfe7;border-radius:8px;font:inherit}.span2{grid-column:1/-1}.modal-foot{display:flex;justify-content:flex-end;gap:8px;margin-top:15px}.secondary{background:#eef2f6;border:0;border-radius:8px;padding:10px 14px;cursor:pointer}.empty{padding:28px;text-align:center;color:var(--muted)}
@media(max-width:1100px){.cards{grid-template-columns:repeat(3,1fr)}.grid2{grid-template-columns:1fr}.pipeline{grid-template-columns:repeat(3,1fr)}}
@media(max-width:760px){.shell{grid-template-columns:1fr}.side{display:none}.content{padding:20px 14px}.topbar{padding:0 16px}.cards{grid-template-columns:1fr 1fr}.pipeline{grid-template-columns:1fr 1fr}.hero{align-items:flex-start;gap:14px}.form-grid{grid-template-columns:1fr}.span2{grid-column:auto}}
</style>
</head>
<body>
<div class="shell">
  <aside class="side">
    <div class="brand"><h1>SHIRE VILLAS</h1><small>AI Sales Operating System</small></div>
    <nav class="nav">
      <a class="active" href="#dashboard"><span class="dot"></span>Dashboard</a>
      <a href="#leads"><span class="dot"></span>Lead Pipeline</a>
      <a href="#ai-review"><span class="dot"></span>AI Review Queue</a>
      <a href="/docs" target="_blank"><span class="dot"></span>API Docs</a>
    </nav>
    <div class="side-foot">Approval-based sales automation<br>Version 2.0</div>
  </aside>
  <main class="main">
    <header class="topbar"><h2>Sales Command Centre</h2><div class="online">● SYSTEM ONLINE</div></header>
    <div class="content">
      <section class="hero" id="dashboard"><div><h3>Shire Villas Sales Dashboard</h3><p>Lead intelligence, pipeline visibility and approval-based outreach in one place.</p></div><button class="primary" onclick="openModal()">+ Add Lead</button></section>
      <section class="cards">
        <div class="card metric"><div class="label">TOTAL LEADS</div><div class="value" id="mTotal">0</div><div class="sub">All captured opportunities</div></div>
        <div class="card metric"><div class="label">QUALIFIED</div><div class="value" id="mQualified">0</div><div class="sub">Score 65 or above</div></div>
        <div class="card metric"><div class="label">MEETINGS</div><div class="value" id="mMeetings">0</div><div class="sub">Meetings booked</div></div>
        <div class="card metric"><div class="label">CONVERTED</div><div class="value" id="mConverted">0</div><div class="sub">Closed opportunities</div></div>
        <div class="card metric"><div class="label">AVG. LEAD SCORE</div><div class="value" id="mScore">0</div><div class="sub">Current database average</div></div>
      </section>
      <section class="grid2">
        <div class="card"><h4 class="section-title">Pipeline Snapshot</h4><div class="pipeline" id="pipeline"></div></div>
        <div class="card"><h4 class="section-title">Lead Sources</h4><div id="sources"><div class="empty">No source data yet</div></div></div>
      </section>
      <section class="card" id="leads"><h4 class="section-title">Lead Pipeline</h4>
        <div class="toolbar"><input id="search" placeholder="Search name, company, email or phone..." oninput="renderLeads()"><select id="statusFilter" onchange="renderLeads()"><option value="">All statuses</option></select><select id="sourceFilter" onchange="renderLeads()"><option value="">All sources</option></select></div>
        <div class="table-wrap"><table><thead><tr><th>Lead</th><th>Company</th><th>Source</th><th>Status</th><th>Score</th><th>Created</th><th>Actions</th></tr></thead><tbody id="rows"></tbody></table></div>
      </section>
      <section class="card review" id="ai-review"><h4 class="section-title">AI Output · Human Review Required</h4><pre id="output">Select “Score”, “Email” or “WhatsApp” beside a lead. Nothing is sent automatically.</pre></section>
    </div>
  </main>
</div>
<div class="modal" id="modal"><div class="modal-box"><div class="modal-head"><h3>Add New Lead</h3><button class="x" onclick="closeModal()">×</button></div><div class="form-grid">
<input id="name" placeholder="Name *"><input id="email" placeholder="Email"><input id="phone" placeholder="Phone"><input id="company" placeholder="Company"><input id="designation" placeholder="Designation"><select id="source"><option>manual</option><option>Apollo</option><option>LinkedIn</option><option>Website</option><option>Referral</option><option>Meta Ads</option><option>Broker</option><option>Other</option></select><textarea id="notes" class="span2" rows="4" placeholder="Notes, investment interest, context..."></textarea></div><div class="modal-foot"><button class="secondary" onclick="closeModal()">Cancel</button><button class="primary" onclick="addLead()">Save Lead</button></div></div></div>
<script>
const STATUSES=['New','Researching','Qualified','Message Ready','Contacted','Replied','Meeting Booked','Follow-up','Not Interested','Converted'];
let allLeads=[];
function esc(v){return String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function openModal(){document.getElementById('modal').classList.add('show')}
function closeModal(){document.getElementById('modal').classList.remove('show')}
async function refresh(){await Promise.all([loadMetrics(),loadLeads()])}
async function loadMetrics(){const r=await fetch('/api/dashboard');const d=await r.json();mTotal.textContent=d.total_leads;mQualified.textContent=d.qualified_leads;mMeetings.textContent=d.meetings;mConverted.textContent=d.converted;mScore.textContent=d.average_score;pipeline.innerHTML=Object.entries(d.pipeline).map(([k,v])=>`<div class="stage"><b>${v}</b><span>${esc(k)}</span></div>`).join('');const src=Object.entries(d.sources).sort((a,b)=>b[1]-a[1]);sources.innerHTML=src.length?src.map(([k,v])=>`<div class="source-row"><span>${esc(k)}</span><b>${v}</b></div>`).join(''):'<div class="empty">No source data yet</div>'}
async function loadLeads(){const r=await fetch('/api/leads');allLeads=await r.json();const current=statusFilter.value;statusFilter.innerHTML='<option value="">All statuses</option>'+STATUSES.map(s=>`<option>${s}</option>`).join('');statusFilter.value=current;const sources=[...new Set(allLeads.map(x=>x.source||'manual'))].sort();const currSrc=sourceFilter.value;sourceFilter.innerHTML='<option value="">All sources</option>'+sources.map(s=>`<option>${esc(s)}</option>`).join('');sourceFilter.value=currSrc;renderLeads()}
function renderLeads(){const q=search.value.trim().toLowerCase(),st=statusFilter.value,src=sourceFilter.value;const arr=allLeads.filter(x=>(!st||x.status===st)&&(!src||(x.source||'manual')===src)&&(!q||[x.name,x.company,x.email,x.phone].some(v=>(v||'').toLowerCase().includes(q))));rows.innerHTML=arr.length?arr.map(x=>{const sc=Number(x.score||0),cls=sc>=65?'hot':sc>=40?'mid':'low';return `<tr><td><div class="leadname">${esc(x.name)}</div><div class="small">${esc(x.designation||'')} ${x.email?'· '+esc(x.email):''}</div></td><td>${esc(x.company||'-')}</td><td>${esc(x.source||'manual')}</td><td><select class="btn" onchange="setStatus(${x.id},this.value)">${STATUSES.map(s=>`<option ${s===x.status?'selected':''}>${s}</option>`).join('')}</select></td><td class="score ${cls}">${sc}</td><td>${x.created_at?new Date(x.created_at).toLocaleDateString():'-'}</td><td><div class="actions"><button class="btn" onclick="score(${x.id})">Score</button><button class="btn" onclick="draft(${x.id},'email')">Email</button><button class="btn" onclick="draft(${x.id},'whatsapp')">WhatsApp</button></div></td></tr>`}).join(''):'<tr><td colspan="7" class="empty">No leads match the current filters.</td></tr>'}
async function addLead(){if(!name.value.trim()){alert('Name is required');return}const body={name:name.value.trim(),email:email.value||null,phone:phone.value||null,company:company.value||null,designation:designation.value||null,source:source.value||'manual',notes:notes.value||''};const r=await fetch('/api/leads',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!r.ok){alert('Unable to save lead');return}[name,email,phone,company,designation,notes].forEach(el=>el.value='');closeModal();await refresh()}
async function setStatus(id,status){await fetch(`/api/leads/${id}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status})});await refresh()}
async function score(id){const r=await fetch(`/api/leads/${id}/score`,{method:'POST'});const x=await r.json();output.textContent=`STATUS: ${x.status}\n\nLead: ${x.lead.name}\nScore: ${x.lead.score}\nPipeline: ${x.lead.status}\n\n${x.explanation}`;document.getElementById('ai-review').scrollIntoView({behavior:'smooth'});await refresh()}
async function draft(id,ch){const r=await fetch(`/api/leads/${id}/draft`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({channel:ch})});const x=await r.json();output.textContent=`STATUS: ${x.status}\nCHANNEL: ${String(x.channel).toUpperCase()}\n\n${x.draft}\n\n${x.notice}`;document.getElementById('ai-review').scrollIntoView({behavior:'smooth'})}
refresh();
</script></body></html>'''
