from logging import Handler
from os import stat, remove, rename
from _thread import allocate_lock


rotating_file_handler_version = "v1.0~203c93f"


def rename_file_if_it_exists(old_file_full_name: str, new_file_full_name: str) -> None:
    try:
        rename(old_file_full_name, new_file_full_name)
    except OSError:
        pass


def remove_file_if_it_exists(file_full_name: str) -> None:
    try:
        remove(file_full_name)
    except OSError:
        pass


def get_file_size_in_bytes(file_full_name: str) -> int:
    return stat(file_full_name)[6]


class RotatingLogFileHandler(Handler):
    def __init__(self,
                 file_full_name: str,
                 max_file_size_in_bytes: int,
                 number_of_backup_files: int):
        super().__init__()
        self.file_full_name = file_full_name
        self.max_file_size_in_bytes = max_file_size_in_bytes
        self.number_of_backup_files = number_of_backup_files

        # The Micropython logging library is not thread-safe, therefore we need to handle thread safety ourselves.
        self.rotating_log_file_handler_lock = allocate_lock()
        self.current_log_file = open(self.file_full_name, "a")
        self.current_log_file_size_in_bytes = get_file_size_in_bytes(self.file_full_name)

    def should_rotation_happen(self, new_log_message_length: int) -> bool:
        return self.current_log_file_size_in_bytes + new_log_message_length > self.max_file_size_in_bytes

    def rotate_log_file(self):
        self.current_log_file.close()

        # remove the oldest backup file if it is there
        remove_file_if_it_exists(f"{self.file_full_name}.{self.number_of_backup_files}")

        # shift backup files
        for i in range(self.number_of_backup_files - 1, 0, -1):
            rename_file_if_it_exists(f"{self.file_full_name}.{i}", f"{self.file_full_name}.{i + 1}")

        # backup the current log file
        if self.number_of_backup_files > 0:
            rename(self.file_full_name, f"{self.file_full_name}.1")

        # create a new log file
        self.current_log_file = open(self.file_full_name, "w")
        self.current_log_file_size_in_bytes = 0

    def emit(self, record):
        if record.levelno < self.level:
            return

        log_message = f"{self.formatter.format(record)}\n"
        log_message_length = len(log_message)

        with self.rotating_log_file_handler_lock:
            if self.should_rotation_happen(log_message_length):
                self.rotate_log_file()
            self.current_log_file.write(log_message)
            self.current_log_file_size_in_bytes += log_message_length

    def close(self):
        with self.rotating_log_file_handler_lock:
            self.current_log_file.close()
        super().close()
