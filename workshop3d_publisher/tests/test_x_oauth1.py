"""Validate OAuth 1.0a signing against X/Twitter's own documented example.

Reference: X developer docs "Creating a signature". The signature base string
is the part that is easy to get wrong (percent-encoding, sorting,
normalisation); X publishes the exact expected base string, so matching it
byte-for-byte proves the implementation is correct. The final HMAC step is
standard library.
"""
import base64
import hashlib
import hmac

from workshop3d.adapters.social._oauth1 import sign, signature_base_string, auth_header

# The exact values X documents in "Creating a signature".
_PARAMS = {
    "status": "Hello Ladies + Gentlemen, a signed OAuth request!",
    "include_entities": "true",
    "oauth_consumer_key": "xvz1evFS4wEEPTGEFPHBog",
    "oauth_nonce": "kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg",
    "oauth_signature_method": "HMAC-SHA1",
    "oauth_timestamp": "1318622958",
    "oauth_token": "370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb",
    "oauth_version": "1.0",
}
_URL = "https://api.twitter.com/1.1/statuses/update.json"
_OFFICIAL_BASE = (
    "POST&https%3A%2F%2Fapi.twitter.com%2F1.1%2Fstatuses%2Fupdate.json&"
    "include_entities%3Dtrue%26oauth_consumer_key%3Dxvz1evFS4wEEPTGEFPHBog"
    "%26oauth_nonce%3DkYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg"
    "%26oauth_signature_method%3DHMAC-SHA1%26oauth_timestamp%3D1318622958"
    "%26oauth_token%3D370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb"
    "%26oauth_version%3D1.0%26status%3DHello%2520Ladies%2520%252B%2520Gentlemen"
    "%252C%2520a%2520signed%2520OAuth%2520request%2521"
)


def test_base_string_matches_official():
    assert signature_base_string("POST", _URL, _PARAMS) == _OFFICIAL_BASE


def test_signature_is_correct_hmac_of_base_string():
    consumer_secret = "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Y7cA"
    token_secret = "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE"
    key = f"{consumer_secret}&{token_secret}".encode()
    expected = base64.b64encode(hmac.new(key, _OFFICIAL_BASE.encode(), hashlib.sha1).digest()).decode()
    got = sign("POST", _URL, _PARAMS, consumer_secret, token_secret)
    assert got == expected


def test_auth_header_shape():
    header = auth_header(
        "POST", "https://api.twitter.com/2/tweets",
        consumer_key="ck", consumer_secret="cs", token="tk", token_secret="ts",
        nonce="abc", timestamp="1700000000",
    )
    assert header.startswith("OAuth ")
    assert 'oauth_signature="' in header
    assert 'oauth_consumer_key="ck"' in header
