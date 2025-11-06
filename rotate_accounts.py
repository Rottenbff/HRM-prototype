#!/usr/bin/env python3
"""
Account Rotation Tracker
Tracks progress across multiple accounts and helps coordinate handoffs
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Configuration
TRACKER_FILE = "multi_account_tracker.json"
SYNC_DIR = os.environ.get("SYNC_DIR", "./sync")

class MultiAccountTracker:
    def __init__(self, tracker_file: str = TRACKER_FILE):
        self.tracker_file = tracker_file
        self.data = self.load_tracker()

    def load_tracker(self) -> Dict:
        """Load tracker data from file"""
        if os.path.exists(self.tracker_file):
            with open(self.tracker_file, 'r') as f:
                return json.load(f)
        return {
            "project": "sudoku_pretrain_multiaccount",
            "total_target_steps": 50000,
            "accounts": {},
            "last_update": None,
            "current_step": 0,
            "sessions": []
        }

    def save_tracker(self):
        """Save tracker data to file"""
        with open(self.tracker_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def register_account(self, account_id: str, account_name: str = ""):
        """Register a new account"""
        if account_id not in self.data["accounts"]:
            self.data["accounts"][account_id] = {
                "name": account_name or account_id,
                "total_steps": 0,
                "sessions": [],
                "last_active": None,
                "status": "ready"
            }
            self.save_tracker()
            print(f"✓ Registered account: {account_id}")

    def log_session(self, account_id: str, start_step: int, end_step: int, start_time: str, end_time: str):
        """Log a training session"""
        if account_id not in self.data["accounts"]:
            self.register_account(account_id)

        steps_trained = end_step - start_step

        session_info = {
            "start_step": start_step,
            "end_step": end_step,
            "steps_trained": steps_trained,
            "start_time": start_time,
            "end_time": end_time,
            "duration": (datetime.fromisoformat(end_time) - datetime.fromisoformat(start_time)).total_seconds()
        }

        # Update account data
        account = self.data["accounts"][account_id]
        account["sessions"].append(session_info)
        account["total_steps"] += steps_trained
        account["last_active"] = end_time
        account["status"] = "just_finished"

        # Update global progress
        self.data["current_step"] = end_step
        self.data["last_update"] = end_time

        # Add to session history
        self.data["sessions"].append({
            "account_id": account_id,
            **session_info
        })

        self.save_tracker()

        # Print progress report
        progress_pct = (end_step / self.data["total_target_steps"]) * 100
        print(f"\n{'='*60}")
        print(f"Account: {account_id}")
        print(f"Steps trained this session: {steps_trained:,}")
        print(f"Current total progress: {end_step:,}/{self.data['total_target_steps']:,} ({progress_pct:.1f}%)")
        print(f"Session duration: {session_info['duration']/3600:.1f} hours")
        print(f"Time per 1000 steps: {(session_info['duration']/steps_trained)*1000/3600:.2f} hours")
        print(f"{'='*60}\n")

    def get_status(self) -> Dict:
        """Get current status of all accounts"""
        status = {
            "total_progress": f"{self.data['current_step']:,}/{self.data['total_target_steps']:,} steps",
            "progress_pct": (self.data['current_step'] / self.data['total_target_steps']) * 100,
            "last_update": self.data.get('last_update', 'Never'),
            "accounts": {}
        }

        for acc_id, acc_data in self.data["accounts"].items():
            status["accounts"][acc_id] = {
                "name": acc_data["name"],
                "total_steps": acc_data["total_steps"],
                "sessions": len(acc_data["sessions"]),
                "last_active": acc_data.get("last_active"),
                "status": acc_data.get("status", "ready")
            }

        return status

    def get_next_account(self) -> str:
        """Get the account with the least recent activity"""
        accounts = self.data["accounts"]

        if not accounts:
            return "account_1"

        # Find account with oldest last_active
        oldest_account = min(accounts.items(),
                           key=lambda x: x[1].get("last_active") or "1970-01-01")
        return oldest_account[0]

    def get_progress_report(self) -> str:
        """Generate a progress report"""
        status = self.get_status()
        report = f"""
╔════════════════════════════════════════════════════════════╗
║           MULTI-ACCOUNT TRAINING PROGRESS REPORT           ║
╠════════════════════════════════════════════════════════════╣
║                                                            ║
║  Total Progress: {status['progress_pct']:>6.1f}% ({status['total_progress']})           ║
║                                                            ║
║  Last Update: {status['last_update']}                      ║
║                                                            ║
║  Accounts Status:                                         ║
║  {'─'*58} ║
"""
        for acc_id, acc_info in status["accounts"].items():
            report += f"║  {acc_info['name']:<15} | "
            report += f"Steps: {acc_info['total_steps']:>8,} | "
            report += f"Sessions: {acc_info['sessions']:>3} | "
            report += f"{acc_info['status']:<12} ║\n"

        report += "╚════════════════════════════════════════════════════════════╝\n"

        return report

def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python rotate_accounts.py register <account_id> [name]")
        print("  python rotate_accounts.py log <account_id> <start_step> <end_step>")
        print("  python rotate_accounts.py status")
        print("  python rotate_accounts.py next_account")
        print("  python rotate_accounts.py report")
        sys.exit(1)

    tracker = MultiAccountTracker()

    command = sys.argv[1]

    if command == "register":
        if len(sys.argv) < 3:
            print("Error: Need account_id")
            sys.exit(1)
        account_id = sys.argv[2]
        account_name = sys.argv[3] if len(sys.argv) > 3 else ""
        tracker.register_account(account_id, account_name)
        print(f"✓ Registered {account_id}")

    elif command == "log":
        if len(sys.argv) < 5:
            print("Error: Need account_id, start_step, end_step")
            sys.exit(1)
        account_id = sys.argv[2]
        start_step = int(sys.argv[3])
        end_step = int(sys.argv[4])

        start_time = datetime.fromtimestamp(time.time() - 3600).isoformat()  # Assume 1 hour session
        end_time = datetime.now().isoformat()

        tracker.log_session(account_id, start_step, end_step, start_time, end_time)

    elif command == "status":
        status = tracker.get_status()
        print(json.dumps(status, indent=2))

    elif command == "report":
        print(tracker.get_progress_report())

    elif command == "next_account":
        next_acc = tracker.get_next_account()
        print(next_acc)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
