#!/bin/bash
# Quick script to run Supabase connection tests
# This script provides easy access to all test functionality

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Supabase Connection Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "/tmp/test_env" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv /tmp/test_env
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source /tmp/test_env/bin/activate

# Install dependencies if needed
echo -e "${YELLOW}Checking dependencies...${NC}"
if ! python -c "import supabase" 2>/dev/null; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -q supabase psycopg2-binary python-dotenv
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${GREEN}✓ Dependencies already installed${NC}"
fi

echo ""
echo -e "${BLUE}Choose test to run:${NC}"
echo "1) Comprehensive Test (DEV + PRD)"
echo "2) DEV Environment Only"
echo "3) PRD Environment Only"
echo "4) REST API Test Only"
echo "5) Direct DB Connection Test Only"
echo "6) Quick Health Check"
echo ""
read -p "Enter choice (1-6): " choice

case $choice in
    1)
        echo -e "${BLUE}Running comprehensive test...${NC}"
        python test_supabase_comprehensive_v2.py
        ;;
    2)
        echo -e "${BLUE}Testing DEV environment...${NC}"
        python -c "
import os
from dotenv import load_dotenv
from supabase import create_client
import psycopg2

load_dotenv()

print('Testing DEV Environment...')
print('=' * 50)

# Test REST API
try:
    supabase = create_client(os.getenv('SUPABASE_URL_DEV'), os.getenv('SUPABASE_KEY_DEV'))
    supabase.auth.get_user()
    print('✅ REST API: Working')
except Exception as e:
    print(f'❌ REST API: {e}')

# Test Direct DB
try:
    conn = psycopg2.connect(
        host=os.getenv('SUPABASE_DB_HOST_DEV'),
        port=os.getenv('SUPABASE_DB_PORT_DEV'),
        database='postgres',
        user='postgres',
        password=os.getenv('SUPABASE_DB_PASSWORD_DEV')
    )
    conn.close()
    print('✅ Direct DB: Working')
except Exception as e:
    print(f'❌ Direct DB: {e}')

print('=' * 50)
"
        ;;
    3)
        echo -e "${BLUE}Testing PRD environment...${NC}"
        python -c "
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

print('Testing PRD Environment...')
print('=' * 50)

# Test REST API
try:
    supabase = create_client(os.getenv('SUPABASE_URL_PRD'), os.getenv('SUPABASE_KEY_PRD'))
    supabase.auth.get_user()
    response = supabase.table('Dioceses').select('*').limit(1).execute()
    print('✅ REST API: Working')
    print(f'✅ Data Access: {len(response.data)} records found')
except Exception as e:
    print(f'❌ REST API: {e}')

print('⚠️  Direct DB: Not available (IPv6 limitation)')
print('=' * 50)
"
        ;;
    4)
        echo -e "${BLUE}Testing REST API connectivity...${NC}"
        python test_supabase_rest_api.py
        ;;
    5)
        echo -e "${BLUE}Testing direct database connections...${NC}"
        python test_prd_db_connection_v4.py
        ;;
    6)
        echo -e "${BLUE}Running quick health check...${NC}"
        python -c "
import os
from dotenv import load_dotenv
from supabase import create_client
import psycopg2

load_dotenv()

print('Quick Health Check')
print('=' * 50)

# DEV Health
dev_status = '✅'
try:
    supabase = create_client(os.getenv('SUPABASE_URL_DEV'), os.getenv('SUPABASE_KEY_DEV'))
    supabase.auth.get_user()
    conn = psycopg2.connect(
        host=os.getenv('SUPABASE_DB_HOST_DEV'),
        port=os.getenv('SUPABASE_DB_PORT_DEV'),
        database='postgres',
        user='postgres',
        password=os.getenv('SUPABASE_DB_PASSWORD_DEV'),
        connect_timeout=5
    )
    conn.close()
except:
    dev_status = '❌'

# PRD Health
prd_status = '✅'
try:
    supabase = create_client(os.getenv('SUPABASE_URL_PRD'), os.getenv('SUPABASE_KEY_PRD'))
    supabase.auth.get_user()
    response = supabase.table('Dioceses').select('*').limit(1).execute()
except:
    prd_status = '❌'

print(f'DEV Environment:  {dev_status}')
print(f'PRD Environment:  {prd_status}')
print('=' * 50)

if dev_status == '✅' and prd_status == '✅':
    print('✅ All systems operational')
    exit(0)
else:
    print('❌ Some systems have issues')
    exit(1)
"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Test completed!${NC}"
echo -e "${BLUE}Check the generated report for details.${NC}"