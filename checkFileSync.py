import os
import hashlib
import shutil
from datetime import datetime

LOG_FILE = "sync_log.txt"

def log(message):
    """Log message to console and log file with timestamp."""
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    entry = f"{timestamp} {message}"
    print(entry)
    with open(LOG_FILE, 'a') as f:
        f.write(entry + "\n")

def compute_checksum(file_path, algo='sha256'):
    """Compute SHA-256 checksum of a file."""
    hash_func = hashlib.new(algo)
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash_func.update(chunk)
    return hash_func.hexdigest()

def get_all_files(directory):
    """Get all file paths in the directory (recursive)."""
    file_paths = []
    for root, _, files in os.walk(directory):
        for file in files:
            abs_path = os.path.join(root, file)
            rel_path = os.path.relpath(abs_path, directory)
            file_paths.append(rel_path)
    return file_paths

def verify_and_sync(source_dir, target_dir, sync_missing=False, overwrite_mismatched=False):
    """Ensure all files in source_dir exist in target_dir with matching checksums."""
    log(f"Started verification from '{source_dir}' to '{target_dir}'")
    source_files = get_all_files(source_dir)
    missing_files = []
    mismatched_files = []

    for rel_path in source_files:
        src_file = os.path.join(source_dir, rel_path)
        tgt_file = os.path.join(target_dir, rel_path)

        if not os.path.exists(tgt_file):
            log(f"[MISSING] {rel_path}")
            missing_files.append(rel_path)
            if sync_missing:
                os.makedirs(os.path.dirname(tgt_file), exist_ok=True)
                shutil.copy2(src_file, tgt_file)
                log(f"  → Copied missing file to target.")
            continue

        src_checksum = compute_checksum(src_file)
        tgt_checksum = compute_checksum(tgt_file)

        if src_checksum != tgt_checksum:
            log(f"[MISMATCH] {rel_path}")
            mismatched_files.append(rel_path)
            if overwrite_mismatched:
                shutil.copy2(src_file, tgt_file)
                log(f"  → Overwrote mismatched file in target.")

    log("\nSummary:")
    log(f"  Total files checked: {len(source_files)}")
    log(f"  Missing files: {len(missing_files)}")
    log(f"  Mismatched files: {len(mismatched_files)}")

    if not missing_files and not mismatched_files:
        log("✅ All files are present and match by checksum.")
    log("-" * 60)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Verify file integrity between two directories using checksums.")
    parser.add_argument("source", help="Path to source directory")
    parser.add_argument("target", help="Path to target directory")
    parser.add_argument("--sync", action="store_true", help="Copy missing files from source to target")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite mismatched files in target")

    args = parser.parse_args()

    verify_and_sync(args.source, args.target, args.sync, args.overwrite)