from triage.redact import redact


def test_github_token_redacted():
    text, n = redact("using ghp_" + "a" * 36 + " to clone")
    assert "ghp_" not in text and n == 1


def test_key_value_secret_keeps_key_hides_value():
    text, _ = redact("export DB_PASSWORD=hunter2 && run")
    assert "hunter2" not in text
    assert "DB_PASSWORD=[REDACTED]" in text


def test_already_masked_values_left_alone():
    text, n = redact("GITHUB_TOKEN: ***")
    assert text == "GITHUB_TOKEN: ***" and n == 0


def test_bearer_header_and_url_credentials():
    text, _ = redact("Authorization: Bearer abc.def.ghi\nclone https://user:pw123@example.com/repo.git")
    assert "abc.def.ghi" not in text and "pw123" not in text


def test_multiline_private_key_removed():
    key = "-----BEGIN RSA PRIVATE KEY-----\nMIIEow\nabcdef\n-----END RSA PRIVATE KEY-----"
    text, _ = redact(f"before\n{key}\nafter")
    assert "MIIEow" not in text and "before" in text and "after" in text


def test_email_redacted_but_git_ssh_remote_kept():
    text, _ = redact("author dev@example.com, remote git@github.com:org/repo.git")
    assert "dev@example.com" not in text
    assert "git@github.com" in text


def test_diagnostic_text_untouched():
    line = "E   TimeoutError: delivery not acknowledged within 0.25s"
    assert redact(line) == (line, 0)
