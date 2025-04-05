#!/usr/bin/env python3
import argparse
import subprocess
import os
import json
import tempfile
import sys
import re
from typing import List, Dict, Optional, Tuple

def display_help():
    """Display a comprehensive help menu with examples."""
    help_text = """
AWS S3 Bucket Misconfiguration Scanner
======================================

A tool to scan AWS S3 buckets for permission misconfigurations.

Usage:
------
  Single bucket:    ./s3-bucket-scanner.py -b BUCKET_NAME -p AWS_PROFILE [-r REGION]
  Multiple buckets: ./s3-bucket-scanner.py -l BUCKET_LIST_FILE -p AWS_PROFILE [-r REGION]
  Help:             ./s3-bucket-scanner.py -h or --help

Arguments:
---------
  -b, --bucket BUCKET_NAME    Scan a single S3 bucket
  -l, --list FILE_PATH        Path to a file containing bucket names (one per line)
  -p, --profile PROFILE_NAME  AWS CLI profile to use for authentication
  -r, --region REGION_NAME    AWS region to use (e.g., us-east-1, eu-west-1)
  -h, --help                  Display this help message

Bucket Name Formats:
------------------
  When providing bucket names (either with -b or in a bucket list file), you can use:
  
  1. Full S3 URL with region: mybucket.s3-us-west-1.amazonaws.com
     (Region will be automatically extracted and used)
  
  2. Full S3 URL without region: mybucket.s3.amazonaws.com
     (Only bucket name "mybucket" will be extracted)
  
  3. Simple bucket name: mybucket
     (Will use default region or specified region via -r option)

Example commands:
---------------
  # Scan a single bucket
  ./s3-bucket-scanner.py -b my-bucket -p default

  # Scan a single bucket with a full URL
  ./s3-bucket-scanner.py -b my-bucket.s3-eu-west-1.amazonaws.com -p default

  # Scan a single bucket in a specific region
  ./s3-bucket-scanner.py -b my-bucket -p default -r eu-west-1

  # Scan multiple buckets listed in a file with region specified
  ./s3-bucket-scanner.py -l my_buckets.txt -p prod-account -r us-west-2

  # Using long-form arguments
  ./s3-bucket-scanner.py --bucket my-bucket --profile default --region ap-southeast-1
  ./s3-bucket-scanner.py --list my_buckets.txt --profile prod-account

Permissions checked:
------------------
  - ls:           List objects in bucket/prefix
  - cp (write):   Upload files to bucket/prefix
  - mv:           Move files within bucket/prefix
  - rm:           Delete files from bucket/prefix
  - cp from (read): Download files from bucket/prefix

Output:
------
  The script outputs a detailed report showing which permissions are enabled
  for each prefix within each bucket. Enabled permissions are highlighted in red
  as potential misconfigurations.

Requirements:
-----------
  - Python 3.6+
  - AWS CLI installed and configured
  - Valid AWS credentials with permissions to test S3 operations
  - Required Python packages: Install with 'pip3 install -r requirements.txt'
    """
    print(help_text)
    sys.exit(0)

def extract_bucket_info(bucket_name: str) -> Tuple[str, Optional[str]]:
    """Extract the bucket name and region from a bucket URL or name."""
    # Match patterns like "bucketname.s3-us-west-1.amazonaws.com" or "bucketname.s3.us-west-1.amazonaws.com"
    s3_url_pattern = r'^([^.]+)\.s3[.-]([a-z0-9-]+)\.amazonaws\.com$'
    s3_url_match = re.match(s3_url_pattern, bucket_name)
    
    if s3_url_match:
        # Get bucket name and region from URL
        bucket = s3_url_match.group(1)
        region = s3_url_match.group(2)
        # Handle edge case for s3.amazonaws.com (which has no region specified)
        if region == "amazonaws":
            return bucket, None
        return bucket, region
    
    # Match pattern like "bucketname.s3.amazonaws.com"
    simple_url_pattern = r'^([^.]+)\.s3\.amazonaws\.com$'
    simple_url_match = re.match(simple_url_pattern, bucket_name)
    
    if simple_url_match:
        # Get only bucket name from URL
        return simple_url_match.group(1), None
    
    # If no patterns match, return the original bucket name without a region
    return bucket_name, None

class S3PermissionScanner:
    def __init__(self, profile: str, region: Optional[str] = None):
        """Initialize the S3 permission scanner with the specified AWS profile and optional region."""
        self.profile = profile
        self.default_region = region
        self.temp_file = "s3_scan_test.txt"
        
        # Create test file
        with open(self.temp_file, "w") as f:
            f.write("This is a test file for S3 permission scanning.")
    
    def __del__(self):
        """Clean up local test file when object is destroyed."""
        if os.path.exists(self.temp_file):
            os.remove(self.temp_file)
    
    def run_aws_command(self, command: List[str], region: Optional[str] = None) -> Tuple[bool, str]:
        """Run AWS CLI command and return success status and output."""
        try:
            cmd = ["aws", "--profile", self.profile]
            
            # Add region if specified
            specific_region = region if region else self.default_region
            if specific_region:
                cmd.extend(["--region", specific_region])
                
            cmd.extend(command)
            result = subprocess.run(cmd, check=False, capture_output=True, text=True)
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
        except Exception as e:
            return False, str(e)
    
    def get_bucket_prefixes(self, bucket: str, region: Optional[str] = None) -> List[str]:
        """Get all top-level prefixes (folders) in a bucket."""
        success, output = self.run_aws_command(["s3api", "list-objects-v2", "--bucket", bucket, "--delimiter", "/"], region)
        
        if not success:
            print(f"Error listing prefixes in {bucket}: {output}")
            return []
        
        prefixes = []
        try:
            data = json.loads(output)
            if "CommonPrefixes" in data:
                prefixes = [p["Prefix"] for p in data["CommonPrefixes"]]
            # Also add the bucket root as a prefix
            prefixes.append("")
        except json.JSONDecodeError:
            print(f"Error parsing JSON response for bucket {bucket}")
        
        return prefixes
    
    def check_ls_permission(self, bucket: str, prefix: str, region: Optional[str] = None) -> bool:
        """Check if listing objects in the prefix is allowed."""
        s3_path = f"s3://{bucket}/{prefix}"
        success, _ = self.run_aws_command(["s3", "ls", s3_path], region)
        return success
    
    def check_cp_permission(self, bucket: str, prefix: str, region: Optional[str] = None) -> bool:
        """Check if copying files to the prefix is allowed."""
        dest_path = f"s3://{bucket}/{prefix}test.txt"
        success, _ = self.run_aws_command(["s3", "cp", self.temp_file, dest_path], region)
        return success
    
    def check_mv_permission(self, bucket: str, prefix: str, region: Optional[str] = None) -> bool:
        """Check if moving files within the prefix is allowed."""
        if not self.check_cp_permission(bucket, prefix, region):
            return False
            
        source_path = f"s3://{bucket}/{prefix}test.txt"
        dest_path = f"s3://{bucket}/{prefix}test_moved.txt"
        success, _ = self.run_aws_command(["s3", "mv", source_path, dest_path], region)
        
        # Move back for cleanup
        if success:
            self.run_aws_command(["s3", "mv", dest_path, source_path], region)
        
        return success
    
    def check_rm_permission(self, bucket: str, prefix: str, region: Optional[str] = None) -> bool:
        """Check if removing files from the prefix is allowed."""
        test_path = f"s3://{bucket}/{prefix}test.txt"
        
        # First ensure the file exists
        if not self.check_cp_permission(bucket, prefix, region):
            return False
            
        success, _ = self.run_aws_command(["s3", "rm", test_path], region)
        return success
    
    def check_cp_from_bucket(self, bucket: str, prefix: str, region: Optional[str] = None) -> bool:
        """Check if copying files from the bucket is allowed."""
        # Skip if list is not allowed
        if not self.check_ls_permission(bucket, prefix, region):
            return False
            
        # Get first file in the prefix
        s3_path = f"s3://{bucket}/{prefix}"
        success, output = self.run_aws_command(["s3", "ls", s3_path], region)
        
        if not success or not output.strip():
            return False
            
        # Parse the first file from ls output
        lines = output.strip().split('\n')
        if not lines:
            return False
            
        parts = lines[0].split()
        if len(parts) < 4:  # Format: date time size filename
            return False
            
        filename = ' '.join(parts[3:])
        if prefix and not filename:
            return False
            
        source_path = f"s3://{bucket}/{prefix}{filename}"
        with tempfile.NamedTemporaryFile(delete=True) as temp:
            success, _ = self.run_aws_command(["s3", "cp", source_path, temp.name], region)
            
        return success
    
    def scan_bucket(self, bucket: str, bucket_region: Optional[str] = None) -> Dict[str, Dict[str, bool]]:
        """Scan a single bucket for permission misconfigurations."""
        results = {}
        region_display = f" (region: {bucket_region})" if bucket_region else ""
        print(f"\nScanning bucket: {bucket}{region_display}")
        
        try:
            prefixes = self.get_bucket_prefixes(bucket, bucket_region)
            if not prefixes:
                print(f"  No prefixes found or insufficient permissions to list prefixes in {bucket}")
                return {}
                
            for prefix in prefixes:
                prefix_display = prefix if prefix else "(root)"
                print(f"  Scanning prefix: {prefix_display}")
                
                ls_permission = self.check_ls_permission(bucket, prefix, bucket_region)
                cp_permission = self.check_cp_permission(bucket, prefix, bucket_region)
                mv_permission = self.check_mv_permission(bucket, prefix, bucket_region) if cp_permission else False
                rm_permission = self.check_rm_permission(bucket, prefix, bucket_region) if cp_permission else False
                cp_from_permission = self.check_cp_from_bucket(bucket, prefix, bucket_region)
                
                results[prefix_display] = {
                    "ls": ls_permission,
                    "cp (write)": cp_permission,
                    "mv": mv_permission,
                    "rm": rm_permission,
                    "cp from (read)": cp_from_permission
                }
                
                # Clean up any potential leftover test files
                if cp_permission and not rm_permission:
                    print(f"    Warning: Test file could not be deleted from {bucket}/{prefix}test.txt")
                
                # Display results for this prefix
                for perm, enabled in results[prefix_display].items():
                    status = "ENABLED" if enabled else "DISABLED"
                    color = "\033[91m" if enabled else "\033[92m"  # Red for enabled (potential misconfiguration), green for disabled
                    print(f"    {perm}: {color}{status}\033[0m")
                    
        except Exception as e:
            print(f"Error scanning bucket {bucket}: {str(e)}")
            
        return results

def main():
    # Check if help flag is passed directly
    if "-h" in sys.argv or "--help" in sys.argv:
        display_help()
    
    parser = argparse.ArgumentParser(description="AWS S3 Bucket Misconfiguration Scanner", add_help=False)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-b", "--bucket", help="Single bucket name to scan")
    group.add_argument("-l", "--list", help="Path to file containing list of bucket names")
    parser.add_argument("-p", "--profile", required=True, help="AWS CLI profile to use")
    parser.add_argument("-r", "--region", help="AWS region to use (e.g., us-east-1, eu-west-1)")
    parser.add_argument("-h", "--help", action="store_true", help="Show this help message")
    
    try:
        args = parser.parse_args()
    except SystemExit:
        # If argparse encounters an error, show our custom help
        display_help()
    
    # Check if help flag was used
    if hasattr(args, 'help') and args.help:
        display_help()
    
    scanner = S3PermissionScanner(args.profile, args.region)
    
    buckets = []
    bucket_regions = {}
    
    if args.bucket:
        # Extract bucket name and region from the provided bucket argument
        bucket_name, bucket_region = extract_bucket_info(args.bucket)
        buckets = [bucket_name]
        
        # Use extracted region or command line region
        if bucket_region and not args.region:
            bucket_regions[bucket_name] = bucket_region
            
    elif args.list:
        try:
            with open(args.list, 'r') as f:
                for line in f:
                    bucket = line.strip()
                    if bucket:
                        # Extract bucket name and region from each line in the file
                        bucket_name, bucket_region = extract_bucket_info(bucket)
                        buckets.append(bucket_name)
                        
                        # Use extracted region if no region was specified on command line
                        if bucket_region and not args.region:
                            bucket_regions[bucket_name] = bucket_region
        except Exception as e:
            print(f"Error reading bucket list file: {str(e)}")
            sys.exit(1)
    
    region_info = f" in region '{args.region}'" if args.region else ""
    print(f"Starting S3 bucket misconfiguration scan using profile '{args.profile}'{region_info}")
    print(f"Scanning {len(buckets)} bucket(s)...")
    
    all_results = {}
    for bucket in buckets:
        # Use explicit region if provided, otherwise use extracted region for this bucket
        bucket_region = args.region if args.region else bucket_regions.get(bucket)
        results = scanner.scan_bucket(bucket, bucket_region)
        all_results[bucket] = results
    
    print("\nScan Summary:")
    for bucket, prefixes in all_results.items():
        bucket_region = args.region if args.region else bucket_regions.get(bucket)
        region_display = f" (region: {bucket_region})" if bucket_region else ""
        print(f"\nBucket: {bucket}{region_display}")
        for prefix, permissions in prefixes.items():
            enabled_perms = [p for p, enabled in permissions.items() if enabled]
            if enabled_perms:
                print(f"  Prefix {prefix} has potential misconfigurations: {', '.join(enabled_perms)}")
            else:
                print(f"  Prefix {prefix} has no detected misconfigurations")
    
    print("\nScan complete.")

if __name__ == "__main__":
    main()
