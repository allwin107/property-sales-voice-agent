import json
import asyncio
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class EnquiryStorage:
    """Storage for property enquiries"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_file()
    
    def _initialize_file(self):
        if not self.file_path.exists():
            self.file_path.write_text("[]")
            logger.info(f"Created enquiries file: {self.file_path}")
    
    async def save_enquiry(self, enquiry: dict) -> bool:
        try:
            enquiries = await self.get_all_enquiries()
            enquiries.append(enquiry)
            
            self.file_path.write_text(json.dumps(enquiries, indent=2))
            logger.info(f"Saved enquiry: {enquiry['enquiry_id']}")
            return True
        except Exception as e:
            logger.error(f"Error saving enquiry: {e}")
            return False
    
    async def get_enquiry(self, enquiry_id: str) -> dict:
        enquiries = await self.get_all_enquiries()
        for enq in enquiries:
            if enq['enquiry_id'] == enquiry_id:
                return enq
        return None
    
    async def update_enquiry(self, enquiry_id: str, updates: dict) -> bool:
        try:
            enquiries = await self.get_all_enquiries()
            for enq in enquiries:
                if enq['enquiry_id'] == enquiry_id:
                    enq.update(updates)
                    break
            
            self.file_path.write_text(json.dumps(enquiries, indent=2))
            logger.info(f"Updated enquiry: {enquiry_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating enquiry: {e}")
            return False
    
    async def get_all_enquiries(self) -> list:
        try:
            return json.loads(self.file_path.read_text())
        except:
            return []
