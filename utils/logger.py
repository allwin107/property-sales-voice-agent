"""
Logger Utility - Enhanced logging with colored output, file logging, and metrics tracking
"""
import logging
import os
import sys
import json
from datetime import datetime
from enum import Enum
from typing import Optional, Dict
from pathlib import Path
import threading


class ErrorCategory(Enum):
    """Error categories for better organization"""
    API_ERROR = "API_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    DATA_VALIDATION_ERROR = "DATA_VALIDATION_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    SERVICE_ERROR = "SERVICE_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for better readability"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
        'BOLD': '\033[1m',        # Bold
    }
    
    # Special prefixes with their colors
    PREFIX_COLORS = {
        'SESSION': '\033[34m',    # Blue
        'WEBSOCKET': '\033[36m',  # Cyan
        'WEBHOOK': '\033[35m',    # Magenta
        'INCOMING': '\033[32m',   # Green
        'AUDIO': '\033[33m',      # Yellow
        'API': '\033[36m',        # Cyan
        'TEST': '\033[35m',       # Magenta
        'SHUTDOWN': '\033[31m',   # Red
        'ERROR': '\033[31m',      # Red
        'RETRY': '\033[33m',      # Yellow
        'CLEANUP': '\033[33m',    # Yellow
    }
    
    def format(self, record):
        # Get base format
        log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Color the level name
        levelname = record.levelname
        colored_levelname = f"{self.COLORS.get(levelname, '')}{self.COLORS['BOLD']}{levelname}{self.COLORS['RESET']}"
        
        # Color special prefixes in message
        message = record.getMessage()
        for prefix, color in self.PREFIX_COLORS.items():
            if f'[{prefix}' in message:
                message = message.replace(f'[{prefix}', f'{color}[{prefix}{self.COLORS["RESET"]}')
        
        # Create colored record
        colored_record = logging.LogRecord(
            name=record.name,
            level=record.levelno,
            pathname=record.pathname,
            lineno=record.lineno,
            msg=message,
            args=(),
            exc_info=record.exc_info
        )
        colored_record.levelname = colored_levelname
        
        # Format with colored values
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(colored_record)


class MetricsTracker:
    """Track performance metrics across sessions"""
    
    def __init__(self):
        self.metrics = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'total_duration': 0,
            'response_times': [],
            'stt_latencies': [],
            'llm_response_times': [],
            'tts_synthesis_times': [],
            'interruptions': 0,
            'data_extractions_success': 0,
            'data_extractions_failed': 0,
            'errors_by_category': {cat.value: 0 for cat in ErrorCategory},
            'slow_responses': 0,  # Responses > 2s
        }
        self.session_metrics = {}
        self.lock = threading.Lock()
    
    def start_call(self, session_id: str):
        """Start tracking a call"""
        with self.lock:
            self.metrics['total_calls'] += 1
            self.session_metrics[session_id] = {
                'start_time': datetime.now(),
                'interruptions': 0,
                'messages_exchanged': 0,
                'stt_latencies': [],
                'llm_times': [],
                'tts_times': [],
            }
    
    def end_call(self, session_id: str, success: bool = True):
        """End tracking a call"""
        with self.lock:
            if session_id in self.session_metrics:
                session = self.session_metrics[session_id]
                duration = (datetime.now() - session['start_time']).total_seconds()
                
                self.metrics['total_duration'] += duration
                if success:
                    self.metrics['successful_calls'] += 1
                else:
                    self.metrics['failed_calls'] += 1
                
                # Remove session metrics
                del self.session_metrics[session_id]
    
    def record_stt_latency(self, session_id: str, latency_ms: float):
        """Record STT latency"""
        with self.lock:
            self.metrics['stt_latencies'].append(latency_ms)
            if session_id in self.session_metrics:
                self.session_metrics[session_id]['stt_latencies'].append(latency_ms)
    
    def record_llm_time(self, session_id: str, time_ms: float):
        """Record LLM response time"""
        with self.lock:
            self.metrics['llm_response_times'].append(time_ms)
            if session_id in self.session_metrics:
                self.session_metrics[session_id]['llm_times'].append(time_ms)
            
            # Check if slow
            if time_ms > 2000:  # 2 seconds
                self.metrics['slow_responses'] += 1
    
    def record_tts_time(self, session_id: str, time_ms: float):
        """Record TTS synthesis time"""
        with self.lock:
            self.metrics['tts_synthesis_times'].append(time_ms)
            if session_id in self.session_metrics:
                self.session_metrics[session_id]['tts_times'].append(time_ms)
    
    def record_interruption(self, session_id: str):
        """Record user interruption"""
        with self.lock:
            self.metrics['interruptions'] += 1
            if session_id in self.session_metrics:
                self.session_metrics[session_id]['interruptions'] += 1
    
    def record_data_extraction(self, success: bool):
        """Record data extraction attempt"""
        with self.lock:
            if success:
                self.metrics['data_extractions_success'] += 1
            else:
                self.metrics['data_extractions_failed'] += 1
    
    def record_error(self, category: ErrorCategory):
        """Record error by category"""
        with self.lock:
            self.metrics['errors_by_category'][category.value] += 1
    
    def get_summary(self) -> Dict:
        """Get metrics summary"""
        with self.lock:
            avg_duration = self.metrics['total_duration'] / max(self.metrics['total_calls'], 1)
            
            avg_stt = sum(self.metrics['stt_latencies']) / max(len(self.metrics['stt_latencies']), 1)
            avg_llm = sum(self.metrics['llm_response_times']) / max(len(self.metrics['llm_response_times']), 1)
            avg_tts = sum(self.metrics['tts_synthesis_times']) / max(len(self.metrics['tts_synthesis_times']), 1)
            
            return {
                'total_calls': self.metrics['total_calls'],
                'successful_calls': self.metrics['successful_calls'],
                'failed_calls': self.metrics['failed_calls'],
                'success_rate': f"{(self.metrics['successful_calls'] / max(self.metrics['total_calls'], 1)) * 100:.1f}%",
                'average_call_duration': f"{avg_duration:.1f}s",
                'average_stt_latency': f"{avg_stt:.0f}ms",
                'average_llm_time': f"{avg_llm:.0f}ms",
                'average_tts_time': f"{avg_tts:.0f}ms",
                'total_interruptions': self.metrics['interruptions'],
                'data_extraction_success_rate': f"{(self.metrics['data_extractions_success'] / max(self.metrics['data_extractions_success'] + self.metrics['data_extractions_failed'], 1)) * 100:.1f}%",
                'slow_responses': self.metrics['slow_responses'],
                'errors_by_category': self.metrics['errors_by_category'],
                'active_sessions': len(self.session_metrics)
            }
    
    def save_to_file(self, filepath: str):
        """Save metrics to JSON file"""
        with self.lock:
            summary = self.get_summary()
            summary['timestamp'] = datetime.now().isoformat()
            
            with open(filepath, 'w') as f:
                json.dump(summary, f, indent=2)


# Global metrics tracker
_metrics_tracker = MetricsTracker()


def setup_logging(log_dir: str = "logs", app_name: str = "hospital_receptionist"):
    """
    Set up logging with colored console output and file logging.
    
    Args:
        log_dir: Directory to store log files
        app_name: Name of the application for log files
        
    Returns:
        Logger instance
    """
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger(app_name)
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)
    
    # File handler for all logs
    app_log_file = log_path / f"{app_name}.log"
    file_handler = logging.FileHandler(app_log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Separate file handler for errors only
    error_log_file = log_path / "errors.log"
    error_handler = logging.FileHandler(error_log_file, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)
    
    logger.info(f"Logging initialized - App log: {app_log_file}, Error log: {error_log_file}")
    
    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (uses root logger if None)
        
    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(name)
    return logging.getLogger("hospital_receptionist")


def log_session_start(session_id: str, caller_info: Dict = None):
    """
    Log session start with caller information.
    
    Args:
        session_id: Session identifier
        caller_info: Dictionary with caller information
    """
    logger = get_logger()
    logger.info(f"[SESSION {session_id}] Call started")
    
    if caller_info:
        logger.info(f"[SESSION {session_id}] Caller: {caller_info.get('from', 'Unknown')}")
        logger.info(f"[SESSION {session_id}] Call SID: {caller_info.get('call_sid', 'Unknown')}")
    
    _metrics_tracker.start_call(session_id)


def log_session_end(session_id: str, duration: float, success: bool = True):
    """
    Log session end with duration.
    
    Args:
        session_id: Session identifier
        duration: Call duration in seconds
        success: Whether call completed successfully
    """
    logger = get_logger()
    logger.info(f"[SESSION {session_id}] Call ended - Duration: {duration:.1f}s")
    
    _metrics_tracker.end_call(session_id, success)


def log_metrics(session_id: str, metric_type: str, value: float, details: Dict = None):
    """
    Log performance metrics.
    
    Args:
        session_id: Session identifier
        metric_type: Type of metric (stt_latency, llm_time, tts_time)
        value: Metric value in milliseconds
        details: Additional details to log
    """
    logger = get_logger()
    
    # Log based on type
    if metric_type == "stt_latency":
        logger.debug(f"[SESSION {session_id}] STT latency: {value:.0f}ms")
        _metrics_tracker.record_stt_latency(session_id, value)
        
    elif metric_type == "llm_time":
        if value > 2000:  # Slow response
            logger.warning(f"[SESSION {session_id}] LLM response time: {value:.0f}ms (SLOW)")
        else:
            logger.debug(f"[SESSION {session_id}] LLM response time: {value:.0f}ms")
        _metrics_tracker.record_llm_time(session_id, value)
        
    elif metric_type == "tts_time":
        logger.debug(f"[SESSION {session_id}] TTS synthesis time: {value:.0f}ms")
        _metrics_tracker.record_tts_time(session_id, value)
        
    elif metric_type == "interruption":
        logger.info(f"[SESSION {session_id}] User interruption detected")
        _metrics_tracker.record_interruption(session_id)
    
    # Log additional details
    if details:
        for key, val in details.items():
            logger.debug(f"[SESSION {session_id}] {key}: {val}")


def log_error(error: Exception, category: ErrorCategory, session_id: str = None, context: str = None):
    """
    Log error with categorization.
    
    Args:
        error: Exception object
        category: Error category
        session_id: Session identifier (optional)
        context: Additional context (optional)
    """
    logger = get_logger()
    
    prefix = f"[SESSION {session_id}] " if session_id else ""
    context_str = f" - Context: {context}" if context else ""
    
    logger.error(
        f"{prefix}[{category.value}] {str(error)}{context_str}",
        exc_info=True
    )
    
    _metrics_tracker.record_error(category)


def log_data_extraction(session_id: str, success: bool, extracted_fields: Dict = None):
    """
    Log data extraction attempt.
    
    Args:
        session_id: Session identifier
        success: Whether extraction was successful
        extracted_fields: Dictionary of extracted fields
    """
    logger = get_logger()
    
    if success:
        logger.info(f"[SESSION {session_id}] Data extraction successful: {list(extracted_fields.keys()) if extracted_fields else []}")
    else:
        logger.warning(f"[SESSION {session_id}] Data extraction failed")
    
    _metrics_tracker.record_data_extraction(success)


def get_metrics_summary() -> Dict:
    """
    Get summary of all tracked metrics.
    
    Returns:
        Dictionary with metrics summary
    """
    return _metrics_tracker.get_summary()


def save_metrics(filepath: str = "logs/metrics.json"):
    """
    Save metrics to file.
    
    Args:
        filepath: Path to save metrics
    """
    _metrics_tracker.save_to_file(filepath)
    logger = get_logger()
    logger.info(f"Metrics saved to {filepath}")


def log_performance_summary(session_id: str, metrics: Dict):
    """
    Log performance summary for a session.
    
    Args:
        session_id: Session identifier
        metrics: Dictionary with performance metrics
    """
    logger = get_logger()
    
    logger.info(f"[SESSION {session_id}] Performance Summary:")
    logger.info(f"[SESSION {session_id}]   Total Duration: {metrics.get('duration', 0):.1f}s")
    logger.info(f"[SESSION {session_id}]   Messages: {metrics.get('messages', 0)}")
    logger.info(f"[SESSION {session_id}]   Interruptions: {metrics.get('interruptions', 0)}")
    logger.info(f"[SESSION {session_id}]   Avg STT: {metrics.get('avg_stt', 0):.0f}ms")
    logger.info(f"[SESSION {session_id}]   Avg LLM: {metrics.get('avg_llm', 0):.0f}ms")
    logger.info(f"[SESSION {session_id}]   Avg TTS: {metrics.get('avg_tts', 0):.0f}ms")
