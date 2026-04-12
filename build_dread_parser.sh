#!/bin/bash

echo "⚡ DREAD PARSER - Build Script ⚡"
echo "================================"
echo ""

# Check if .NET SDK is installed
if ! command -v dotnet &> /dev/null; then
    echo "❌ .NET SDK not found. Please install .NET 6.0 SDK first."
    echo "   Download: https://dotnet.microsoft.com/download"
    exit 1
fi

echo "✅ .NET SDK found: $(dotnet --version)"
echo ""

# Navigate to project directory
cd DreadParser

# Restore packages
echo "📦 Restoring NuGet packages..."
dotnet restore

if [ $? -ne 0 ]; then
    echo "❌ Failed to restore packages"
    exit 1
fi

echo ""
echo "🔨 Building DreadParser..."
dotnet build --configuration Release

if [ $? -ne 0 ]; then
    echo "❌ Build failed"
    exit 1
fi

echo ""
echo "✅ Build successful!"
echo ""
echo "📁 Output location:"
echo "   bin/Release/net6.0-windows/"
echo ""
echo "🚀 To run the application:"
echo "   cd bin/Release/net6.0-windows"
echo "   ./DreadParser.exe"
echo ""
echo "⚠️  Note: For RAR/7Z support, place 7z.dll in the output directory"
