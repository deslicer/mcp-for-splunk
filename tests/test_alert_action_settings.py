"""Unit tests for alert action field mapping."""

from src.tools.alerts.alert_action_settings import AlertActionSettings
from src.tools.alerts.alert_saved_search import create_alert_config


class TestAlertActionSettings:
    def setup_method(self) -> None:
        self.mapper = AlertActionSettings()

    def test_email_uses_flat_param_keys(self) -> None:
        fields = self.mapper.splunk_fields(
            [
                {
                    "name": "email",
                    "params": {"to": "ops@example.com", "subject": "High errors"},
                    "enabled": True,
                }
            ]
        )
        assert fields["actions"] == "email"
        assert fields["action.email"] == "1"
        assert fields["action.email.to"] == "ops@example.com"
        assert fields["action.email.subject"] == "High errors"

    def test_custom_action_prefixes_param(self) -> None:
        fields = self.mapper.splunk_fields(
            [{"name": "my_pagerduty", "params": {"routing_key": "R0abc"}}]
        )
        assert fields["action.my_pagerduty"] == "1"
        assert fields["action.my_pagerduty.param.routing_key"] == "R0abc"
        assert fields["actions"] == "my_pagerduty"

    def test_dotted_param_key_is_used_as_is(self) -> None:
        fields = self.mapper.splunk_fields(
            [{"name": "webhook", "params": {"param.url": "https://hooks.example/splunk"}}]
        )
        assert fields["action.webhook.param.url"] == "https://hooks.example/splunk"

    def test_multiple_actions_join_csv(self) -> None:
        fields = self.mapper.splunk_fields(
            [
                {"name": "email", "params": {"to": "a@b.com"}},
                {"name": "rss", "params": {}},
            ]
        )
        assert fields["actions"] == "email,rss"
        assert fields["action.email"] == "1"
        assert fields["action.rss"] == "1"

    def test_patch_keeps_other_actions_and_unspecified_params(self) -> None:
        current = {
            "actions": "email,webhook",
            "action.email": "1",
            "action.email.to": "ops@example.com",
            "action.email.subject": "Old",
            "action.webhook": "1",
            "action.webhook.param.url": "https://old.example",
        }
        fields = self.mapper.patch_fields(
            current,
            [{"name": "email", "params": {"subject": "New subject"}}],
        )
        assert fields["action.email"] == "1"
        assert fields["action.email.subject"] == "New subject"
        assert "action.email.to" not in fields
        assert "action.webhook" not in fields
        assert fields["actions"] == "email,webhook"

    def test_patch_can_disable_one_action(self) -> None:
        current = {"actions": "email,rss", "action.email": "1", "action.rss": "1"}
        fields = self.mapper.patch_fields(
            current,
            [{"name": "email", "enabled": False, "params": {}}],
        )
        assert fields["action.email"] == "0"
        assert fields["actions"] == "rss"

    def test_override_disables_missing_actions(self) -> None:
        current = {"actions": "email,rss", "action.email": "1", "action.rss": "1"}
        fields = self.mapper.override_fields(
            current,
            [{"name": "webhook", "params": {"url": "https://hooks.example"}}],
        )
        assert fields["actions"] == "webhook"
        assert fields["action.webhook"] == "1"
        assert fields["action.webhook.param.url"] == "https://hooks.example"
        assert fields["action.email"] == "0"
        assert fields["action.rss"] == "0"

    def test_parse_actions_accepts_json_string(self) -> None:
        parsed = self.mapper.parse_actions(
            '[{"name": "email", "params": {"to": "ops@example.com"}}]'
        )
        assert parsed == [
            {"name": "email", "params": {"to": "ops@example.com"}, "enabled": True}
        ]


class TestCreateAlertConfig:
    def test_uses_rest_alert_argument_names(self) -> None:
        config = create_alert_config(
            search="index=_internal | head 1",
            description="probe",
            earliest_time="-15m",
            latest_time="now",
            cron_schedule="0 0 1 1 *",
            is_visible=True,
            alert_type="number of events",
            alert_comparator="greater than",
            alert_threshold="0",
            alert_condition="",
            alert_track=True,
            alert_severity=3,
            alert_digest_mode=True,
        )
        assert "alert.comparator" not in config
        assert "alert.threshold" not in config
        assert config["alert_comparator"] == "greater than"
        assert config["alert_threshold"] == "0"
        assert config["alert.track"] == "1"
