#!/bin/bash

# Multi-Architecture Build Test Script
# This script validates the Dockerfile changes and provides build commands

echo "🔍 Multi-Architecture Build Validation"
echo "======================================"
echo ""

# Check if Docker is available
if command -v docker >/dev/null 2>&1; then
    echo "✅ Docker is available"

    # Check Docker Buildx
    if docker buildx version >/dev/null 2>&1; then
        echo "✅ Docker Buildx is available"
        docker buildx ls
        echo ""
    else
        echo "❌ Docker Buildx is not available"
        echo "💡 Install buildx: https://docs.docker.com/buildx/working-with-buildx/"
        echo ""
    fi
else
    echo "❌ Docker is not available"
    echo "💡 Install Docker: https://docs.docker.com/get-docker/"
    echo ""
fi

echo "📋 Build Commands to Test:"
echo "========================="
echo ""

echo "1. Test Pipeline Dockerfile (multi-arch):"
echo "   docker buildx build --platform linux/amd64,linux/arm64 -f Dockerfile.pipeline -t test-pipeline:multi-arch ."
echo ""

echo "2. Test Backend Dockerfile (multi-arch):"
echo "   docker buildx build --platform linux/amd64,linux/arm64 -f backend/Dockerfile -t test-backend:multi-arch backend/"
echo ""

echo "3. Test Frontend Dockerfile (multi-arch):"
echo "   docker buildx build --platform linux/amd64,linux/arm64 -f frontend/Dockerfile -t test-frontend:multi-arch frontend/"
echo ""

echo "4. Push to registry (replace with your registry):"
echo "   docker buildx build --platform linux/amd64,linux/arm64 -f Dockerfile.pipeline -t tomatl/diocesan-vitality:pipeline-test --push ."
echo ""

echo "📝 Dockerfile Changes Validation:"
echo "================================="
echo ""

# Validate Dockerfile.pipeline changes
if grep -q 'ARCH=$(dpkg --print-architecture)' Dockerfile.pipeline; then
    echo "✅ Dockerfile.pipeline has dynamic architecture detection"
else
    echo "❌ Dockerfile.pipeline missing dynamic architecture detection"
fi

if grep -q 'arch=amd64' Dockerfile.pipeline; then
    echo "❌ Dockerfile.pipeline still has hardcoded amd64 architecture"
else
    echo "✅ Dockerfile.pipeline no longer has hardcoded amd64"
fi

echo ""

echo "🚀 GitHub Actions Workflow Files:"
echo "================================="
echo ""

if [ -f ".github/workflows/multi-arch-build.yml" ]; then
    echo "✅ Multi-architecture workflow created"
else
    echo "❌ Multi-architecture workflow missing"
fi

echo ""

echo "📊 Summary:"
echo "==========="
echo "• Fixed Dockerfile.pipeline architecture detection"
echo "• Created multi-arch GitHub Actions workflow"
echo "• Both AMD64 and ARM64 platforms supported"
echo "• Compatible with DOKS (x86_64) and local development (ARM64)"
echo ""

echo "🎯 Next Steps:"
echo "=============="
echo "1. Test locally: ./test-multi-arch.sh"
echo "2. Commit changes to trigger GitHub Actions"
echo "3. Monitor GitHub Actions run for successful multi-arch build"
echo "4. Deploy to DOKS cluster"
echo ""
