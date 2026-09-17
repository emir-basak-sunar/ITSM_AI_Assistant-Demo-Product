# TODO — ITSM Asistanı

## Done
- [x] ITSM chatbot prototype (classify, suggest, fill, ticket)
- [x] 4-level taxonomy: Talep → Birim → Modül → Süreç
- [x] Schema-based dynamic slot filling (`schemas.json`)
- [x] Priority inference (Kritik/Yüksek/Orta/Düşük)
- [x] Local JSONL auth (`auth.py`)
- [x] FastAPI backend + React/TypeScript UI
- [x] Report command queue + daily_jobs.py
- [x] Expected-action dialogues (13/13)

## Later
- [ ] Real ITSM API (ServiceNow / Jira)
- [ ] Mail/Teams delivery of JOB output
- [ ] Hand-labeled gold subset for the taxonomy
- [ ] JWT/session persistence across API restarts

## Won’t do (unless PRD changes)
- Marketplace iade/kargo bot
- CFPB English finance
- Scraping third-party sites
