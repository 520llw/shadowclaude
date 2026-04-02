"""
Example: KAIROS Jobs
Demonstrates scheduled jobs with KAIROS daemon.
"""

import datetime
import shadowclaude as sc
from shadowclaude.kairos import Job, Trigger


def backup_memories():
    """Task: Backup memory data."""
    timestamp = datetime.datetime.now().isoformat()
    print(f"[{timestamp}] Backing up memories...")
    # Backup logic here
    return {"status": "success", "files_backed_up": 10}


def cleanup_old_data():
    """Task: Clean up old temporary data."""
    timestamp = datetime.datetime.now().isoformat()
    print(f"[{timestamp}] Cleaning up old data...")
    # Cleanup logic here
    return {"status": "success", "items_removed": 5}


def health_check():
    """Task: System health check."""
    timestamp = datetime.datetime.now().isoformat()
    print(f"[{timestamp}] Running health check...")
    return {"status": "healthy", "checks_passed": 5}


def main():
    kairos = sc.Kairos()
    
    # Schedule daily backup at 2 AM
    backup_job = Job(
        name="daily_backup",
        trigger=Trigger.cron("0 2 * * *"),
        action=backup_memories
    )
    
    # Schedule cleanup every 6 hours
    cleanup_job = Job(
        name="cleanup_old",
        trigger=Trigger.interval(hours=6),
        action=cleanup_old_data
    )
    
    # Schedule health check every 30 minutes
    health_job = Job(
        name="health_check",
        trigger=Trigger.interval(minutes=30),
        action=health_check
    )
    
    # Register jobs
    kairos.schedule(backup_job)
    kairos.schedule(cleanup_job)
    kairos.schedule(health_job)
    
    print("=== KAIROS Scheduled Jobs ===")
    print(f"Registered {len(kairos.jobs)} jobs")
    
    for job in kairos.jobs:
        print(f"  - {job.name}: {job.trigger}")
    
    # Start daemon (would run in background in production)
    print("\nStarting KAIROS daemon...")
    # kairos.start()  # Uncomment to actually run


if __name__ == "__main__":
    main()
