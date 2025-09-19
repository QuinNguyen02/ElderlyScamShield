import os
import json
from datetime import datetime, timedelta
import pandas as pd
from sklearn.model_selection import train_test_split
from .classifier import train_baseline, load_model

class ModelTrainingService:
    def __init__(self, feedback_dir, model_dir, base_data_path):
        self.feedback_dir = feedback_dir
        self.model_dir = model_dir
        self.base_data_path = base_data_path
        self.last_training_time = None
        self.min_feedback_samples = 50  # Minimum feedback samples before retraining
        self.training_interval = timedelta(hours=24)  # Retrain every 24 hours if enough new data
        
    def _load_feedback_data(self):
        """Load feedback data from JSONL file"""
        feedback_file = os.path.join(self.feedback_dir, "feedback_log.jsonl")
        feedback_data = []
        
        if os.path.exists(feedback_file):
            with open(feedback_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        feedback_data.append({
                            'text': data['transcript'],
                            'label': 0 if data['feedback'] == 'not_scam' else 1,
                            'source': 'feedback'
                        })
                    except Exception as e:
                        print(f"Error parsing feedback line: {e}")
        
        return feedback_data

    def _load_base_training_data(self):
        """Load original training data"""
        df = pd.read_csv(self.base_data_path)
        return [{'text': text, 'label': label, 'source': 'original'} 
                for text, label in zip(df['text'], df['label'])]

    def _save_model_version(self, model, version):
        """Save a versioned copy of the model"""
        version_dir = os.path.join(self.model_dir, 'versions')
        os.makedirs(version_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_path = os.path.join(version_dir, f'model_v{version}_{timestamp}.pkl')
        
        with open(model_path, 'wb') as f:
            import pickle
            pickle.dump(model, f)
        
        # Update the current model
        current_model_path = os.path.join(self.model_dir, 'baseline_model.pkl')
        with open(current_model_path, 'wb') as f:
            pickle.dump(model, f)
        
        return model_path

    def should_retrain(self):
        """Check if model should be retrained based on feedback volume and time"""
        if self.last_training_time is None:
            return True
            
        feedback_data = self._load_feedback_data()
        time_since_last_training = datetime.now() - self.last_training_time
        
        return (len(feedback_data) >= self.min_feedback_samples and 
                time_since_last_training >= self.training_interval)

    def retrain_model(self):
        """Retrain the model with feedback data"""
        try:
            # Load both original and feedback data
            base_data = self._load_base_training_data()
            feedback_data = self._load_feedback_data()
            
            if not feedback_data:
                print("No feedback data available for training")
                return False
                
            # Combine data with higher weight for feedback
            combined_data = base_data + feedback_data * 2  # Duplicate feedback for higher weight
            
            # Convert to DataFrame
            df = pd.DataFrame(combined_data)
            
            # Split data
            X = df['text'].astype(str)
            y = df['label'].astype(int)
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
            
            # Train new model
            version = len(os.listdir(os.path.join(self.model_dir, 'versions'))) + 1
            model_path = self._save_model_version(train_baseline(X_train, y_train), version)
            
            # Update last training time
            self.last_training_time = datetime.now()
            
            # Log training results
            with open(os.path.join(self.model_dir, 'training_log.txt'), 'a') as f:
                f.write(f"\n{datetime.now()} - Trained model v{version}")
                f.write(f"\nFeedback samples: {len(feedback_data)}")
                f.write(f"\nTotal samples: {len(combined_data)}")
                f.write(f"\nModel saved to: {model_path}\n")
            
            print(f"Successfully trained new model version {version}")
            return True
            
        except Exception as e:
            print(f"Error during model retraining: {e}")
            return False