#!/usr/bin/env python3
"""
Database Batch Operations for improved performance.
Provides batch upsert functionality to reduce database round trips.
"""

import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from collections import defaultdict
from core.logger import get_logger

logger = get_logger(__name__)


class DatabaseBatchManager:
    """
    Manages batch database operations for improved performance.
    Accumulates records and performs batch upserts when thresholds are met.
    """
    
    def __init__(self, supabase_client, batch_size: int = 25):
        """
        Initialize batch manager.
        
        Args:
            supabase_client: Supabase client instance
            batch_size: Number of records per batch (default: 25)
        """
        self.supabase = supabase_client
        self.batch_size = batch_size
        self.pending_records = defaultdict(list)  # table_name -> [records]
        self.batch_configs = {}  # table_name -> config
        self.stats = {
            'total_batches': 0,
            'total_records': 0,
            'total_time': 0.0
        }
        
        logger.info(f"📦 Database batch manager initialized (batch_size={batch_size})")
    
    def configure_table(self, table_name: str, conflict_columns: str):
        """
        Configure table-specific batch settings.
        
        Args:
            table_name: Name of the database table
            conflict_columns: Columns to use for conflict resolution
        """
        self.batch_configs[table_name] = {
            'on_conflict': conflict_columns
        }
        logger.debug(f"📋 Configured table '{table_name}' with conflict columns: {conflict_columns}")
    
    def add_record(self, table_name: str, record: Dict[str, Any], auto_flush: bool = True) -> bool:
        """
        Add a record to the batch queue.
        
        Args:
            table_name: Target table name
            record: Record data to insert/update
            auto_flush: Whether to auto-flush when batch size reached
            
        Returns:
            bool: True if batch was flushed, False otherwise
        """
        # Ensure table is configured
        if table_name not in self.batch_configs:
            logger.warning(f"Table '{table_name}' not configured, using default settings")
            self.configure_table(table_name, "id")
        
        # Add timestamp if not present
        if 'updated_at' not in record:
            record['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        self.pending_records[table_name].append(record)
        logger.debug(f"📝 Added record to batch queue for '{table_name}' "
                    f"({len(self.pending_records[table_name])}/{self.batch_size})")
        
        # Auto-flush if batch size reached
        if auto_flush and len(self.pending_records[table_name]) >= self.batch_size:
            return self.flush_table(table_name)
        
        return False
    
    def flush_table(self, table_name: str) -> bool:
        """
        Flush all pending records for a specific table.
        
        Args:
            table_name: Table to flush
            
        Returns:
            bool: True if successful, False otherwise
        """
        if table_name not in self.pending_records or not self.pending_records[table_name]:
            logger.debug(f"No pending records for table '{table_name}'")
            return True
        
        records = self.pending_records[table_name].copy()
        record_count = len(records)
        
        try:
            start_time = time.time()
            config = self.batch_configs.get(table_name, {'on_conflict': 'id'})
            
            logger.info(f"📦 Batch upserting {record_count} records to '{table_name}'...")
            
            response = (
                self.supabase.table(table_name)
                .upsert(records, on_conflict=config['on_conflict'])
                .execute()
            )
            
            if hasattr(response, 'error') and response.error:
                error_msg = (
                    response.error.message 
                    if hasattr(response.error, 'message') 
                    else str(response.error)
                )
                logger.error(f"❌ Batch upsert failed for '{table_name}': {error_msg}")
                return False
            
            # Success - clear pending records and update stats
            self.pending_records[table_name].clear()
            elapsed = time.time() - start_time
            
            self.stats['total_batches'] += 1
            self.stats['total_records'] += record_count
            self.stats['total_time'] += elapsed
            
            avg_time_per_record = (elapsed / record_count) * 1000  # ms per record
            
            logger.info(f"✅ Successfully batch upserted {record_count} records to '{table_name}' "
                       f"({elapsed:.2f}s, {avg_time_per_record:.1f}ms/record)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Batch upsert error for '{table_name}': {str(e)}")
            return False
    
    def flush_all(self) -> Dict[str, bool]:
        """
        Flush all pending records for all tables.
        
        Returns:
            dict: Table name -> success status
        """
        results = {}
        
        for table_name in list(self.pending_records.keys()):
            if self.pending_records[table_name]:  # Only flush if has records
                results[table_name] = self.flush_table(table_name)
        
        return results
    
    def get_pending_count(self, table_name: Optional[str] = None) -> int:
        """
        Get count of pending records.
        
        Args:
            table_name: Specific table name, or None for total count
            
        Returns:
            int: Number of pending records
        """
        if table_name:
            return len(self.pending_records.get(table_name, []))
        else:
            return sum(len(records) for records in self.pending_records.values())
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get batch operation statistics.
        
        Returns:
            dict: Statistics including batches, records, timing
        """
        stats = self.stats.copy()
        stats['pending_records'] = self.get_pending_count()
        stats['avg_batch_time'] = (
            self.stats['total_time'] / max(self.stats['total_batches'], 1)
        )
        stats['avg_record_time'] = (
            self.stats['total_time'] / max(self.stats['total_records'], 1)
        ) * 1000  # Convert to milliseconds
        
        return stats
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Auto-flush all pending records when exiting context."""
        results = self.flush_all()
        
        # Log summary
        total_pending = sum(len(records) for records in self.pending_records.values())
        if total_pending > 0:
            logger.info(f"🔄 Context exit: flushed pending records for {len(results)} tables")
        
        stats = self.get_stats()
        logger.info(f"📊 Batch operation summary: {stats['total_batches']} batches, "
                   f"{stats['total_records']} records, {stats['total_time']:.2f}s total, "
                   f"{stats['avg_record_time']:.1f}ms/record")


# Global batch manager instance
_batch_manager = None


def get_batch_manager(supabase_client=None, batch_size: int = 25) -> DatabaseBatchManager:
    """
    Get or create the global batch manager instance.
    
    Args:
        supabase_client: Supabase client (required for first call)
        batch_size: Batch size for new instance
        
    Returns:
        DatabaseBatchManager: Global batch manager instance
    """
    global _batch_manager
    
    if _batch_manager is None:
        if supabase_client is None:
            raise ValueError("supabase_client is required for first call to get_batch_manager")
        _batch_manager = DatabaseBatchManager(supabase_client, batch_size)
    
    return _batch_manager


def cleanup_batch_manager():
    """Clean up the global batch manager."""
    global _batch_manager
    
    if _batch_manager is not None:
        _batch_manager.flush_all()
        _batch_manager = None
        logger.debug("🧹 Global batch manager cleaned up")