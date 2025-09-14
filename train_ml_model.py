#!/usr/bin/env python3
"""
ML Model Training Script for URL Prediction

This script trains the ML URL prediction model using historical extraction data.
Run this script after collecting sufficient extraction data to improve URL prediction accuracy.
"""

import argparse
from datetime import datetime
from core.ml_url_predictor import get_ml_url_predictor
from core.db import get_supabase_client
from core.logger import get_logger

logger = get_logger(__name__)


def main():
    """Train the ML URL prediction model."""
    parser = argparse.ArgumentParser(description='Train ML URL Prediction Model')
    parser.add_argument('--retrain', action='store_true',
                       help='Force retrain even if model is already trained')
    parser.add_argument('--min-samples', type=int, default=10,
                       help='Minimum number of samples required for training (default: 10)')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')

    args = parser.parse_args()

    print("🧠 ML URL Prediction Model Training")
    print("=" * 50)

    try:
        # Initialize components
        print("📡 Connecting to database...")
        supabase = get_supabase_client()

        print("🧠 Initializing ML predictor...")
        ml_predictor = get_ml_url_predictor(supabase)

        # Check current status
        print(f"🔍 Current model status: {'Trained' if ml_predictor.is_trained else 'Not trained'}")

        # Load and analyze training data
        print("📊 Loading training data...")
        urls, labels = ml_predictor.load_training_data()

        positive_samples = sum(labels)
        negative_samples = len(labels) - positive_samples

        print("\n📊 Training Data Summary:")
        print(f"   Total URLs: {len(urls)}")
        print(f"   Successful URLs (positive): {positive_samples}")
        print(f"   Failed URLs (negative): {negative_samples}")

        if args.verbose and urls:
            print("\n🔍 Sample URLs (first 5):")
            for i, (url, label) in enumerate(zip(urls[:5], labels[:5])):
                status = "✅ Success" if label == 1 else "❌ Failed"
                print(f"   {i+1}. {status} - {url}")

        # Check if we have enough data
        if len(urls) < args.min_samples:
            print(f"\n⚠️  Insufficient training data!")
            print(f"   Required: {args.min_samples} samples")
            print(f"   Available: {len(urls)} samples")
            print("\n💡 To collect more training data:")
            print("   1. Run more schedule extractions")
            print("   2. The extraction pipeline automatically collects visit tracking data")
            print("   3. Run this training script again when you have more data")
            return False

        # Train the model
        if ml_predictor.is_trained and not args.retrain:
            print(f"\n✅ Model is already trained!")
            print("   Use --retrain flag to force retraining")

            # Test prediction
            test_prediction(ml_predictor)
            return True

        print(f"\n🧠 Training model...")
        start_time = datetime.now()

        success = ml_predictor.train_model(retrain=args.retrain)

        training_time = datetime.now() - start_time

        if success:
            print(f"✅ Model training completed successfully!")
            print(f"   Training time: {training_time.total_seconds():.2f} seconds")
            print(f"   Model status: {'Trained' if ml_predictor.is_trained else 'Failed'}")

            # Test the trained model
            test_prediction(ml_predictor)

            print("\n🎯 Model Training Complete!")
            print("   The model will now be used automatically during extractions")
            return True
        else:
            print("❌ Model training failed!")
            print("   Check logs for detailed error information")
            return False

    except Exception as e:
        logger.error(f"Training error: {e}")
        print(f"❌ Training error: {e}")
        return False


def test_prediction(ml_predictor):
    """Test the trained model with sample predictions."""
    print("\n🧪 Testing trained model...")

    test_domains = [
        'stjohnparish.org',
        'holyfamilycatholic.org',
        'stmaryschurch.com'
    ]

    for domain in test_domains:
        try:
            predictions = ml_predictor.predict_successful_urls(domain)
            print(f"   {domain}: {len(predictions)} URLs predicted")

            if predictions:
                top_url, confidence = predictions[0]
                print(f"      Top prediction: {top_url} (confidence: {confidence:.3f})")

        except Exception as e:
            print(f"   {domain}: Prediction failed - {e}")


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)