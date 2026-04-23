#!/usr/bin/env python3
"""
GoFile Link Keeper - Keeps GoFile links active by periodically downloading them

This script prevents GoFile's 10-day inactivity deletion by making small
download requests to each file, registering activity without consuming bandwidth.
"""

import os
import sys
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_API_KEY = os.getenv('SUPABASE_API_KEY')
BATCH_SIZE = int(os.getenv('BATCH_SIZE', '100'))  # Process 100 links per run
DELAY_BETWEEN_REQUESTS = float(os.getenv('DELAY_BETWEEN_REQUESTS', '2'))  # 2 seconds
MIN_KEEP_INTERVAL_DAYS = float(os.getenv('MIN_KEEP_INTERVAL_DAYS', '5'))  # Don't re-keep if kept in last 5 days
PRIORITY_MODE = os.getenv('PRIORITY_MODE', 'normal')  # Priority mode for adaptive processing
AGE_FILTER_DAYS = int(os.getenv('AGE_FILTER_DAYS', '0'))  # Filter files by upload age (0 = all files)
EXECUTION_MODE = os.getenv('EXECUTION_MODE', 'auto')  # Execution mode for logging

# Validate environment variables
if not SUPABASE_URL or not SUPABASE_API_KEY:
    logger.error("❌ Missing required environment variables: SUPABASE_URL and SUPABASE_API_KEY")
    sys.exit(1)


class SupabaseClient:
    """Simple Supabase client for REST API operations"""
    
    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'apikey': api_key,
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
    
    def get_active_links(self, limit: int = 100) -> List[Dict]:
        """Fetch active GoFile links that need keeping alive with smart filtering"""
        endpoint = f"{self.url}/rest/v1/gofile_uploads"
        
        # Calculate cutoff date based on keep interval
        cutoff_hours = MIN_KEEP_INTERVAL_DAYS * 24
        cutoff_date = (datetime.utcnow() - timedelta(hours=cutoff_hours)).isoformat()
        
        # Base query parameters
        params = {
            'select': 'id,streamer_name,gofile_link,upload_date,last_kept,keep_alive_count,status',
            'order': 'last_kept.asc.nullsfirst,upload_date.desc',  # Prioritize never-kept, then newest
            'limit': str(limit)
        }
        
        # Build filters based on priority mode and settings
        filters = []
        
        # Status filter - only active links
        filters.append('(status.eq.active,status.is.null)')
        
        # Keep interval filter (unless processing all)
        if MIN_KEEP_INTERVAL_DAYS > 0:
            filters.append(f'(last_kept.is.null,last_kept.lt.{cutoff_date})')
        
        # Age filter based on upload date
        if AGE_FILTER_DAYS > 0:
            age_cutoff = (datetime.utcnow() - timedelta(days=AGE_FILTER_DAYS)).isoformat()
            filters.append(f'upload_date.gte.{age_cutoff}')
        
        # Priority-specific filters
        if PRIORITY_MODE == 'critical':
            # Only files uploaded in last 24 hours that haven't been kept in 2 hours
            recent_cutoff = (datetime.utcnow() - timedelta(days=1)).isoformat()
            filters.append(f'upload_date.gte.{recent_cutoff}')
        elif PRIORITY_MODE == 'important':
            # Files uploaded in last week that haven't been kept in 6 hours
            week_cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
            filters.append(f'upload_date.gte.{week_cutoff}')
        elif PRIORITY_MODE == 'retry':
            # Only files that failed recently - prioritize never-kept files
            filters.append('(last_kept.is.null,keep_alive_count.lt.3)')
        elif PRIORITY_MODE == 'test':
            # Limit to small set for testing
            params['limit'] = '5'
        
        # Apply filters using 'and' logic
        if len(filters) > 1:
            params['and'] = ','.join([f'({f})' for f in filters])
        elif len(filters) == 1:
            params['or'] = filters[0]
        
        try:
            logger.info(f"🔍 Querying Supabase with filters: {PRIORITY_MODE} mode, {AGE_FILTER_DAYS}d age limit")
            response = requests.get(endpoint, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            
            links = response.json()
            logger.info(f"📋 Found {len(links)} links matching criteria")
            
            return links
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to fetch links from Supabase: {e}")
            logger.error(f"   Query params: {params}")
            return []
    
    def update_keep_status(self, record_id: int, success: bool, error_msg: Optional[str] = None):
        """Update the keep-alive status of a record"""
        endpoint = f"{self.url}/rest/v1/gofile_uploads"
        
        update_data = {}
        
        if success:
            update_data = {
                'last_kept': datetime.utcnow().isoformat(),
                'status': 'active'
            }
        else:
            update_data = {
                'status': 'failed'
            }
        
        params = {'id': f'eq.{record_id}'}
        
        try:
            response = requests.patch(endpoint, headers=self.headers, params=params, json=update_data, timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️  Failed to update record {record_id}: {e}")
    
    def mark_as_deleted(self, record_id: int):
        """Mark a record as deleted (for 404 errors)"""
        endpoint = f"{self.url}/rest/v1/gofile_uploads"
        
        update_data = {
            'status': 'deleted'
        }
        
        params = {'id': f'eq.{record_id}'}
        
        try:
            response = requests.patch(endpoint, headers=self.headers, params=params, json=update_data, timeout=30)
            response.raise_for_status()
            logger.info(f"  🗑️  Marked record {record_id} as deleted")
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️  Failed to mark record {record_id} as deleted: {e}")


class GoFileKeeper:
    """Keeps GoFile links alive by making minimal download requests with smart error handling"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        # Add retry strategy
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'rate_limited': 0,
            'already_deleted': 0,
            'network_errors': 0
        }
        self.failed_links = []  # Track failed links for reporting
    
    def keep_alive(self, link: str) -> tuple[bool, Optional[str]]:
        """
        Keep a GoFile link alive by downloading first 1KB with smart error handling
        Returns: (success, error_message)
        """
        try:
            # First, check if link is still valid with HEAD request
            head_response = self.session.head(link, timeout=15, allow_redirects=True)
            
            # Handle different status codes intelligently
            if head_response.status_code == 404:
                self.stats['already_deleted'] += 1
                return False, "File deleted (404) - marking as deleted"
            elif head_response.status_code == 429:
                self.stats['rate_limited'] += 1
                # Wait longer for rate limiting
                time.sleep(30)
                return False, "Rate limited (429) - will retry later"
            elif head_response.status_code >= 500:
                return False, f"Server error ({head_response.status_code}) - GoFile may be down"
            elif head_response.status_code >= 400:
                return False, f"Client error ({head_response.status_code})"
            
            # Download first 1KB to register activity
            headers = {'Range': 'bytes=0-1023'}  # First 1KB
            response = self.session.get(link, headers=headers, timeout=30, stream=True)
            
            if response.status_code in [200, 206]:  # 200 OK or 206 Partial Content
                # Read and discard the data (just to complete the request)
                chunk_count = 0
                for chunk in response.iter_content(chunk_size=1024):
                    chunk_count += 1
                    if chunk_count >= 1:  # Only read first chunk
                        break
                
                # Verify we got some data
                if chunk_count > 0:
                    return True, None
                else:
                    return False, "No data received"
            elif response.status_code == 429:
                self.stats['rate_limited'] += 1
                time.sleep(30)
                return False, "Rate limited during download"
            else:
                return False, f"Download failed ({response.status_code})"
                
        except requests.exceptions.Timeout:
            self.stats['network_errors'] += 1
            return False, "Request timeout"
        except requests.exceptions.ConnectionError:
            self.stats['network_errors'] += 1
            return False, "Connection error"
        except requests.exceptions.RequestException as e:
            self.stats['network_errors'] += 1
            return False, f"Network error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def process_links(self, links: List[Dict]):
        """Process a batch of links with smart error handling and adaptive delays"""
        self.stats['total'] = len(links)
        
        if not links:
            logger.info("✨ No links to process")
            return
        
        logger.info(f"🔄 Processing {len(links)} links in {PRIORITY_MODE} mode...")
        
        # Adaptive delay based on mode
        base_delay = DELAY_BETWEEN_REQUESTS
        consecutive_failures = 0
        
        for idx, record in enumerate(links, 1):
            link = record.get('gofile_link')
            record_id = record.get('id')
            streamer = record.get('streamer_name', 'unknown')
            last_kept = record.get('last_kept')
            keep_count = record.get('keep_alive_count', 0)
            
            if not link or not record_id:
                logger.warning(f"⚠️  [{idx}/{len(links)}] Skipping invalid record: {record}")
                self.stats['skipped'] += 1
                continue
            
            # Show progress with context
            age_info = ""
            if last_kept:
                try:
                    last_kept_dt = datetime.fromisoformat(last_kept.replace('Z', '+00:00'))
                    hours_ago = (datetime.utcnow().replace(tzinfo=last_kept_dt.tzinfo) - last_kept_dt).total_seconds() / 3600
                    age_info = f" (last kept {hours_ago:.1f}h ago)"
                except:
                    age_info = f" (kept {keep_count}x)"
            else:
                age_info = " (never kept)"
            
            logger.info(f"[{idx}/{len(links)}] {streamer}{age_info}")
            logger.info(f"  🔗 {link[:60]}{'...' if len(link) > 60 else ''}")
            
            success, error = self.keep_alive(link)
            
            if success:
                logger.info(f"  ✅ Kept alive successfully")
                self.stats['success'] += 1
                consecutive_failures = 0
            else:
                logger.warning(f"  ❌ Failed: {error}")
                self.stats['failed'] += 1
                self.failed_links.append({
                    'streamer': streamer,
                    'link': link[:50] + '...',
                    'error': error
                })
                consecutive_failures += 1
            
            # Update database with enhanced error handling
            try:
                supabase = SupabaseClient(SUPABASE_URL, SUPABASE_API_KEY)
                if success:
                    supabase.update_keep_status(record_id, True)
                elif "deleted" in error.lower() or "404" in error:
                    # Mark as deleted instead of failed for 404s
                    supabase.mark_as_deleted(record_id)
                else:
                    supabase.update_keep_status(record_id, False, error)
            except Exception as db_error:
                logger.warning(f"  ⚠️  Database update failed: {db_error}")
            
            # Adaptive delay based on failures and rate limiting
            if idx < len(links):  # Don't delay after last item
                current_delay = base_delay
                
                # Increase delay if we're getting rate limited
                if consecutive_failures > 2:
                    current_delay *= 2
                    logger.info(f"  ⏳ Increased delay to {current_delay}s due to failures")
                
                # Add extra delay for rate limiting
                if "rate limit" in error.lower() if error else False:
                    current_delay += 30
                    logger.info(f"  🚦 Rate limit detected, waiting {current_delay}s")
                
                # Random jitter to prevent synchronized requests
                jitter = current_delay * 0.1 * (0.5 - time.time() % 1)
                total_delay = current_delay + jitter
                
                if total_delay > 0:
                    time.sleep(total_delay)
    
    def print_summary(self):
        """Print comprehensive execution summary"""
        logger.info("\n" + "="*70)
        logger.info("📊 SMART KEEPER EXECUTION SUMMARY")
        logger.info("="*70)
        logger.info(f"Execution Mode: {EXECUTION_MODE}")
        logger.info(f"Priority Mode: {PRIORITY_MODE}")
        logger.info(f"Age Filter: {AGE_FILTER_DAYS} days" if AGE_FILTER_DAYS > 0 else "Age Filter: All files")
        logger.info(f"Keep Interval: {MIN_KEEP_INTERVAL_DAYS} days")
        logger.info("")
        logger.info(f"📈 RESULTS:")
        logger.info(f"Total links processed: {self.stats['total']}")
        logger.info(f"✅ Successfully kept alive: {self.stats['success']}")
        logger.info(f"❌ Failed: {self.stats['failed']}")
        logger.info(f"⏭️  Skipped (invalid): {self.stats['skipped']}")
        logger.info(f"🗑️  Already deleted: {self.stats['already_deleted']}")
        logger.info(f"🚦 Rate limited: {self.stats['rate_limited']}")
        logger.info(f"🌐 Network errors: {self.stats['network_errors']}")
        
        if self.stats['total'] > 0:
            success_rate = (self.stats['success'] / self.stats['total']) * 100
            logger.info(f"📊 Success rate: {success_rate:.1f}%")
            
            # Performance insights
            if success_rate >= 95:
                logger.info("🎉 Excellent performance!")
            elif success_rate >= 85:
                logger.info("👍 Good performance")
            elif success_rate >= 70:
                logger.info("⚠️  Moderate performance - check for issues")
            else:
                logger.info("🚨 Poor performance - investigation needed")
        
        # Show failed links summary
        if self.failed_links:
            logger.info(f"\n🔍 FAILED LINKS SUMMARY:")
            for i, failed in enumerate(self.failed_links[:5], 1):  # Show first 5
                logger.info(f"  {i}. {failed['streamer']}: {failed['error']}")
            if len(self.failed_links) > 5:
                logger.info(f"  ... and {len(self.failed_links) - 5} more")
        
        # Recommendations
        logger.info(f"\n💡 RECOMMENDATIONS:")
        if self.stats['rate_limited'] > 0:
            logger.info("  - Consider increasing DELAY_BETWEEN_REQUESTS")
        if self.stats['network_errors'] > self.stats['success']:
            logger.info("  - Check network connectivity and GoFile status")
        if self.stats['already_deleted'] > 0:
            logger.info(f"  - Clean up {self.stats['already_deleted']} deleted links from database")
        if self.stats['total'] == 0:
            logger.info("  - Check database filters and keep intervals")
        
        logger.info("="*70)


def main():
    """Main execution function"""
    logger.info("🚀 GoFile Link Keeper Started")
    logger.info(f"⚙️  Configuration:")
    logger.info(f"   - Execution mode: {EXECUTION_MODE}")
    logger.info(f"   - Priority mode: {PRIORITY_MODE}")
    logger.info(f"   - Batch size: {BATCH_SIZE}")
    logger.info(f"   - Delay between requests: {DELAY_BETWEEN_REQUESTS}s")
    logger.info(f"   - Min keep interval: {MIN_KEEP_INTERVAL_DAYS} days")
    logger.info(f"   - Age filter: {AGE_FILTER_DAYS} days" if AGE_FILTER_DAYS > 0 else "   - Age filter: All files")
    logger.info("")
    
    # Initialize clients
    supabase = SupabaseClient(SUPABASE_URL, SUPABASE_API_KEY)
    keeper = GoFileKeeper()
    
    # Fetch links that need keeping alive
    logger.info("📥 Fetching links from Supabase...")
    links = supabase.get_active_links(limit=BATCH_SIZE)
    
    if not links:
        logger.info("✨ No links need keeping alive at this time")
        return 0
    
    logger.info(f"📋 Found {len(links)} links to process\n")
    
    # Process the links
    keeper.process_links(links)
    
    # Print summary
    keeper.print_summary()
    
    # Exit with error code if too many failures
    if keeper.stats['failed'] > keeper.stats['success']:
        logger.error("⚠️  More failures than successes - check your GoFile links!")
        return 1
    
    logger.info("\n✅ GoFile Link Keeper Completed Successfully")
    return 0


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"💥 Unexpected error: {e}")
        sys.exit(1)
