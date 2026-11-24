from open_data_elt import alert


class FakePost:
    def __init__(self, status=200):
        self.status, self.calls = status, []

    def post(self, url, json, timeout):
        self.calls.append((url, json))
        return type("R", (), {"status_code": self.status})()


def test_message_has_step_error_lines_and_run_link(tmp_path, monkeypatch):
    log = tmp_path / "load.log"
    log.write_text(
        "[load] fuelprice: incremental via API since 2026-10-15\n"
        "LOAD FAILED: SchemaDriftError: fuelprice: required column(s) ['ron97'] missing\n"
    )
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_REPOSITORY", "someone/open-data-elt-pipeline")
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    msg = alert.build_message("load", log)
    assert "step: load" in msg
    assert "SchemaDriftError" in msg and "incremental via API" not in msg
    assert msg.endswith("/someone/open-data-elt-pipeline/actions/runs/42")


def test_send_without_secrets_prints_and_returns_false(monkeypatch, capsys):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert alert.send("boom") is False
    assert "boom" in capsys.readouterr().out


def test_send_posts_to_bot_and_hides_token_on_error(monkeypatch, capsys):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:secret")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999")
    ok = FakePost(200)
    assert alert.send("hi", session=ok) is True
    assert ok.calls[0][1] == {"chat_id": "999", "text": "hi", "disable_web_page_preview": True}
    assert alert.send("hi", session=FakePost(401)) is False
    assert "secret" not in capsys.readouterr().out


def test_dbt_test_summary_counts_tests_only(tmp_path):
    import json

    from open_data_elt.export import dbt_test_summary

    path = tmp_path / "rr.json"
    path.write_text(
        json.dumps(
            {
                "metadata": {"generated_at": "2026-11-24T00:00:00Z"},
                "results": [
                    {"unique_id": "model.open_data.dim_date", "status": "success"},
                    {"unique_id": "test.open_data.unique_x", "status": "pass"},
                    {"unique_id": "unit_test.open_data.m.t", "status": "pass"},
                    {"unique_id": "test.open_data.not_null_y", "status": "fail"},
                ],
            }
        )
    )
    s = dbt_test_summary(path)
    assert (s["total"], s["by_status"]) == (3, {"pass": 2, "fail": 1})
    assert s["failed"] == ["test.open_data.not_null_y"]
