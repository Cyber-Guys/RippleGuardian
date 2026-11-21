from decimal import Decimal

from ixh26 import config
from ixh26.contracts import XRP
from ixh26.flows import smoke
from ixh26.flows.monitor import Monitor
from ixh26.flows.report import build_incident, incident_pdf
from ixh26.flows.trace import run_trace_job
from ixh26.store.repo import Store

SETTINGS = config.load_settings({})


async def test_incident_has_timeline_trace_and_pdf() -> None:
    store = Store.from_url("sqlite://")
    await smoke.run_scenario(store)
    demo = store.user_by_name("demo")
    row = store.create_trace(demo.id, smoke.VICTIM, XRP, Decimal(95 * smoke.XRP1), 1001)
    await run_trace_job(smoke.FakeReader(smoke.scenario()), Monitor(store), row, SETTINGS)

    incident = build_incident(store, demo.id, smoke.VICTIM, SETTINGS)
    assert incident.compromised
    assert [s.title for s in incident.timeline] == ["Signing key changed", "Sent 95 XRP"]
    assert incident.stolen_drops == 95 * smoke.XRP1
    assert incident.exchanges[0]["destination_tag"] == smoke.TAG
    assert incident.reference.startswith("RG-") and len(incident.fingerprint) == 64

    pdf = incident_pdf(incident, SETTINGS)
    assert pdf.startswith(b"%PDF") and len(pdf) > 2000
