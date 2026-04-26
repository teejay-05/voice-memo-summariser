"""
Twilio webhook handler.
Builds TwiML responses to control call flow and recording.
"""

from xml.etree.ElementTree import Element, SubElement, tostring
from fastapi.responses import Response


def build_twiml_response(
    message: str,
    record: bool = False,
    recording_callback: str = None,
) -> Response:
    """
    Build a TwiML XML response.

    Args:
        message: Text for Twilio to read to the caller.
        record: Whether to record the call after the message.
        recording_callback: URL to POST the recording to when done.

    Returns:
        FastAPI Response with TwiML XML content.
    """
    response = Element("Response")

    # Say the greeting
    say = SubElement(response, "Say", voice="Polly.Joanna", language="en-GB")
    say.text = message

    if record:
        record_attrs = {
            "maxLength": "120",         # 2 minute max memo
            "playBeep": "true",
            "trim": "trim-silence",
        }
        if recording_callback:
            record_attrs["recordingStatusCallback"] = recording_callback
            record_attrs["recordingStatusCallbackMethod"] = "POST"

        SubElement(response, "Record", **record_attrs)

        # Say goodbye after recording
        goodbye = SubElement(response, "Say", voice="Polly.Joanna", language="en-GB")
        goodbye.text = "Thank you! Your memo has been received and is being processed."

    xml_str = tostring(response, encoding="unicode", xml_declaration=False)
    twiml = f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_str}'

    return Response(content=twiml, media_type="application/xml")


def validate_twilio_signature(
    auth_token: str,
    signature: str,
    url: str,
    params: dict,
) -> bool:
    """
    Validate that a webhook request genuinely came from Twilio.
    Uses HMAC-SHA1 signature verification.
    """
    import hmac
    import hashlib
    import base64

    # Build the string to sign
    sorted_params = "".join(f"{k}{v}" for k, v in sorted(params.items()))
    string_to_sign = url + sorted_params

    # Compute expected signature
    mac = hmac.new(
        auth_token.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha1,
    )
    expected = base64.b64encode(mac.digest()).decode("utf-8")

    return hmac.compare_digest(expected, signature)
