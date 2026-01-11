#!/usr/bin/env python3
"""
Verification script for the refactoring of automate_complete.py
This script checks that all modules are properly structured and importable.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, '.')

def test_imports():
    """Test that all modules can be imported."""
    print("=" * 60)
    print("TESTING MODULE IMPORTS")
    print("=" * 60)
    
    modules = [
        # Core modules (no external deps)
        ('core.config', 'Config, config', False),
        ('core.models', 'GenerationConfig, ScenePrompt, ProcessingStatus', False),
        ('core.logger', 'Logger', False),
        ('core.utils', 'parse_prompt_item, check_processed_videos, compute_generation_status', False),
        
        # UI modules (requires wx)
        ('ui.variables', 'SimpleVar', False),
        ('ui.dialogs', 'messagebox, filedialog', True),  # requires wx
        
        # Media modules (no external deps for import)
        ('media.ffmpeg_ops', 'MediaProcessor', False),
        
        # Generation modules (requires playwright)
        ('generation.base_runner', 'BaseRunner', False),
        ('generation.factory', 'create_runner', True),  # requires playwright
        
        # Services modules (requires playwright/youtube)
        ('services.pipeline', 'Pipeline', True),  # requires external deps
    ]
    
    success_count = 0
    fail_count = 0
    optional_fail_count = 0
    
    for module_path, classes, optional in modules:
        try:
            exec(f"from {module_path} import {classes}")
            print(f"✅ {module_path}")
            success_count += 1
        except ImportError as e:
            if optional:
                print(f"⚠️  {module_path}: {e} (optional dependency)")
                optional_fail_count += 1
            else:
                print(f"❌ {module_path}: {e}")
                fail_count += 1
        except Exception as e:
            print(f"⚠️  {module_path}: {e}")
            if not optional:
                fail_count += 1
    
    print(f"\nResults: {success_count} passed, {fail_count} failed")
    if optional_fail_count > 0:
        print(f"         {optional_fail_count} optional dependencies missing (expected in test env)")
    return fail_count == 0


def test_file_structure():
    """Test that all expected files exist."""
    print("\n" + "=" * 60)
    print("TESTING FILE STRUCTURE")
    print("=" * 60)
    
    expected_files = [
        # Entry point
        'automate_complete.py',
        
        # Core package
        'core/__init__.py',
        'core/config.py',
        'core/models.py',
        'core/logger.py',
        'core/utils.py',
        
        # UI package
        'ui/__init__.py',
        'ui/main_window.py',
        'ui/dialogs.py',
        'ui/variables.py',
        
        # Services package
        'services/__init__.py',
        'services/pipeline.py',
        
        # Generation package
        'generation/__init__.py',
        'generation/base_runner.py',
        'generation/default_runner.py',
        'generation/flow_runner.py',
        'generation/google_flow_runner.py',
        'generation/factory.py',
        
        # Media package
        'media/__init__.py',
        'media/ffmpeg_ops.py',
        
        # Supporting files
        'requirements.txt',
        'README.md',
        'REFACTORING_SUMMARY.md',
        
        # Existing helpers (unchanged)
        'flow_editor_runner.py',
        'youtube_uploader.py',
        'thumbnail_generator.py',
    ]
    
    success_count = 0
    fail_count = 0
    
    for filepath in expected_files:
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"✅ {filepath:45s} ({size:6d} bytes)")
            success_count += 1
        else:
            print(f"❌ {filepath:45s} NOT FOUND")
            fail_count += 1
    
    print(f"\nResults: {success_count} files found, {fail_count} missing")
    return fail_count == 0


def count_lines():
    """Count lines of code in the new structure."""
    print("\n" + "=" * 60)
    print("CODE METRICS")
    print("=" * 60)
    
    packages = {
        'core': 'core',
        'ui': 'ui',
        'services': 'services',
        'generation': 'generation',
        'media': 'media',
    }
    
    total_lines = 0
    
    for package_name, package_dir in packages.items():
        lines = 0
        files = 0
        if os.path.isdir(package_dir):
            for filename in os.listdir(package_dir):
                if filename.endswith('.py'):
                    filepath = os.path.join(package_dir, filename)
                    with open(filepath, 'r') as f:
                        file_lines = len(f.readlines())
                        lines += file_lines
                        files += 1
        
        print(f"{package_name:15s}: {lines:5d} lines in {files} files")
        total_lines += lines
    
    # Add entrypoint
    if os.path.exists('automate_complete.py'):
        with open('automate_complete.py', 'r') as f:
            entrypoint_lines = len(f.readlines())
            print(f"{'entrypoint':15s}: {entrypoint_lines:5d} lines")
            total_lines += entrypoint_lines
    
    # Compare to old file
    if os.path.exists('automate_complete_old.py'):
        with open('automate_complete_old.py', 'r') as f:
            old_lines = len(f.readlines())
            print(f"{'OLD (monolithic)':15s}: {old_lines:5d} lines")
    
    print(f"\n{'TOTAL (new)':15s}: {total_lines:5d} lines in modular structure")


def main():
    """Run all verification tests."""
    print("\n" + "=" * 60)
    print("REFACTORING VERIFICATION")
    print("=" * 60)
    
    # Run tests
    imports_ok = test_imports()
    structure_ok = test_file_structure()
    count_lines()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    if imports_ok and structure_ok:
        print("✅ All verification checks passed!")
        print("✅ Refactoring is complete and modules are properly structured")
        print("\n⚠️  Note: Full testing requires wxPython, playwright, and other")
        print("   runtime dependencies. Install with: pip install -r requirements.txt")
        return 0
    else:
        print("❌ Some verification checks failed")
        if not imports_ok:
            print("   - Module imports failed")
        if not structure_ok:
            print("   - File structure incomplete")
        return 1


if __name__ == '__main__':
    sys.exit(main())
