"""
Unified Logger for BOT-VCSGO-BETA-V2 Scrapers
Simplifies logging for both batch (steam_listing) and non-batch (steamid_scraper) operations
"""

import logging
import time
from typing import Optional, Dict, Any, List, Union
from pathlib import Path


class UnifiedLogger:
    """
    Unified logging system that handles both batch and non-batch operations
    
    Features:
    - Batch progress tracking with detailed statistics
    - Performance metrics (rate, ETA, success rate)
    - Proxy manager integration logging
    - WSL system detection logging
    - Consistent format across all scrapers
    - Memory efficient logging patterns
    """
    
    def __init__(self, scraper_name: str, logger: Optional[logging.Logger] = None):
        """
        Initialize unified logger
        
        Args:
            scraper_name: Name of the scraper (e.g., 'SteamListing', 'SteamID')
            logger: Optional existing logger, creates new one if None
        """
        self.scraper_name = scraper_name
        self.logger = logger or logging.getLogger(scraper_name)
        
        # Batch tracking
        self.batch_start_time = None
        self.current_batch = 0
        self.total_batches = 0
        self.successful_batches = 0
        
        # Performance tracking
        self.session_start_time = time.time()
        self.request_count = 0
        self.connection_errors = 0
        self.consecutive_errors = 0
        
        # Progress logging intervals
        self.progress_intervals = [1, 10, 25, 50, 100]  # Log at these intervals
    
    def log_initialization(self, config: Dict[str, Any], proxy_stats: Optional[Dict] = None):
        """
        Log scraper initialization with system and proxy info
        
        Args:
            config: System configuration dictionary
            proxy_stats: Optional proxy manager statistics
        """
        self.logger.info(f"{self.scraper_name} scraper initialized")
        
        if 'system_info' in config:
            system_info = config['system_info']
            self.logger.info(f"System detected: {system_info.get('system_type', 'Unknown')}")
            self.logger.info(f"WSL2 optimized: {'[YES]' if system_info.get('is_wsl2', False) else '[NO]'}")
            
            if 'cpu_cores' in system_info:
                self.logger.info(f"CPU cores: {system_info['cpu_cores']}")
            if 'available_memory_gb' in system_info:
                self.logger.info(f"Available memory: {system_info['available_memory_gb']:.1f}GB")
        
        if 'max_workers' in config:
            self.logger.info(f"Max workers: {config['max_workers']}")
        
        if 'request_delay' in config:
            self.logger.info(f"Request delay: {config['request_delay']}s")
            
        self._log_proxy_initialization(proxy_stats)
    
    def _log_proxy_initialization(self, proxy_stats: Optional[Dict]):
        """Log proxy manager initialization"""
        if not proxy_stats:
            return
            
        proxy_count = proxy_stats.get('proxy_count', 0)
        if proxy_count > 0:
            region = proxy_stats.get('current_region', 'unknown').upper()
            self.logger.info(f"🌍 Loaded {proxy_count} proxies from {region} region")
            
            # Handle both single pool and multi-pool stats
            if 'pools' in proxy_stats:
                # Multi-pool system (steam_listing)
                active_regions = [pool['region'] for pool in proxy_stats['pools'].values() if pool['active']]
                total_proxies = sum(pool['proxy_count'] for pool in proxy_stats['pools'].values())
                self.logger.info(f"🚀 Multi-pool system: {len(active_regions)} active regions, {total_proxies} total proxies")
                self.logger.info(f"🎯 Active regions: {', '.join([r.upper() for r in active_regions])}")
            
            # Auto-detected IP
            whitelist_ip = proxy_stats.get('whitelist_ip', [])
            if whitelist_ip:
                self.logger.info(f"🎯 Auto-detected IP: {whitelist_ip[0]}")
        else:
            self.logger.warning("⚠️ No proxies loaded")
    
    def start_batch_processing(self, total_items: int, batch_size: int = None, max_workers: int = None):
        """
        Initialize batch processing logging
        
        Args:
            total_items: Total number of items to process
            batch_size: Size of each batch (optional)
            max_workers: Number of workers (optional)
        """
        self.batch_start_time = time.time()
        self.current_batch = 0
        self.successful_batches = 0
        
        if batch_size:
            self.total_batches = (total_items + batch_size - 1) // batch_size
            self.logger.info(f"📊 BATCH PROCESSING: {self.total_batches} batches, {total_items} total items")
        else:
            self.total_batches = total_items
            self.logger.info(f"📊 CONCURRENT PROCESSING: {total_items} items")
        
        if max_workers:
            self.logger.info(f"⚙️ Using {max_workers} workers")
        
        if batch_size:
            self.logger.info(f"⚡ Batch size: {batch_size}")
    
    def log_batch_progress(self, completed: int, successful: int, extra_info: Optional[Dict] = None):
        """
        Log batch processing progress with detailed statistics
        
        Args:
            completed: Number of completed batches/items
            successful: Number of successful batches/items  
            extra_info: Optional extra information (proxy stats, etc.)
        """
        self.current_batch = completed
        self.successful_batches = successful
        
        # Log at specific intervals for optimal performance
        should_log = (
            completed in self.progress_intervals or
            completed % 50 == 0 or
            completed == self.total_batches
        )
        
        if not should_log:
            return
        
        # Calculate metrics
        progress = (completed / self.total_batches) * 100 if self.total_batches > 0 else 0
        success_rate = (successful / completed) * 100 if completed > 0 else 0
        
        # Time calculations
        elapsed = time.time() - self.batch_start_time if self.batch_start_time else 0
        rate = completed / (elapsed / 60) if elapsed > 0 else 0  # per minute
        eta = (self.total_batches - completed) / (rate / 60) if rate > 0 else 0  # in minutes
        
        # Build log message
        log_parts = [
            f"📈 Progress: {completed}/{self.total_batches} ({progress:.1f}%)",
            f"✅ Success: {success_rate:.1f}%",
            f"⚡ Rate: {rate:.1f}/min"
        ]
        
        if eta > 0 and completed < self.total_batches:
            log_parts.append(f"⏱️ ETA: {eta:.1f}min")
        
        # Add extra info
        if extra_info:
            if 'active_pools' in extra_info:
                log_parts.append(f"🌍 Pools: {extra_info['active_pools']}")
            if 'proxy_region' in extra_info:
                log_parts.append(f"📍 Region: {extra_info['proxy_region'].upper()}")
        
        self.logger.info(" | ".join(log_parts))
    
    def log_completion(self, total_items: int, successful_items: int, extra_stats: Optional[Dict] = None):
        """
        Log processing completion with final statistics
        
        Args:
            total_items: Total items processed
            successful_items: Successfully processed items
            extra_stats: Optional additional statistics
        """
        success_rate = (successful_items / total_items) * 100 if total_items > 0 else 0
        elapsed = time.time() - self.session_start_time
        
        self.logger.info("="*60)
        self.logger.info(f"🏁 {self.scraper_name.upper()} PROCESSING COMPLETED")
        self.logger.info("="*60)
        self.logger.info(f"📊 Results: {successful_items}/{total_items} successful ({success_rate:.1f}%)")
        self.logger.info(f"⏱️ Total time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
        
        if self.request_count > 0:
            self.logger.info(f"🌐 Total requests: {self.request_count}")
            
        if extra_stats:
            for key, value in extra_stats.items():
                self.logger.info(f"📈 {key}: {value}")
    
    def log_error(self, error_msg: str, item_name: str = None, attempt: int = None):
        """
        Log errors with consistent formatting
        
        Args:
            error_msg: Error message
            item_name: Optional item name that caused error
            attempt: Optional attempt number
        """
        self.connection_errors += 1
        self.consecutive_errors += 1
        
        error_parts = ["❌ Error"]
        if item_name:
            error_parts.append(f"({item_name})")
        if attempt:
            error_parts.append(f"[Attempt {attempt}]")
        error_parts.append(f": {error_msg}")
        
        self.logger.error(" ".join(error_parts))
    
    def log_retry(self, delay: float, attempt: int, max_attempts: int, context: str = ""):
        """
        Log retry attempts with backoff information
        
        Args:
            delay: Delay before retry in seconds
            attempt: Current attempt number
            max_attempts: Maximum number of attempts
            context: Optional context string
        """
        context_str = f" ({context})" if context else ""
        self.logger.warning(f"⏳ Retry {attempt}/{max_attempts} in {delay:.1f}s{context_str}")
    
    def log_performance_report(self, proxy_stats: Optional[Dict] = None):
        """
        Generate comprehensive performance report
        
        Args:
            proxy_stats: Optional proxy manager statistics  
        """
        session_duration = time.time() - self.session_start_time
        
        self.logger.info("\\n" + "="*60)
        self.logger.info(f"🎯 {self.scraper_name.upper()} PERFORMANCE REPORT")
        self.logger.info("="*60)
        self.logger.info(f"⏱️ Session duration: {session_duration:.1f}s ({session_duration/60:.1f} minutes)")
        self.logger.info(f"🌐 Total requests: {self.request_count}")
        self.logger.info(f"❌ Connection errors: {self.connection_errors}")
        
        if self.total_batches > 0:
            self.logger.info(f"📊 Batches: {self.current_batch}/{self.total_batches}")
            
        self._log_proxy_performance(proxy_stats)
        self.logger.info("="*60)
    
    def _log_proxy_performance(self, proxy_stats: Optional[Dict]):
        """Log detailed proxy performance analysis"""
        if not proxy_stats:
            return
            
        self.logger.info("\\n🏊 PROXY PERFORMANCE ANALYSIS:")
        self.logger.info("-" * 40)
        
        # Handle multi-pool systems
        if 'pools' in proxy_stats:
            pool_scores = []
            for pool_name, pool_data in proxy_stats['pools'].items():
                total_requests = pool_data['success_count'] + pool_data['error_count']
                
                if total_requests > 0:
                    success_rate = (pool_data['success_count'] / total_requests) * 100
                    score = success_rate - (pool_data['consecutive_errors'] * 15)
                    pool_scores.append((pool_name, pool_data['region'], score, success_rate, pool_data))
                else:
                    pool_scores.append((pool_name, pool_data['region'], 0, 0, pool_data))
            
            # Sort pools by score
            pool_scores.sort(key=lambda x: x[2], reverse=True)
            
            for i, (pool_name, region, score, success_rate, pool_data) in enumerate(pool_scores, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                total_requests = pool_data['success_count'] + pool_data['error_count']
                
                self.logger.info(
                    f"{medal} {pool_name.upper()} ({region.upper()}): "
                    f"Score={score:.1f} | Success={success_rate:.1f}% | "
                    f"Requests={total_requests} | Proxies={pool_data['proxy_count']}"
                )
        else:
            # Single pool system
            region = proxy_stats.get('current_region', 'unknown').upper()
            proxy_count = proxy_stats.get('proxy_count', 0)
            errors = proxy_stats.get('consecutive_errors', 0)
            self.logger.info(f"📍 Region: {region} | Proxies: {proxy_count} | Errors: {errors}")
    
    def increment_request_count(self):
        """Increment request counter"""
        self.request_count += 1
    
    def reset_consecutive_errors(self):
        """Reset consecutive error counter on success"""
        if self.consecutive_errors > 0:
            self.consecutive_errors = max(0, self.consecutive_errors - 1)
    
    def log_info(self, message: str):
        """Log info message with consistent formatting"""
        self.logger.info(message)
    
    def log_warning(self, message: str):
        """Log warning message with consistent formatting"""
        self.logger.warning(message)
    
    def log_debug(self, message: str):
        """Log debug message with consistent formatting"""
        self.logger.debug(message)


# Convenience functions for quick usage
def create_logger(scraper_name: str, logger: Optional[logging.Logger] = None) -> UnifiedLogger:
    """
    Create a unified logger instance
    
    Args:
        scraper_name: Name of the scraper
        logger: Optional existing logger
        
    Returns:
        UnifiedLogger instance
    """
    return UnifiedLogger(scraper_name, logger)


def log_scraper_start(unified_logger: UnifiedLogger, scraper_type: str):
    """
    Log scraper startup message
    
    Args:
        unified_logger: UnifiedLogger instance
        scraper_type: Type of scraper ('batch' or 'concurrent')
    """
    unified_logger.log_info(f"🚀 Starting {scraper_type} processing with unified logging")