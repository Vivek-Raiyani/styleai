"""
Database cleanup utility for StyleAI Studio.
Removes guest accounts and test generation data prior to deployment or maintenance.

Usage:
    python clean_data.py                  # Cleans all guest accounts and their associated data
    python clean_data.py --all-testing    # Cleans guests + all user selfies/results/batches (keeps assets & catalog)
    python clean_data.py --stats          # Show database row counts without deleting
"""
import sys
import argparse
from sqlalchemy.orm import Session
from db import (
    SessionLocal, User, Selfie, Result, Asset,
    CuratedLook, BrandModel, BrandProduct, BrandBatch, BrandPairResult
)


def get_stats(db: Session) -> dict:
    return {
        "total_users": db.query(User).count(),
        "guest_users": db.query(User).filter(User.is_guest == True).count(),
        "registered_users": db.query(User).filter(User.is_guest == False).count(),
        "selfies": db.query(Selfie).count(),
        "results": db.query(Result).count(),
        "brand_batches": db.query(BrandBatch).count(),
        "brand_pair_results": db.query(BrandPairResult).count(),
        "custom_models": db.query(BrandModel).filter(BrandModel.is_preset == False).count(),
        "custom_products": db.query(BrandProduct).filter(BrandProduct.is_preset == False).count(),
        "preset_models": db.query(BrandModel).filter(BrandModel.is_preset == True).count(),
        "preset_products": db.query(BrandProduct).filter(BrandProduct.is_preset == True).count(),
        "catalog_assets": db.query(Asset).count(),
        "curated_looks": db.query(CuratedLook).count(),
    }


def clean_guest_data(db: Session) -> dict:
    """
    Remove all guest users and their associated records:
    - Guest selfies
    - Guest results
    - Guest brand batches & pair results
    - Guest custom models/products
    """
    guest_ids = [u.id for u in db.query(User.id).filter(User.is_guest == True).all()]
    if not guest_ids:
        return {"guests_deleted": 0, "selfies_deleted": 0, "results_deleted": 0, "batches_deleted": 0}

    # Delete pair results for guests
    pair_count = db.query(BrandPairResult).filter(BrandPairResult.user_id.in_(guest_ids)).delete(synchronize_session=False)
    # Delete batches for guests
    batch_count = db.query(BrandBatch).filter(BrandBatch.user_id.in_(guest_ids)).delete(synchronize_session=False)
    # Delete results for guests
    result_count = db.query(Result).filter(Result.user_id.in_(guest_ids)).delete(synchronize_session=False)
    # Delete selfies for guests
    selfie_count = db.query(Selfie).filter(Selfie.user_id.in_(guest_ids)).delete(synchronize_session=False)
    # Delete custom brand models/products uploaded by guests
    db.query(BrandModel).filter(BrandModel.user_id.in_(guest_ids)).delete(synchronize_session=False)
    db.query(BrandProduct).filter(BrandProduct.user_id.in_(guest_ids)).delete(synchronize_session=False)
    # Delete guest users
    guest_count = db.query(User).filter(User.id.in_(guest_ids)).delete(synchronize_session=False)

    db.commit()
    return {
        "guests_deleted": guest_count,
        "selfies_deleted": selfie_count,
        "results_deleted": result_count,
        "batches_deleted": batch_count,
        "pair_results_deleted": pair_count,
    }


def clean_all_testing_data(db: Session) -> dict:
    """
    Remove all guest users and purge all test generation runs across all accounts
    (selfies, results, brand batches), while keeping admin/demo accounts and catalog assets.
    """
    # 1. Clean guests first
    guest_summary = clean_guest_data(db)

    # 2. Delete all remaining pair results and batches
    pair_count = db.query(BrandPairResult).delete(synchronize_session=False)
    batch_count = db.query(BrandBatch).delete(synchronize_session=False)

    # 3. Delete all remaining results and selfies (testing artifacts)
    result_count = db.query(Result).delete(synchronize_session=False)
    selfie_count = db.query(Selfie).delete(synchronize_session=False)

    # 4. Clean non-preset models/products
    custom_models = db.query(BrandModel).filter(BrandModel.is_preset == False).delete(synchronize_session=False)
    custom_products = db.query(BrandProduct).filter(BrandProduct.is_preset == False).delete(synchronize_session=False)

    db.commit()
    return {
        **guest_summary,
        "total_selfies_purged": selfie_count + guest_summary.get("selfies_deleted", 0),
        "total_results_purged": result_count + guest_summary.get("results_deleted", 0),
        "total_batches_purged": batch_count + guest_summary.get("batches_deleted", 0),
        "total_pair_results_purged": pair_count + guest_summary.get("pair_results_deleted", 0),
    }


def main():
    parser = argparse.ArgumentParser(description="StyleAI database cleanup utility.")
    parser.add_argument("--stats", action="store_true", help="Show current DB counts only")
    parser.add_argument("--all-testing", action="store_true", help="Purge all test generation runs across all accounts")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        print("=" * 60)
        print("StyleAI Database Cleanup Utility")
        print("=" * 60)

        before = get_stats(db)
        print("Current Database State:")
        for k, v in before.items():
            print(f"  - {k}: {v}")

        if args.stats:
            return

        print("-" * 60)
        if args.all_testing:
            print("Purging ALL test runs (guest accounts + test selfies/results/batches)...")
            res = clean_all_testing_data(db)
            print("Cleanup completed:", res)
        else:
            print("Purging all GUEST accounts and their associated test data...")
            res = clean_guest_data(db)
            print("Cleanup completed:", res)

        print("-" * 60)
        after = get_stats(db)
        print("Updated Database State:")
        for k, v in after.items():
            print(f"  - {k}: {v}")
        print("=" * 60)

    finally:
        db.close()


if __name__ == "__main__":
    main()
