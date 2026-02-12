"""
Storage Service - Appointment Data Management
Simple JSON-based storage for appointment data
"""
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import aiofiles
from pathlib import Path

logger = logging.getLogger(__name__)

# Path to appointments data file
DATA_DIR = Path(__file__).parent.parent / "data"
APPOINTMENTS_FILE = DATA_DIR / "appointments.json"


class AppointmentStorage:
    """
    Simple JSON-based storage for appointment data
    """
    
    def __init__(self, file_path: str = None):
        """
        Initialize appointment storage
        
        Args:
            file_path: Path to appointments JSON file (optional)
        """
        self.file_path = file_path or str(APPOINTMENTS_FILE)
        logger.info(f"[STORAGE] Initialized with file: {self.file_path}")
        
    async def initialize(self):
        """Initialize storage - create file if it doesn't exist"""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            
            # Check if file exists
            if not os.path.exists(self.file_path):
                logger.info(f"[STORAGE] Creating new appointments file: {self.file_path}")
                async with aiofiles.open(self.file_path, 'w') as f:
                    await f.write('[]')
                logger.info("[STORAGE] Appointments file created successfully")
            else:
                logger.info("[STORAGE] Appointments file already exists")
                
        except Exception as e:
            logger.error(f"[ERROR] Failed to initialize storage: {e}", exc_info=True)
            raise
    
    async def save_appointment(self, session_id: str, data: Dict) -> bool:
        """
        Save appointment data to storage
        
        Args:
            session_id: Unique session identifier
            data: Appointment data dictionary
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            logger.info(f"[STORAGE] Saving appointment for session: {session_id}")
            
            # Ensure file exists
            await self.initialize()
            
            # Read existing appointments
            appointments = await self._read_appointments()
            
            # Create appointment record
            appointment = {
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "patient_name": data.get("patient_name", ""),
                "phone_number": data.get("phone_number", ""),
                "appointment_type": data.get("appointment_type", ""),
                "department": data.get("department", ""),
                "preferred_date": data.get("preferred_date", ""),
                "chief_complaint": data.get("chief_complaint", ""),
                "call_duration": data.get("call_duration", 0)
            }
            
            # Check if appointment with this session_id already exists
            existing_index = None
            for i, appt in enumerate(appointments):
                if appt.get("session_id") == session_id:
                    existing_index = i
                    break
            
            if existing_index is not None:
                # Update existing appointment
                appointments[existing_index] = appointment
                logger.info(f"[STORAGE] Updated existing appointment for session: {session_id}")
            else:
                # Append new appointment
                appointments.append(appointment)
                logger.info(f"[STORAGE] Added new appointment for session: {session_id}")
            
            # Write back to file
            await self._write_appointments(appointments)
            
            logger.info(f"[STORAGE] Successfully saved appointment: {appointment['patient_name']}")
            logger.debug(f"[STORAGE] Appointment details: {appointment}")
            
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to save appointment: {e}", exc_info=True)
            return False
    
    async def get_appointment(self, session_id: str) -> Optional[Dict]:
        """
        Retrieve appointment by session_id
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Appointment dictionary if found, None otherwise
        """
        try:
            logger.info(f"[STORAGE] Retrieving appointment for session: {session_id}")
            
            # Read all appointments
            appointments = await self._read_appointments()
            
            # Find appointment with matching session_id
            for appointment in appointments:
                if appointment.get("session_id") == session_id:
                    logger.info(f"[STORAGE] Found appointment for session: {session_id}")
                    logger.debug(f"[STORAGE] Appointment data: {appointment}")
                    return appointment
            
            logger.warning(f"[STORAGE] No appointment found for session: {session_id}")
            return None
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to retrieve appointment: {e}", exc_info=True)
            return None
    
    async def get_all_appointments(self) -> List[Dict]:
        """
        Retrieve all appointments
        
        Returns:
            List of all appointment dictionaries
        """
        try:
            logger.info("[STORAGE] Retrieving all appointments")
            
            appointments = await self._read_appointments()
            
            logger.info(f"[STORAGE] Retrieved {len(appointments)} appointments")
            return appointments
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to retrieve appointments: {e}", exc_info=True)
            return []
    
    async def delete_appointment(self, session_id: str) -> bool:
        """
        Delete appointment by session_id
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            logger.info(f"[STORAGE] Deleting appointment for session: {session_id}")
            
            # Read all appointments
            appointments = await self._read_appointments()
            
            # Filter out the appointment to delete
            original_count = len(appointments)
            appointments = [a for a in appointments if a.get("session_id") != session_id]
            
            if len(appointments) < original_count:
                # Appointment was found and removed
                await self._write_appointments(appointments)
                logger.info(f"[STORAGE] Successfully deleted appointment for session: {session_id}")
                return True
            else:
                logger.warning(f"[STORAGE] No appointment found to delete for session: {session_id}")
                return False
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to delete appointment: {e}", exc_info=True)
            return False
    
    async def get_appointments_by_date(self, date_str: str) -> List[Dict]:
        """
        Get appointments for a specific date
        
        Args:
            date_str: Date string to search for
            
        Returns:
            List of appointments for the given date
        """
        try:
            logger.info(f"[STORAGE] Retrieving appointments for date: {date_str}")
            
            appointments = await self._read_appointments()
            
            # Filter appointments by preferred_date
            filtered = [
                a for a in appointments 
                if date_str.lower() in a.get("preferred_date", "").lower()
            ]
            
            logger.info(f"[STORAGE] Found {len(filtered)} appointments for date: {date_str}")
            return filtered
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to retrieve appointments by date: {e}", exc_info=True)
            return []
    
    async def _read_appointments(self) -> List[Dict]:
        """
        Read appointments from file (internal method)
        
        Returns:
            List of appointment dictionaries
        """
        try:
            # Ensure file exists
            if not os.path.exists(self.file_path):
                await self.initialize()
                return []
            
            # Read file content
            async with aiofiles.open(self.file_path, 'r') as f:
                content = await f.read()
            
            # Parse JSON
            if not content or content.strip() == '':
                return []
            
            appointments = json.loads(content)
            
            if not isinstance(appointments, list):
                logger.warning("[STORAGE] Invalid appointments format, resetting to empty array")
                return []
            
            return appointments
            
        except json.JSONDecodeError as e:
            logger.error(f"[ERROR] JSON decode error: {e}")
            logger.warning("[STORAGE] Corrupted JSON file, returning empty list")
            return []
        except Exception as e:
            logger.error(f"[ERROR] Failed to read appointments: {e}", exc_info=True)
            return []
    
    async def _write_appointments(self, appointments: List[Dict]):
        """
        Write appointments to file (internal method)
        
        Args:
            appointments: List of appointment dictionaries
        """
        try:
            # Convert to JSON with pretty printing
            content = json.dumps(appointments, indent=2, ensure_ascii=False)
            
            # Write to file
            async with aiofiles.open(self.file_path, 'w') as f:
                await f.write(content)
            
            logger.debug(f"[STORAGE] Written {len(appointments)} appointments to file")
            
        except Exception as e:
            logger.error(f"[ERROR] Failed to write appointments: {e}", exc_info=True)
            raise


# Singleton instance
_storage_instance = None


async def get_storage() -> AppointmentStorage:
    """
    Get or create storage instance (singleton pattern)
    
    Returns:
        AppointmentStorage instance
    """
    global _storage_instance
    
    if _storage_instance is None:
        _storage_instance = AppointmentStorage()
        await _storage_instance.initialize()
        logger.info("[FACTORY] Created storage instance")
    
    return _storage_instance


# Convenience functions for direct use
async def save_appointment(session_id: str, data: Dict) -> bool:
    """Save appointment data"""
    storage = await get_storage()
    return await storage.save_appointment(session_id, data)


async def get_appointment(session_id: str) -> Optional[Dict]:
    """Get appointment by session_id"""
    storage = await get_storage()
    return await storage.get_appointment(session_id)


async def get_all_appointments() -> List[Dict]:
    """Get all appointments"""
    storage = await get_storage()
    return await storage.get_all_appointments()


async def delete_appointment(session_id: str) -> bool:
    """Delete appointment by session_id"""
    storage = await get_storage()
    return await storage.delete_appointment(session_id)


async def get_appointments_by_date(date_str: str) -> List[Dict]:
    """Get appointments for a specific date"""
    storage = await get_storage()
    return await storage.get_appointments_by_date(date_str)
