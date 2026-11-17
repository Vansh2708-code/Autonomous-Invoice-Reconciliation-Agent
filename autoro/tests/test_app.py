"""Functional smoke tests using a disposable database, never production records."""
import os
import tempfile
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ['AUTORO_DATA_DIR'] = tempfile.mkdtemp(prefix='autoro-test-')
os.environ['APP_SECRET_KEY'] = 'test-only-fixed-secret-not-for-deployment'
os.environ.pop('GEMINI_API_KEY', None)

from fastapi.testclient import TestClient
from main import app


def login_user(client, email):
    response = client.post('/api/auth/signup', json={'name':'Demo Analyst','email':email,'password':'local-test-password'})
    assert response.status_code == 200, response.text
    return {'X-CSRF-Token': response.json()['csrf']}


def test_manual_reconcile_and_access_controls():
    with TestClient(app) as client:
        headers = login_user(client,'alice@local.test')
        data = dict(vendor='Alpha Supplies',issue_date='2026-10-15',currency='INR',template_label='Standard',
                    line_items=[dict(sku='ABC',description='Paper packs',quantity=10,unit_price=100,tax_rate=18)])
        po = client.post('/api/documents/manual',headers=headers,json={**data,'doc_type':'po','number':'PO-001'}).json()['document']
        inv = client.post('/api/documents/manual',headers=headers,json={**data,'doc_type':'invoice','number':'INV-001','linked_po':'PO-001',
                 'line_items':[dict(sku='ABC',description='Paper packs',quantity=12,unit_price=100,tax_rate=18)]}).json()['document']
        assert po['total']==1180
        assert inv['total']==1416
        # Reconciliation cannot be issued by a cross-site form without CSRF.
        assert client.post('/api/reconcile',json={'po_id':po['id'],'invoice_id':inv['id']}).status_code==403
        response=client.post('/api/reconcile',headers=headers,json={'po_id':po['id'],'invoice_id':inv['id']})
        assert response.status_code==200,response.text
        r=response.json()
        assert r['result']['discrepancy_count']>=2
        pdf=client.get(f"/api/reports/{r['report_id']}/pdf")
        assert pdf.status_code==200 and pdf.content[:4]==b'%PDF'
        batch=client.post('/api/reconcile/batch',headers=headers,json={'start_date':'2026-10-01','end_date':'2026-10-31'})
        assert batch.status_code==200,batch.text
        assert batch.json()['result']['matched_pairs']==1
        assert batch.json()['result']['total_discrepancies']>=2
        # A second user cannot read any of Alice's records or PDF reports.
        client.post('/api/auth/logout',headers=headers)
        other_headers=login_user(client,'bob@local.test')
        assert client.get('/api/documents/'+po['id']).status_code==404
        assert client.get(f"/api/reports/{r['report_id']}/pdf").status_code==404
        assert client.post('/api/reconcile',headers=other_headers,json={'po_id':po['id'],'invoice_id':inv['id']}).status_code==404


def test_forecasting_thresholds_and_synthetic_seed():
    with TestClient(app) as client:
        headers=login_user(client,'carol@local.test')
        assert all(not x['eligible'] for x in client.get('/api/forecast/eligibility').json()['tiers'])
        seed=client.post('/api/demo/seed',headers=headers)
        assert seed.status_code==200,seed.text
        assert '312 synthetic invoices' in seed.json()['message']
        elig=client.get('/api/forecast/eligibility').json()
        assert elig['count']==312 and elig['months_with_data']==12
        assert all(x['eligible'] for x in elig['tiers'])
        for horizon in (1,3,12):
            response=client.post(f'/api/forecast/{horizon}',headers=headers)
            assert response.status_code==200,response.text
            r=response.json()
            assert len(r['result']['forecast'])==horizon
            assert r['result']['currency']=='INR'
            assert client.get(f"/api/reports/{r['report_id']}/pdf").content.startswith(b'%PDF')
        docs=client.get('/api/documents').json()
        assert docs['total_matching']==624
        assert len(docs['items'])==400
        assert client.post('/api/demo/seed',headers=headers).status_code==409


def test_upload_unconfigured_and_retry():
    with TestClient(app) as client:
        headers=login_user(client,'dave@local.test')
        # Distinct PDFs should upload as pending when no Gemini key is set.
        response=client.post('/api/documents/upload',headers=headers,data={'doc_type':'po'},files={'file':('sample.pdf',b'%PDF-1.4\n% local test', 'application/pdf')})
        assert response.status_code==200,response.text
        d=response.json()['document']
        assert d['status']=='pending'
        assert client.post(f'/api/documents/{d["id"]}/extract',headers=headers).status_code==503
        edit=client.put(f'/api/documents/{d["id"]}',headers=headers,json={'doc_type':'po','number':'PO-2', 'vendor':'Demo', 'issue_date':'2026-10-02',
              'line_items':[{'sku':'P1','description':'A','quantity':1,'unit_price':1,'tax_rate':0}]})
        assert edit.status_code==200,edit.text
        assert edit.json()['document']['status']=='processed'
        assert client.get(f'/api/documents/{d["id"]}/original').status_code==200
        assert client.delete(f'/api/documents/{d["id"]}',headers=headers).status_code==200
        assert client.get(f'/api/documents/{d["id"]}/original').status_code==404
