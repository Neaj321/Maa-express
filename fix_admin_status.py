"""
Automated fixer to align all code with database schema (admin_status field)
Run once: python fix_admin_status.py
"""

import os
import sys

def update_file(filepath, find_replace_pairs):
    """Update a file with multiple find/replace operations"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        for old, new in find_replace_pairs:
            content = content.replace(old, new)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Updated: {filepath}")
            return True
        else:
            print(f"⏭️  No changes: {filepath}")
            return False
    except Exception as e:
        print(f"❌ Error updating {filepath}: {e}")
        return False

def main():
    print("=" * 70)
    print("🔧 Fixing admin_status field inconsistency")
    print("=" * 70)
    
    changes_made = 0
    
    # 1. Fix models.py
    print("\n📝 Updating models.py...")
    if update_file("models.py", [
        ("    status = db.Column(\n        db.Enum('pending', 'approved', 'rejected', name=\"cat1_status_enum\"),\n        default='pending'\n    )",
         "    admin_status = db.Column(\n        db.Enum('pending', 'approved', 'rejected', name=\"cat1_status_enum\"),\n        default='pending'\n    )"),
        
        ("    status = db.Column(\n        db.Enum('pending', 'approved', 'rejected', name=\"cat2_status_enum\"),\n        default='pending'\n    )",
         "    admin_status = db.Column(\n        db.Enum('pending', 'approved', 'rejected', name=\"cat2_status_enum\"),\n        default='pending'\n    )"),
        
        ("    status = db.Column(\n        db.Enum('pending', 'approved', 'rejected', name=\"cat3_status_enum\"),\n        default='pending'\n    )",
         "    admin_status = db.Column(\n        db.Enum('pending', 'approved', 'rejected', name=\"cat3_status_enum\"),\n        default='pending'\n    )"),
    ]):
        changes_made += 1
    
    # 2. Fix blueprints/category1.py
    print("\n📝 Updating blueprints/category1.py...")
    if update_file("blueprints/category1.py", [
        ('filter_by(status="approved")', 'filter_by(admin_status="approved")'),
        ('status="pending"', 'admin_status="pending"'),
    ]):
        changes_made += 1
    
    # 3. Fix blueprints/main.py
    print("\n📝 Updating blueprints/main.py...")
    if update_file("blueprints/main.py", [
        ('filter_by(status="approved")', 'filter_by(admin_status="approved")'),
    ]):
        changes_made += 1
    
    # 4. Fix blueprints/admin.py (inconsistent lines)
    print("\n📝 Updating blueprints/admin.py...")
    if update_file("blueprints/admin.py", [
        ('q.filter_by(status=status_filter)', 'q.filter_by(admin_status=status_filter)'),
        ('listing.status = new_status', 'listing.admin_status = new_status'),
        ('product.status = new_status', 'product.admin_status = new_status'),
    ]):
        changes_made += 1
    
    # 5. Update copilot-instructions.md
    print("\n📝 Updating .github/copilot-instructions.md...")
    if update_file(".github/copilot-instructions.md", [
        ("- Listing lifecycle (Category1): status values observed in code — `pending_documents`, `pending_phone_verification`, `pending_admin_review`, `approved`, `rejected`, `sold`. Follow these exact strings when updating status.",
         "- **Admin approval system**: All listing models (`Category1Listing`, `Category2Listing`, `Category3Product`) use `admin_status` field with values: `pending`, `approved`, `rejected`. Always filter by `admin_status=\"approved\"` for public views."),
        
        ("- Admin status update: `POST /admin/category1/<listing_uid>/update-status` — allowed values: `approved`, `rejected`.",
         "- Admin status update: `POST /admin/category1/<listing_id>/update-status` — allowed values: `approved`, `rejected`, `pending`. Updates `admin_status` field."),
    ]):
        changes_made += 1
    
    print("\n" + "=" * 70)
    if changes_made > 0:
        print(f"✅ SUCCESS! Updated {changes_made} file(s)")
        print("\n📋 Changes made:")
        print("   • models.py: status → admin_status (3 models)")
        print("   • blueprints/category1.py: filter/create uses admin_status")
        print("   • blueprints/main.py: filter uses admin_status")
        print("   • blueprints/admin.py: fixed inconsistencies")
        print("   • .github/copilot-instructions.md: updated docs")
        print("\n🚀 Next step: Restart Flask")
        print("   python app.py")
    else:
        print("ℹ️  All files already correct (no changes needed)")
    print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)