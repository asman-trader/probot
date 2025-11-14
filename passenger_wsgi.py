import os
import sys

# Ensure project root is on sys.path
BASE_DIR = os.path.dirname(__file__)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Import the Flask application from web_app module
from web_app import app, scheduler, restore_jobs

# Ensure one-time init in Passenger
_PASSENGER_INIT_DONE = globals().get("_PASSENGER_INIT_DONE", False)

# Ensure scheduler is running for Passenger
# Passenger may need explicit scheduler initialization
if (not _PASSENGER_INIT_DONE) and scheduler and not scheduler.running:
    try:
        scheduler.start()
        print("Scheduler started in Passenger mode")
    except Exception as e:
        print(f"Warning: Could not start scheduler in Passenger: {e}")
        # Scheduler might already be running from module import
        try:
            if hasattr(scheduler, 'state') and scheduler.state == 1:
                print("Scheduler already running")
        except:
            pass

# Restore jobs immediately after scheduler starts (for Passenger)
# This ensures jobs are restored even if threading doesn't work in Passenger
def restore_jobs_in_passenger():
    """Restore jobs in Passenger with proper error handling"""
    global _PASSENGER_INIT_DONE
    try:
        if _PASSENGER_INIT_DONE:
            return
        import time
        time.sleep(2)  # Wait 2 seconds for scheduler to be fully ready
        
        # Double check scheduler is running
        if not scheduler.running:
            print("Warning: Scheduler is not running, attempting to start...")
            try:
                scheduler.start()
                print("Scheduler started successfully in restore function")
                time.sleep(1)  # Wait another second after starting
            except Exception as e:
                print(f"Error starting scheduler in restore: {e}")
                return
        
        print("Attempting to restore jobs...")
        restore_jobs()
        print("Jobs restored in Passenger mode")
        _PASSENGER_INIT_DONE = True
        
        # Verify job was restored
        try:
            from web_app import curd, CHAT_ID
            job_id = curd.getJob(chatid=CHAT_ID)
            if job_id:
                job = scheduler.get_job(job_id)
                if job:
                    print(f"Job verified: {job_id} is scheduled. Next run: {job.next_run_time}")
                else:
                    print(f"Warning: Job {job_id} not found in scheduler after restore")
        except Exception as e:
            print(f"Warning: Could not verify restored job: {e}")
            
    except Exception as e:
        print(f"Warning: Could not restore jobs in Passenger: {e}")
        import traceback
        traceback.print_exc()

# Restore jobs
restore_jobs_in_passenger()

# Expose Flask application for Phusion Passenger
# Passenger expects 'application' variable
application = app

