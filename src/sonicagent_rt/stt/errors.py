"""Typed failures for batch speech requests.

API routes map these to stable ``error.code`` values. Messages are safe to
return to callers: they do not include audio, transcripts, secrets, or paths.
"""

from __future__ import annotations


class SpeechError(Exception):
    """Base class for expected speech-service failures."""

    code = "inference_failed"
    status_code = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class Unauthenticated(SpeechError):
    code = "unauthenticated"
    status_code = 401


class OriginDenied(SpeechError):
    code = "origin_denied"
    status_code = 403


class VoiceDisabled(SpeechError):
    code = "voice_disabled"
    status_code = 404


class InvalidRequest(SpeechError):
    code = "invalid_request"
    status_code = 400


class UnsupportedLanguage(SpeechError):
    code = "unsupported_language"
    status_code = 400


class UnsupportedModel(SpeechError):
    code = "unsupported_model"
    status_code = 400


class UnsupportedFormat(SpeechError):
    code = "unsupported_format"
    status_code = 400


class UnsupportedCodec(SpeechError):
    code = "unsupported_codec"
    status_code = 415


class AudioTooLarge(SpeechError):
    code = "audio_too_large"
    status_code = 413


class AudioTooLong(SpeechError):
    code = "audio_too_long"
    status_code = 413


class TextTooLong(SpeechError):
    code = "text_too_long"
    status_code = 413


class InvalidAudio(SpeechError):
    code = "invalid_audio"
    status_code = 422


class RateLimited(SpeechError):
    code = "rate_limited"
    status_code = 429


class DuplicateRequest(SpeechError):
    code = "duplicate_request"
    status_code = 409


class Cancelled(SpeechError):
    code = "cancelled"
    status_code = 408


class InferenceTimeout(SpeechError):
    code = "timeout"
    status_code = 504


class BackendWarming(SpeechError):
    code = "backend_warming"
    status_code = 503


class ModelUnavailable(SpeechError):
    code = "model_unavailable"
    status_code = 503


class VoiceUnavailable(SpeechError):
    code = "voice_unavailable"
    status_code = 503


class InferenceFailed(SpeechError):
    code = "inference_failed"
    status_code = 500
