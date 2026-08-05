
import os
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shire_ai_os.db")
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
app = FastAPI(title="Shire Villas AI Sales OS - Simple MVP", version="1.0.0")

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


def lead_to_dict(x):
    return {"id":x.id,"name":x.name,"email":x.email,"phone":x.phone,"company":x.company,
            "designation":x.designation,"source":x.source,"status":x.status,"score":x.score,
            "notes":x.notes,"created_at":x.created_at.isoformat()}

@app.get("/health")
def health():
    return {"status":"ok","service":"shire-villas-ai-os-simple"}

@app.get("/api/leads")
def list_leads():
    db=SessionLocal()
    try: return [lead_to_dict(x) for x in db.query(Lead).order_by(Lead.id.desc()).all()]
    finally: db.close()

@app.post("/api/leads")
def create_lead(payload: LeadCreate):
    db=SessionLocal()
    try:
        lead=Lead(**payload.model_dump())
        db.add(lead); db.commit(); db.refresh(lead)
        return lead_to_dict(lead)
    finally: db.close()

@app.patch("/api/leads/{lead_id}")
def update_lead(lead_id:int,payload:LeadUpdate):
    db=SessionLocal()
    try:
        lead=db.get(Lead,lead_id)
        if not lead: raise HTTPException(404,"Lead not found")
        for k,v in payload.model_dump(exclude_none=True).items(): setattr(lead,k,v)
        db.commit(); db.refresh(lead); return lead_to_dict(lead)
    finally: db.close()

@app.post("/api/leads/{lead_id}/score")
def score_lead(lead_id:int):
    db=SessionLocal()
    try:
        lead=db.get(Lead,lead_id)
        if not lead: raise HTTPException(404,"Lead not found")
        score=20
        score += 20 if lead.email else 0
        score += 15 if lead.phone else 0
        score += 15 if lead.company else 0
        score += 10 if lead.designation else 0
        score += 10 if lead.notes and len(lead.notes)>30 else 0
        score += 10 if lead.source.lower() not in ("manual","") else 0
        lead.score=min(score,100)
        lead.status = "Qualified" if lead.score >= 65 else "Researching"
        db.commit(); db.refresh(lead)
        return {"status":"READY_FOR_REVIEW","lead":lead_to_dict(lead),"explanation":"Rule-based starter score. Replace with your approved AI scoring prompt later."}
    finally: db.close()

@app.post("/api/leads/{lead_id}/draft")
def generate_draft(lead_id:int,payload:DraftRequest):
    db=SessionLocal()
    try:
        lead=db.get(Lead,lead_id)
        if not lead: raise HTTPException(404,"Lead not found")
        first=lead.name.split()[0]
        company_line=f" at {lead.company}" if lead.company else ""
        if payload.channel.lower()=="whatsapp":
            draft=f"Hello {first}, I’m reaching out from Shire Villas, Siolim, Goa. We are presenting a limited collection of luxury villas. I thought this may be relevant to you{company_line}. May I share a concise investment brief and arrange a short call?"
        else:
            draft=f"Dear {first},\n\nI’m reaching out from Shire Villas in Siolim, Goa. We are presenting a limited collection of luxury villas designed for discerning buyers and investors. Based on your profile{company_line}, I thought the opportunity may be relevant.\n\nMay I share the investment brief and arrange a short introductory call?\n\nRegards,\nShire Villas Team"
        return {"status":"READY_FOR_REVIEW","channel":payload.channel,"objective":payload.objective,"draft":draft,"notice":"Nothing has been sent automatically."}
    finally: db.close()

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTML_PAGE

HTML_PAGE = r'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Shire Villas AI OS</title>
<style>body{font-family:Arial;margin:0;background:#f4f6f8;color:#17202a}.top{background:#152238;color:white;padding:20px 6%}.wrap{max-width:1100px;margin:25px auto;padding:0 16px}.card{background:white;border-radius:12px;padding:20px;margin-bottom:18px;box-shadow:0 2px 10px #0001}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}input,select,textarea,button{padding:10px;border:1px solid #ccd3da;border-radius:7px;width:100%;box-sizing:border-box}button{background:#1769aa;color:white;border:0;cursor:pointer}.actions button{width:auto;margin:2px}.badge{padding:4px 8px;border-radius:12px;background:#e8f1fa;font-size:12px}table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid #eee;text-align:left;font-size:14px}pre{white-space:pre-wrap;background:#f7f7f7;padding:12px;border-radius:8px}</style></head>
<body><div class="top"><h2>SHIRE VILLAS · AI Sales OS</h2><div>Simple approval-based MVP</div></div><div class="wrap">
<div class="card"><h3>Add Lead</h3><div class="grid"><input id="name" placeholder="Name *"><input id="email" placeholder="Email"><input id="phone" placeholder="Phone"><input id="company" placeholder="Company"><input id="designation" placeholder="Designation"><input id="source" placeholder="Source" value="manual"></div><textarea id="notes" placeholder="Notes" style="margin-top:12px"></textarea><button onclick="addLead()" style="margin-top:12px">Add Lead</button></div>
<div class="card"><h3>Lead Pipeline</h3><div style="overflow:auto"><table><thead><tr><th>Lead</th><th>Company</th><th>Status</th><th>Score</th><th>Actions</th></tr></thead><tbody id="rows"></tbody></table></div></div>
<div class="card"><h3>AI Output · Ready for Review</h3><pre id="output">Select Score or Draft beside a lead.</pre></div></div>
<script>
async function load(){let r=await fetch('/api/leads');let a=await r.json();rows.innerHTML=a.map(x=>`<tr><td><b>${x.name}</b><br><small>${x.email||''} ${x.phone||''}</small></td><td>${x.company||'-'}</td><td><span class="badge">${x.status}</span></td><td>${x.score}</td><td class="actions"><button onclick="score(${x.id})">Score</button><button onclick="draft(${x.id},'email')">Email Draft</button><button onclick="draft(${x.id},'whatsapp')">WhatsApp</button></td></tr>`).join('')}
async function addLead(){if(!name.value.trim()){alert('Name is required');return}await fetch('/api/leads',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name.value,email:email.value||null,phone:phone.value||null,company:company.value||null,designation:designation.value||null,source:source.value||'manual',notes:notes.value})});name.value=email.value=phone.value=company.value=designation.value=notes.value='';load()}
async function score(id){let r=await fetch(`/api/leads/${id}/score`,{method:'POST'});output.textContent=JSON.stringify(await r.json(),null,2);load()}
async function draft(id,ch){let r=await fetch(`/api/leads/${id}/draft`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({channel:ch})});let x=await r.json();output.textContent=x.draft+'\n\nStatus: '+x.status+'\n'+x.notice}
load()</script></body></html>'''
