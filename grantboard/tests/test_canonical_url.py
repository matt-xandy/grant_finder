from grantboard.app.pipeline.normalize import canonical_url


def test_canonical_url_removes_query_and_trailing_slash():
    url = "https://Example.com/path/?utm_source=foo"
    assert canonical_url(url) == "https://example.com/path"
