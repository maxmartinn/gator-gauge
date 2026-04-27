#!/usr/bin/env python3
"""
Quick test to verify AWS S3 access is working.
Run this before starting the dashboard.
"""

import os
import sys

# Check AWS_PROFILE
profile = os.environ.get("AWS_PROFILE", "default")
print(f"🔐 Using AWS profile: {profile}")

# Import boto3 and test access
try:
    import boto3
    from data_access import get_available_locations

    client = boto3.client("s3", region_name="us-east-1")
    print(f"✅ boto3 client created successfully")

    # Test S3 access
    response = client.list_objects_v2(Bucket="gator-gains-data", MaxKeys=1)
    if response.get("Contents"):
        print(f"✅ S3 bucket 'gator-gains-data' is accessible")
    else:
        print(f"⚠️ Bucket exists but no objects found (might be OK if empty)")

    # Try to fetch locations
    print("🔍 Fetching available locations...")
    locations = get_available_locations(client)
    print(f"✅ Found {len(locations)} locations:")
    for loc in locations[:5]:
        print(f"   - {loc}")
    if len(locations) > 5:
        print(f"   ... and {len(locations) - 5} more")

    print("\n✅ All checks passed! You're ready to run the dashboard.")
    print(f"   Run: make dashboard")

except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nTroubleshooting:")
    print(f"  1. Ensure AWS_PROFILE={profile} is exported in your shell")
    print(f"  2. Run: aws s3 ls s3://gator-gains-data/ --profile {profile}")
    print(f"  3. Check that your IAM user has S3 read permissions")
    sys.exit(1)
