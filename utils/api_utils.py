from urllib.parse import urlparse, parse_qs


def url_to_params_dict(url: str) -> dict:
    parsed = urlparse(url)
    params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    return params
