from datetime import datetime, timedelta
from collections import Counter, defaultdict
import logging

class Login:
    def __init__(self, log_file):
        """
        Initialize the Login class with the log file path.

        Args:
        log_file (str): Path to the log file.
        """
        self.log_file = log_file

    def parse_log_file(self):
        """
        Parse the log file and return a list of login events.

        Each login event is a tuple containing timestamp, username, and login status.

        Returns:
        list: List of login events.
        """
        log_entries = []
        with open(self.log_file, 'r') as file:
            for line in file:
                parts = line.strip().split(' - ')
                if len(parts) == 4:  
                    log_time = datetime.strptime(parts[0], '%Y-%m-%d %H:%M:%S,%f')
                    user = parts[2]
                    status = parts[3].split()[1]  
                    log_entries.append((log_time, user, status))
        return log_entries

    def check_login_status(self, username, within_minutes=10, max_attempts=3):
        """
        Check the login status for a user.

        If the number of failed login attempts within the specified time does not exceed the maximum allowed, allow login.

        Args:
        username (str): Username.
        within_minutes (int): Time window in minutes.
        max_attempts (int): Maximum number of failed login attempts.

        Returns:
        bool: Returns True if allowed to login, False otherwise.
        """
        current_time = datetime.now()
        log_entries = self.parse_log_file()
        user_failed_logins = [entry for entry in log_entries if entry[1] == username 
                              and entry[2] == 'failed' 
                              and current_time - entry[0] <= timedelta(minutes=within_minutes)]
        failed_login_count = len(user_failed_logins)

        if failed_login_count >= max_attempts:
            return False  
        return True  

    def get_recent_failed_users(self, within_minutes=10):
        """
        Get a list of users who have failed to login recently within the specified time frame.

        Args:
        within_minutes (int): Time window in minutes.

        Returns:
        list[str]: List of usernames with failed login attempts.
        """
        current_time = datetime.now()
        log_entries = self.parse_log_file()

        recent_failed_logins = [
            entry[1]  
            for entry in log_entries
            if entry[2] == 'failed' and current_time - entry[0] <= timedelta(minutes=within_minutes)
        ]

        return list(set(recent_failed_logins))

    def remove_failed_logins_from_file(self, username):
        """
        Remove the last 100 failed login records for a user from the log file.

        Args:
        username (str): Username.
        """
        try:
            # Read the log file
            with open(self.log_file, 'r') as file:
                log_lines = file.readlines()

            # Remove the last 100 failed login records
            cleaned_log_lines = []
            failed_count = 0
            for line in reversed(log_lines):
                if failed_count >= 100:
                    break
                if username in line and "failed" in line:
                    failed_count += 1
                else:
                    cleaned_log_lines.append(line)

            # Write the cleaned log back to the file
            with open(self.log_file, 'w') as file:
                file.writelines(reversed(cleaned_log_lines))

            logging.info(f"Successfully removed the last 100 failed login records for user '{username}'.")
        
        except FileNotFoundError:
            logging.error(f"Error: Log file '{self.log_file}' not found.")
        except PermissionError:
            logging.error("Error: Permission denied to read or write log file.")
        except Exception as e:
            logging.error(f"An error occurred: {e}")

    def get_login_counts(self):
        """
        Get login statistics for the past 7 days and each user's login status.

        Returns:
        tuple: A tuple containing two elements. The first is a dictionary of daily login statistics (success and failure counts), and the second is a dictionary of each user's login statistics (success and failure counts).
        """
        try:
            log_entries = self.parse_log_file()

            today = datetime.now().date()
            start_date = today - timedelta(days=7)
            daily_stats = {}  
            user_stats = defaultdict(lambda: {'succeed': 0, 'failed': 0})

            for log_entry in log_entries:
                timestamp, username, status = log_entry
                date = timestamp.date()

                # Initialize daily stats if not present
                if date not in daily_stats:
                    daily_stats[date] = {'succeed': 0, 'failed': 0}

                # Update daily and user login stats
                if status == 'succeed':
                    daily_stats[date]['succeed'] += 1
                    user_stats[username]['succeed'] += 1
                elif status == 'failed':
                    daily_stats[date]['failed'] += 1
                    user_stats[username]['failed'] += 1

            # Ensure the returned data includes the past 7 days, even without login records
            recent_daily_stats = {}
            for offset in range(7):
                date = today - timedelta(days=offset)
                recent_daily_stats[date] = daily_stats.get(date, {'succeed': 0, 'failed': 0})
            
            # Sort recent daily login stats in descending order by date
            sorted_recent_daily_stats = dict(sorted(recent_daily_stats.items(), reverse=True))

            # Return the recent daily login stats and user login status
            return sorted_recent_daily_stats, dict(user_stats)
        
        except FileNotFoundError:
            logging.error(f"Error: Log file '{self.log_file}' not found.")
        except PermissionError:
            logging.error("Error: Permission denied to read or write log file.")
        except Exception as e:
            logging.error(f"An error occurred: {e}")