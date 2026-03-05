#!/bin/bash

# AWS Lambda Deployment Script for ezdoc-back
# This script packages the application for Lambda deployment

set -e

echo "🚀 Starting Lambda deployment package creation..."

# Configuration
PACKAGE_DIR="lambda_package"
ZIP_FILE="ezdoc-lambda.zip"

# Clean up previous builds
echo "🧹 Cleaning up previous builds..."
rm -rf $PACKAGE_DIR
rm -f $ZIP_FILE

# Create package directory
echo "📁 Creating package directory..."
mkdir -p $PACKAGE_DIR

# Install dependencies
echo "📦 Installing dependencies..."

# Use requirements.txt if it exists (simpler and more reliable)
if [ -f "requirements.txt" ]; then
    echo "   Using requirements.txt..."
    pip install -r requirements.txt -t $PACKAGE_DIR --platform manylinux2014_x86_64 --python-version 3.13 --only-binary=:all:
elif command -v poetry &> /dev/null && [ -f "pyproject.toml" ]; then
    echo "   Using Poetry to export dependencies..."
    # Export dependencies from Poetry (without dev dependencies, without exact hashes)
    poetry export -f requirements.txt --output temp_requirements.txt --without-hashes --without-urls
    pip install -r temp_requirements.txt -t $PACKAGE_DIR --platform manylinux2014_x86_64 --python-version 3.13 --only-binary=:all: --upgrade
    rm temp_requirements.txt
else
    echo "   ❌ Error: No requirements.txt or pyproject.toml found!"
    exit 1
fi

# Copy application code
echo "📋 Copying application code..."
cp -r app $PACKAGE_DIR/
cp lambda_handler.py $PACKAGE_DIR/
cp lambda_function.py $PACKAGE_DIR/
cp alembic.ini $PACKAGE_DIR/ 2>/dev/null || true
cp -r alembic $PACKAGE_DIR/ 2>/dev/null || true

# Remove unnecessary files to reduce package size
echo "🔧 Optimizing package size..."
cd $PACKAGE_DIR
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true

# Create zip file
echo "📦 Creating deployment package..."
zip -r ../$ZIP_FILE . -q

cd ..
PACKAGE_SIZE=$(du -h $ZIP_FILE | cut -f1)
echo "✅ Deployment package created: $ZIP_FILE (Size: $PACKAGE_SIZE)"
echo ""
echo "📌 Next steps:"
echo "   1. Upload $ZIP_FILE to AWS Lambda"
echo "   2. Set handler to: lambda_handler.handler"
echo "   3. Configure environment variables"
echo "   4. Set timeout to at least 30 seconds"
echo "   5. Set memory to at least 512 MB"
echo ""
echo "🎉 Package ready for deployment!"
