from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_legacy_revision_08_precedes_harvest_schema_and_handover_migrations():
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config()
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    script = ScriptDirectory.from_config(config)

    legacy_release = script.get_revision("20261007_08")
    harvest_schema = script.get_revision("20261008_15")
    handover_flow = script.get_revision("20261007_09")

    assert legacy_release.down_revision == "20261007_07"
    assert harvest_schema.down_revision == "20261007_08"
    assert handover_flow.down_revision == "20261008_15"
    recall_orders = script.get_revision("20261015_25")
    assert recall_orders.down_revision == "20261012_24"
    shipments = script.get_revision("20261016_26")
    assert shipments.down_revision == "20261015_25"
    telemetry = script.get_revision("20261018_27")
    assert telemetry.down_revision == "20261016_26"
    recall_order_lots = script.get_revision("20261019_28")
    assert recall_order_lots.down_revision == "20261018_27"
    violations = script.get_revision("20261019_29")
    assert violations.down_revision == "20261019_28"
    recall_confirmations = script.get_revision("20261020_30")
    assert recall_confirmations.down_revision == "20261019_29"
    public_trace = script.get_revision("20261020_31")
    assert public_trace.down_revision == "20261020_30"
    product_cold_chain_config = script.get_revision("20261020_32")
    assert product_cold_chain_config.down_revision == "20261020_31"
    integrity_scanner = script.get_revision("20261021_33")
    assert integrity_scanner.down_revision == "20261020_32"
    notifications = script.get_revision("20261021_34")
    assert notifications.down_revision == "20261021_33"
    invitations = script.get_revision("20261021_36")
    assert invitations.down_revision == "20261021_35"
    input_lots = script.get_revision("20261021_37")
    assert input_lots.down_revision == "20261021_36"
    processing_steps = script.get_revision("20261021_38")
    assert processing_steps.down_revision == "20261021_37"
    public_route = script.get_revision("20261021_39")
    assert public_route.down_revision == "20261021_38"
    aggregates = script.get_revision("20261021_40")
    assert aggregates.down_revision == "20261021_39"
    deactivate_guard = script.get_revision("20261021_41")
    assert deactivate_guard.down_revision == "20261021_40"
    rls_branches = script.get_revision("20261021_42")
    assert rls_branches.down_revision == "20261021_41"
    assert script.get_current_head() == "20261021_42"
