"""
Audio Utilities for Local Testing

Provides audio format conversion helpers for microphone and speaker operations.
"""
import audioop
import logging

logger = logging.getLogger(__name__)


def pcm_to_mulaw(pcm_data: bytes, width: int = 2) -> bytes:
    """
    Convert PCM audio to mulaw format.
    
    Args:
        pcm_data: PCM audio bytes
        width: Sample width in bytes (default: 2 for 16-bit)
        
    Returns:
        Mulaw-encoded audio bytes
    """
    try:
        return audioop.lin2ulaw(pcm_data, width)
    except Exception as e:
        logger.error(f"[AUDIO] Error converting PCM to mulaw: {e}")
        raise


def mulaw_to_pcm(mulaw_data: bytes, width: int = 2) -> bytes:
    """
    Convert mulaw audio to PCM format.
    
    Args:
        mulaw_data: Mulaw-encoded audio bytes
        width: Sample width in bytes (default: 2 for 16-bit)
        
    Returns:
        PCM audio bytes
    """
    try:
        return audioop.ulaw2lin(mulaw_data, width)
    except Exception as e:
        logger.error(f"[AUDIO] Error converting mulaw to PCM: {e}")
        raise


def resample_audio(audio_data: bytes, width: int, in_rate: int, out_rate: int) -> bytes:
    """
    Resample audio to a different sample rate.
    
    Args:
        audio_data: Audio bytes to resample
        width: Sample width in bytes
        in_rate: Input sample rate
        out_rate: Output sample rate
        
    Returns:
        Resampled audio bytes
    """
    try:
        resampled, _ = audioop.ratecv(audio_data, width, 1, in_rate, out_rate, None)
        return resampled
    except Exception as e:
        logger.error(f"[AUDIO] Error resampling audio: {e}")
        raise


def adjust_volume(audio_data: bytes, width: int, factor: float) -> bytes:
    """
    Adjust audio volume by a factor.
    
    Args:
        audio_data: Audio bytes
        width: Sample width in bytes
        factor: Volume factor (1.0 = no change, 2.0 = double, 0.5 = half)
        
    Returns:
        Volume-adjusted audio bytes
    """
    try:
        return audioop.mul(audio_data, width, factor)
    except Exception as e:
        logger.error(f"[AUDIO] Error adjusting volume: {e}")
        raise
