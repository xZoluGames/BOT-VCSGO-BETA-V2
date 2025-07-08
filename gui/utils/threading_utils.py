# Threading Utilities for GUI

import threading
from concurrent.futures import ThreadPoolExecutor
import queue
import time
import threading
from typing import Callable, Any
class ThreadManager:
    def __init__(self, max_workers=10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_tasks = {}
        self.results_queue = queue.Queue()
    
    def submit_task(self, task_id, func, *args, **kwargs):
        """Submit a task to the thread pool"""
        future = self.executor.submit(func, *args, **kwargs)
        self.active_tasks[task_id] = future
        return future
    
    def get_task_result(self, task_id, timeout=None):
        """Get result from a specific task"""
        if task_id in self.active_tasks:
            try:
                return self.active_tasks[task_id].result(timeout=timeout)
            except Exception as e:
                print(f"Task {task_id} failed: {e}")
                return None
        return None
    
    def cancel_task(self, task_id):
        """Cancel a specific task"""
        if task_id in self.active_tasks:
            cancelled = self.active_tasks[task_id].cancel()
            if cancelled:
                del self.active_tasks[task_id]
            return cancelled
        return False
    
    def shutdown(self, wait=True):
        """Shutdown the thread pool"""
        self.executor.shutdown(wait=wait)

class ThreadSafeUpdater:
    """Utility for thread-safe GUI updates"""
    
    @staticmethod
    def update_widget(widget, method, *args, **kwargs):
        """Update widget in a thread-safe manner"""
        if hasattr(widget, 'after'):
            widget.after(0, lambda: getattr(widget, method)(*args, **kwargs))
    
    @staticmethod
    def update_text(widget, text):
        """Update widget text safely"""
        if hasattr(widget, 'after') and hasattr(widget, 'configure'):
            widget.after(0, lambda: widget.configure(text=text))
    
    @staticmethod
    def update_progress(progressbar, value):
        """Update progress bar safely"""
        if hasattr(progressbar, 'after') and hasattr(progressbar, 'set'):
            progressbar.after(0, lambda: progressbar.set(value))
    
    @staticmethod
    def schedule_callback(widget, callback, delay=0):
        """Schedule a callback to run in the main thread"""
        if hasattr(widget, 'after'):
            widget.after(delay, callback)

class BackgroundTask:
    """Wrapper for background tasks with progress tracking"""
    
    def __init__(self, func, callback=None, error_callback=None):
        self.func = func
        self.callback = callback
        self.error_callback = error_callback
        self.thread = None
        self.result = None
        self.error = None
        self.finished = False
        self.cancelled = False
    
    def start(self, *args, **kwargs):
        """Start the background task"""
        self.thread = threading.Thread(
            target=self._run_task,
            args=args,
            kwargs=kwargs,
            daemon=True
        )
        self.thread.start()
    
    def _run_task(self, *args, **kwargs):
        """Internal method to run the task"""
        try:
            if not self.cancelled:
                self.result = self.func(*args, **kwargs)
                
            if self.callback and not self.cancelled:
                self.callback(self.result)
                
        except Exception as e:
            self.error = e
            if self.error_callback:
                self.error_callback(e)
        finally:
            self.finished = True
    
    def cancel(self):
        """Cancel the task"""
        self.cancelled = True
    
    def is_finished(self):
        """Check if task is finished"""
        return self.finished
    
    def join(self, timeout=None):
        """Wait for task to complete"""
        if self.thread:
            self.thread.join(timeout)

def run_in_background(widget, task: Callable, on_success: Callable = None, on_error: Callable = None):
    """Run a task in background thread and handle results"""
    def worker():
        try:
            result = task()
            if on_success and widget.winfo_exists():
                widget.after(0, on_success, result)
        except Exception as e:
            if on_error and widget.winfo_exists():
                widget.after(0, on_error, str(e))
    
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

