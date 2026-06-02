#!/usr/bin/env python3
"""
Comprehensive diagnostic script for PRD Supabase database connection.
Tests DNS resolution, network connectivity, and database connection.
"""

import os
import sys
import socket
from dotenv import load_dotenv
import psycopg2
from psycopg2 import OperationalError

def test_dns_resolution(hostname):
    """Test DNS resolution for the hostname"""
    print(f"\n🔍 Testing DNS resolution for: {hostname}")

    try:
        # Get all addresses
        addr_info = socket.getaddrinfo(hostname, 5432, socket.AF_UNSPEC, socket.SOCK_STREAM)

        ipv4_addresses = []
        ipv6_addresses = []

        for addr in addr_info:
            family, socktype, proto, canonname, sockaddr = addr
            ip = sockaddr[0]
            if family == socket.AF_INET:
                ipv4_addresses.append(ip)
            elif family == socket.AF_INET6:
                ipv6_addresses.append(ip)

        print(f"   ✅ DNS resolution successful")
        if ipv4_addresses:
            print(f"   📌 IPv4 Addresses: {', '.join(ipv4_addresses)}")
        else:
            print(f"   ⚠️  No IPv4 addresses found")

        if ipv6_addresses:
            print(f"   📌 IPv6 Addresses: {', '.join(ipv6_addresses)}")
        else:
            print(f"   ⚠️  No IPv6 addresses found")

        return ipv4_addresses, ipv6_addresses

    except socket.gaierror as e:
        print(f"   ❌ DNS resolution failed: {e}")
        return [], []

def test_tcp_connectivity(hostname, port, ip_address=None):
    """Test TCP connectivity to the database"""
    print(f"\n🔍 Testing TCP connectivity to {hostname}:{port}")

    if ip_address:
        print(f"   Using IP address: {ip_address}")

    try:
        sock = socket.socket(socket.AF_INET if ip_address else socket.AF_INET6, socket.SOCK_STREAM)
        sock.settimeout(10)

        target = ip_address if ip_address else hostname
        result = sock.connect_ex((target, port))

        if result == 0:
            print(f"   ✅ TCP connection successful")
            sock.close()
            return True
        else:
            print(f"   ❌ TCP connection failed (error code: {result})")
            sock.close()
            return False

    except socket.timeout:
        print(f"   ❌ TCP connection timeout")
        return False
    except Exception as e:
        print(f"   ❌ TCP connection error: {e}")
        return False

def test_database_connection(db_host, db_port, db_user, db_password, db_name, ip_address=None):
    """Test database connection"""
    print(f"\n🔍 Testing database connection")

    if ip_address:
        print(f"   Using IP address: {ip_address}")

    try:
        connection = psycopg2.connect(
            host=ip_address if ip_address else db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=10
        )

        print(f"   ✅ Database connection successful")

        # Test basic query
        cursor = connection.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()

        print(f"\n📊 Database Information:")
        print(f"   PostgreSQL Version: {version[0]}")

        # Get current database and user
        cursor.execute("SELECT current_database(), current_user;")
        db_info = cursor.fetchone()
        print(f"   Current Database: {db_info[0]}")
        print(f"   Current User: {db_info[1]}")

        cursor.close()
        connection.close()
        return True

    except OperationalError as e:
        print(f"   ❌ Database connection failed: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Database connection error: {e}")
        return False

def main():
    """Main diagnostic function"""
    # Load environment variables
    load_dotenv()

    # Get credentials
    db_host = os.getenv('SUPABASE_DB_HOST_PRD')
    db_port = int(os.getenv('SUPABASE_DB_PORT_PRD', '5432'))
    db_password = os.getenv('SUPABASE_DB_PASSWORD_PRD')
    db_user = 'postgres'
    db_name = 'postgres'

    # Mask password for display
    masked_password = db_password[:4] + '...' + db_password[-4:] if len(db_password) > 8 else '***'

    print("=" * 70)
    print("PRD Supabase Database Connection - Comprehensive Diagnostic")
    print("=" * 70)
    print(f"Host: {db_host}")
    print(f"Port: {db_port}")
    print(f"Database: {db_name}")
    print(f"User: {db_user}")
    print(f"Password: {masked_password}")
    print("=" * 70)

    # Test 1: DNS Resolution
    ipv4_addresses, ipv6_addresses = test_dns_resolution(db_host)

    if not ipv4_addresses and not ipv6_addresses:
        print("\n❌ CRITICAL: DNS resolution failed - cannot proceed")
        return False

    # Test 2: TCP Connectivity
    tcp_success = False

    # Try IPv4 first if available
    if ipv4_addresses:
        for ip in ipv4_addresses:
            if test_tcp_connectivity(db_host, db_port, ip):
                tcp_success = True
                break

    # Try IPv6 if IPv4 failed
    if not tcp_success and ipv6_addresses:
        for ip in ipv6_addresses:
            if test_tcp_connectivity(db_host, db_port, ip):
                tcp_success = True
                break

    if not tcp_success:
        print("\n❌ CRITICAL: TCP connectivity failed - cannot proceed")
        return False

    # Test 3: Database Connection
    db_success = False

    # Try IPv4 first if available
    if ipv4_addresses:
        for ip in ipv4_addresses:
            if test_database_connection(db_host, db_port, db_user, db_password, db_name, ip):
                db_success = True
                break

    # Try IPv6 if IPv4 failed
    if not db_success and ipv6_addresses:
        for ip in ipv6_addresses:
            if test_database_connection(db_host, db_port, db_user, db_password, db_name, ip):
                db_success = True
                break

    # Final result
    print("\n" + "=" * 70)
    if db_success:
        print("✅ SUCCESS: All tests passed - database connection is working!")
    else:
        print("❌ FAILURE: Database connection test failed")
        print("\n💡 Troubleshooting Suggestions:")
        print("   - Verify the database credentials are correct")
        print("   - Check if the database allows connections from your IP")
        print("   - Verify network connectivity and firewall rules")
        print("   - Check if the database is running and accepting connections")
        print("   - Try connecting from a different network or location")
    print("=" * 70)

    return db_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)