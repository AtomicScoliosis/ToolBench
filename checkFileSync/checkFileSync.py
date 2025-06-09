import os
import hashlib
import shutil
from datetime import datetime
from collections import defaultdict

LOG_FILE = "sync_log.txt"

def log(message):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    entry = f"{timestamp} {message}"
    print(entry)
    with open(LOG_FILE, 'a') as f:
        f.write(entry + "\n")

def compute_checksum(file_path, algo='sha256'):
    hash_func = hashlib.new(algo)
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash_func.update(chunk)
    return hash_func.hexdigest()

def get_all_files(directory):
    file_paths = []
    for root, _, files in os.walk(directory):
        for file in files:
            abs_path = os.path.join(root, file)
            file_paths.append(abs_path)
    print(file_paths)        
    return file_paths

def find_matching_file(src_checksum, src_filename, target_files):
    for tgt_file in target_files:
        if os.path.basename(tgt_file) == src_filename:
            try:
                tgt_checksum = compute_checksum(tgt_file)
                if tgt_checksum == src_checksum:
                    return tgt_file
            except Exception:
                continue
    return None

def detect_duplicates(file_paths):
    checksum_map = defaultdict(list)
    name_map = defaultdict(list)

    for file in file_paths:
        try:
            checksum = compute_checksum(file)
            checksum_map[checksum].append(file)
        except Exception as e:
            log(f"[ERROR] Could not read {file}: {e}")
        name_map[os.path.basename(file)].append(file)

    duplicate_checksums = {k: v for k, v in checksum_map.items() if len(v) > 1}
    duplicate_names = {k: v for k, v in name_map.items() if len(v) > 1}

    if duplicate_checksums:
        log("\n Duplicate Files by Checksum (Content):")
        for checksum, files in duplicate_checksums.items():
            log(f"  Checksum: {checksum}")
            for f in files:
                log(f"    :{f}")
    else:
        log(" No duplicate content files found in source.")

    if duplicate_names:
        log("\n Duplicate Files by Name:")
        for name, files in duplicate_names.items():
            log(f"  Filename: {name}")
            for f in files:
                log(f"    : {f}")
    else:
        log(" No duplicate filenames found in source.")

def verify_and_sync(source_dir, target_dir, sync_missing=False, overwrite_mismatched=False):
    log(f"Started verification from '{source_dir}' to '{target_dir}'")

    source_files = get_all_files(source_dir)
    target_files = get_all_files(target_dir)

    # Detect duplicates in source
    detect_duplicates(source_files)

    missing_files = []
    mismatched_files = []

    for src_file in source_files:
        rel_path = os.path.relpath(src_file, source_dir)
        full_path = os.path.abspath(os.path.join(source_dir,src_file))
        src_filename = os.path.basename(src_file)
        src_checksum = compute_checksum(src_file)

        match = find_matching_file(src_checksum, src_filename, target_files)

        if match:
            log(f"[OK] Found matching '{src_filename}' in target.")
            continue

        candidates = [f for f in target_files if os.path.basename(f) == src_filename]
        if candidates:
            log(f"[MISMATCH] {rel_path} (filename exists but no checksum match)")
            mismatched_files.append(rel_path)
            if overwrite_mismatched:
                tgt_path = os.path.join(target_dir, rel_path)
                os.makedirs(os.path.dirname(tgt_path), exist_ok=True)
                shutil.copy2(src_file, tgt_path)
                log(f"  → Overwrote file at '{tgt_path}'")
        else:
            log(f"[MISSING] {full_path}")
            missing_files.append(rel_path)
            if sync_missing:
                tgt_path = os.path.join(target_dir, rel_path)
                os.makedirs(os.path.dirname(tgt_path), exist_ok=True)
                shutil.copy2(src_file, tgt_path)
                log(f"  : Copied to '{tgt_path}'")

    log(f" Missing File List:\n {missing_files} \n")
    log(f" Mismatch File List:\n {mismatched_files} \n")
    log("\nSummary:")
    log(f"  Total source files checked: {len(source_files)}")
    log(f"  Missing files: {len(missing_files)}")
    log(f"  Mismatched files: {len(mismatched_files)}")
    if not missing_files and not mismatched_files:
        log(" All files accounted for and match by checksum.")
    log("-" * 60)

if __name__ == "__main__":
    import argparse
    import tkinter as tk
    from tkinter import filedialog

    logPath = os.path.abspath(LOG_FILE)
    if os.path.exists(logPath):
        os.remove(logPath)
        print(f"{logPath} has been deleted.")
    else:
        print(f"{logPath} does not exist.")
    parser = argparse.ArgumentParser(description="Verify and sync files using checksums, find duplicates.")
    parser.add_argument("source", nargs='?', help="Path to source directory")
    parser.add_argument("target", nargs='?', help="Path to target directory")
    parser.add_argument("--sync", action="store_true", help="Copy missing files from source to target")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite mismatched files in target")

    args = parser.parse_args()

    # Use GUI dialog if source/target not provided
    if not args.source or not args.target:
        tk.Tk().withdraw()  # Hide root window
        if not args.source:
            log(" Please select the SOURCE folder...")
            args.source = filedialog.askdirectory(title="Select Source Directory")
        if not args.target:
            log(" Please select the TARGET folder...")
            args.target = filedialog.askdirectory(title="Select Target Directory")

    if not args.source or not args.target:
        log(" Source and Target directories are required.")
        exit(1)

    verify_and_sync(args.source, args.target, args.sync, args.overwrite)